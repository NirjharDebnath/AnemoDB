import socket
import time
import random
import sys
import psycopg2
from psycopg2 import pool

# Configuration
CACHE_HOST = '127.0.0.1'
CACHE_PORT = 8080

DB_CONFIG = {
    "dbname": "college_db",
    "user": "postgres",
    "password": "postgres", # Update to match your local setup
    "host": "127.0.0.1",
    "port": 5432
}

# Pre-defined Query Templates (Mixing easy, medium, and heavy loads)
QUERY_TEMPLATES = [
    # Easy: Point Lookups
    ("EASY", "SELECT student_id, roll_number, name FROM students WHERE student_id = {};"),
    ("EASY", "SELECT * FROM faculty WHERE department_id = {};"),
    
    # Medium: Multi-Table JOINs
    ("MEDIUM", "SELECT s.name, c.course_name, m.marks, m.grade FROM students s JOIN marks m ON s.student_id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE s.student_id = {};"),
    ("MEDIUM", "SELECT c.course_name, f.name FROM courses c JOIN faculty f ON c.department_id = f.department_id WHERE c.course_id = {};"),
    
    # Complex: Massive Aggregations (No format parameters needed)
    ("COMPLEX", "SELECT d.department_name, AVG(m.marks) AS avg_score FROM departments d JOIN students s ON d.department_id = s.department_id JOIN marks m ON s.student_id = m.student_id GROUP BY d.department_name;"),
    ("COMPLEX", "SELECT course_id, COUNT(student_id) as enrolled_count FROM enrollments GROUP BY course_id ORDER BY enrolled_count DESC LIMIT 5;")
]

def generate_query():
    q_type, q_template = random.choice(QUERY_TEMPLATES)
    
    if q_type == "EASY" or q_type == "MEDIUM":
        if "student_id =" in q_template:
            # Target IDs 1-100 to force frequent cache collisions
            query = q_template.format(random.randint(1, 100))
        elif "department_id =" in q_template:
            query = q_template.format(random.randint(1, 6))
        elif "course_id =" in q_template:
            query = q_template.format(random.randint(1, 120))
    else:
        query = q_template
        
    return q_type, query

def query_cache(query):
    start = time.perf_counter()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((CACHE_HOST, CACHE_PORT))
            s.sendall((query + "\n<EOQ>\n").encode('utf-8'))
            
            res = ""
            while "<EOQ>" not in res:
                chunk = s.recv(1024).decode('utf-8')
                if not chunk: break
                res += chunk
            clean_res = res.replace("<EOQ>", "").strip()
    except Exception as e:
        clean_res = f"[CACHE ERROR] {e}"
        
    latency = (time.perf_counter() - start) * 1000.0
    return clean_res, latency

def query_db(query, db_pool):
    start = time.perf_counter()
    conn = None
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute(query)
        records = cur.fetchall()
        cur.close()
        clean_res = f"Returned {len(records)} rows"
    except Exception as e:
        clean_res = f"[DB ERROR] {e}"
    finally:
        if conn:
            db_pool.putconn(conn)
            
    latency = (time.perf_counter() - start) * 1000.0
    return clean_res, latency

if __name__ == "__main__":
    print("========================================")
    print("   LIVE CACHE & DB TRAFFIC SIMULATOR    ")
    print("========================================")
    
    target_choice = input("Target system (1 for Cache Server, 2 for Direct DB): ").strip()
    iter_choice = input("Number of queries (Enter a number, or type 'inf' for continuous loop): ").strip()
    
    target_is_cache = (target_choice == '1')
    
    try:
        max_iters = float('inf') if iter_choice.lower() == 'inf' else int(iter_choice)
    except ValueError:
        print("Invalid input. Defaulting to 10 iterations.")
        max_iters = 10

    db_pool = None
    if not target_is_cache:
        print("Initializing DB Connection Pool...")
        db_pool = psycopg2.pool.ThreadedConnectionPool(minconn=1, maxconn=5, **DB_CONFIG)
        
    print(f"\nStarting traffic generation to {'Cache Server' if target_is_cache else 'PostgreSQL'}...")
    print("Press CTRL+C to stop manually.\n")
    print(f"{'TYPE':<10} | {'LATENCY':<10} | {'QUERY / RESULT'}")
    print("-" * 70)
    
    count = 0
    try:
        while count < max_iters:
            q_type, sql = generate_query()
            
            if target_is_cache:
                result, latency = query_cache(sql)
            else:
                result, latency = query_db(sql, db_pool)
                
            q_snippet = sql[:30] + "..." if len(sql) > 30 else sql
            r_snippet = result[:30] + "..." if len(result) > 30 else result
            
            print(f"{q_type:<10} | {latency:>7.2f} ms | {q_snippet} -> {r_snippet}")
            
            count += 1
            time.sleep(0.05) # Slight delay to make the terminal output readable
            
    except KeyboardInterrupt:
        print("\n\nSimulation stopped by user.")
        
    print(f"\nCompleted {count} requests.")