import socket
import time
import random
import concurrent.futures

HOST = '127.0.0.1'
PORT = 8080

def send_query(query):
    start_time = time.time()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            
            payload = query + "\n<EOQ>\n"
            s.sendall(payload.encode('utf-8'))
            
            response_data = ""
            while "<EOQ>" not in response_data:
                chunk = s.recv(1024).decode('utf-8')
                if not chunk:
                    break
                response_data += chunk
                
            clean_response = response_data.replace("<EOQ>", "").strip()
            
    except Exception as e:
        clean_response = f"[ERROR] {e}"
        
    latency = (time.time() - start_time) * 1000 
    return query, clean_response, latency

if __name__ == "__main__":
    # Generate a mix of queries from 04_test_queries.sql
    queries = []
    
    # 1. Point Lookups (Fast DB execution)
    for _ in range(20):
        student_id = random.randint(10000, 10005) # Narrow range to force cache collisions
        queries.append(f"SELECT * FROM students WHERE student_id = {student_id};")
        
    # 2. Heavy JOIN Queries (Slow DB execution)
    for _ in range(20):
        student_id = random.randint(12340, 12345)
        queries.append(f"SELECT s.name, c.course_name, m.marks, m.grade FROM students s JOIN marks m ON s.student_id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE s.student_id = {student_id};")
        
    # 3. Aggregation Queries
    for _ in range(10):
        queries.append("SELECT d.department_name, AVG(m.marks) as avg_marks FROM departments d JOIN students s ON d.department_id = s.department_id JOIN marks m ON s.student_id = m.student_id GROUP BY d.department_name;")

    # Shuffle to simulate unpredictable traffic
    random.shuffle(queries)
    
    print(f"Launching {len(queries)} concurrent requests to {HOST}:{PORT}...\n")
    
    hits = 0
    misses = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(send_query, queries))

    results.sort(key=lambda x: x[2])
    
    for query, response, latency in results:
        if "HIT" in response:
            hits += 1
        elif "MISS" in response:
            misses += 1
            
        snippet = response[:70] + "..." if len(response) > 70 else response
        # Condense query string for clean terminal output
        q_snippet = query[:35] + "..." if len(query) > 35 else query
        print(f"[{latency:>6.2f} ms] {q_snippet:<40} -> {snippet}")

    print("\n" + "="*40)
    print("           METRICS SUMMARY")
    print("="*40)
    print(f"Total Requests : {len(queries)}")
    print(f"Cache Hits     : {hits}")
    print(f"Cache Misses   : {misses}")
    print(f"Hit Rate       : {(hits / len(queries)) * 100:.1f}%")

    print("\nFetching Server Telemetry...")
    _, stats_res, _ = send_query("STATS")
    print(stats_res)
    