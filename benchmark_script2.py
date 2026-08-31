import socket
import time
import random
import concurrent.futures
import psycopg2
from psycopg2 import pool

CACHE_HOST = '127.0.0.1'
CACHE_PORT = 8080

DB_CONFIG = {
    "dbname": "college_db",
    "user": "postgres",
    "password": "postgres", 
    "host": "127.0.0.1",
    "port": 5432
}

# Increased maxconn to 20 to match the worker threads
db_pool = psycopg2.pool.ThreadedConnectionPool(minconn=1, maxconn=20, **DB_CONFIG)

def send_to_cache(query):
    start = time.perf_counter()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((CACHE_HOST, CACHE_PORT))
            payload = query + "\n<EOQ>\n"
            s.sendall(payload.encode('utf-8'))
            
            res = ""
            while "<EOQ>" not in res:
                chunk = s.recv(1024).decode('utf-8')
                if not chunk:
                    break
                res += chunk
    except Exception as e:
        print(f"[Cache Error] {e}")
        
    return (time.perf_counter() - start) * 1000.0

def send_to_db(query):
    start = time.perf_counter()
    conn = None
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute(query)
        _ = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"[DB Error] {e}")
    finally:
        if conn:
            db_pool.putconn(conn)
        
    return (time.perf_counter() - start) * 1000.0

if __name__ == "__main__":
    queries = []
    
    # 1. Easy: 250 Point Lookups (ID pool 1-50 to ensure cache collisions)
    for _ in range(250):
        s_id = random.randint(1, 50)
        queries.append(f"SELECT student_id, roll_number, name FROM students WHERE student_id = {s_id};")
        
    # 2. Medium: 200 Heavy 3-Way JOINs (ID pool 1-50)
    for _ in range(200):
        s_id = random.randint(1, 50)
        queries.append(f"SELECT s.name, c.course_name, m.marks, m.grade FROM students s JOIN marks m ON s.student_id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE s.student_id = {s_id};")
        
    # 3. Complex: 50 Massive Aggregations (5,000,000 rows scanned)
    for _ in range(50):
        queries.append("SELECT d.department_name, AVG(m.marks) AS avg_score FROM departments d JOIN students s ON d.department_id = s.department_id JOIN marks m ON s.student_id = m.student_id GROUP BY d.department_name;")

    random.shuffle(queries)
    
    print("=" * 65)
    print(f"Executing {len(queries)} mixed queries across 20 concurrent threads...")
    print("=" * 65)
    
    # --- RUN 1: DIRECT POSTGRESQL ---
    print("\n[1/3] Running Direct PostgreSQL queries...")
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        db_latencies = list(executor.map(send_to_db, queries))
    db_wall_time = time.perf_counter() - t0
    db_avg = sum(db_latencies) / len(db_latencies)

    # --- RUN 2: CACHE SERVER (COLD RUN) ---
    print("[2/3] Running Cache Server (Cold Cache - Misses & Coalescing)...")
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        cold_cache_latencies = list(executor.map(send_to_cache, queries))
    cold_wall_time = time.perf_counter() - t0
    cold_avg = sum(cold_cache_latencies) / len(cold_cache_latencies)

    # --- RUN 3: CACHE SERVER (WARM RUN) ---
    print("[3/3] Running Cache Server (Warm Cache - 100% Hits)...")
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        warm_cache_latencies = list(executor.map(send_to_cache, queries))
    warm_wall_time = time.perf_counter() - t0
    warm_avg = sum(warm_cache_latencies) / len(warm_cache_latencies)

    # --- SUMMARY TABLE ---
    print("\n" + "=" * 65)
    print("                      BENCHMARK RESULTS")
    print("=" * 65)
    print(f"{'Target':<22} | {'Wall Time':<12} | {'Avg Latency':<15} | {'Throughput'}")
    print("-" * 65)
    print(f"{'Direct PostgreSQL':<22} | {db_wall_time:>10.3f} s | {db_avg:>12.2f} ms | {len(queries)/db_wall_time:>8.1f} req/s")
    print(f"{'Cache (Cold Start)':<22} | {cold_wall_time:>10.3f} s | {cold_avg:>12.2f} ms | {len(queries)/cold_wall_time:>8.1f} req/s")
    print(f"{'Cache (Warm Cache)':<22} | {warm_wall_time:>10.3f} s | {warm_avg:>12.2f} ms | {len(queries)/warm_wall_time:>8.1f} req/s")
    print("-" * 65)
    if warm_wall_time > 0:
        print(f"Warm Cache Speedup: {db_wall_time / warm_wall_time:.2f}x faster than Direct PostgreSQL")
    print("=" * 65)
    
    
    