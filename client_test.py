import socket
import time
import random
import concurrent.futures

HOST = '127.0.0.1'
PORT = 8080

def send_query(query):
    start_time = time.time()
    try:
        # Create a new TCP socket for each request
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(query.encode('utf-8'))
            
            # Wait for the C++ server to process and reply
            response = s.recv(1024).decode('utf-8').strip()
    except Exception as e:
        response = f"[ERROR] {e}"
        
    latency = (time.time() - start_time) * 1000  # Convert to milliseconds
    return query, response, latency

if __name__ == "__main__":
    # Generate 50 queries targeting only 5 unique keys
    queries = [f"SELECT * FROM users WHERE id = {random.randint(1, 5)}" for _ in range(50)]
    
    print(f"Launching {len(queries)} concurrent requests to {HOST}:{PORT}...\n")
    
    hits = 0
    misses = 0

    # Fire 10 threads simultaneously to create a "Thundering Herd"
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(send_query, queries))

    # Print results sorted by latency
    results.sort(key=lambda x: x[2])
    
    for query, response, latency in results:
        if "HIT" in response:
            hits += 1
        elif "MISS" in response:
            misses += 1
            
        print(f"[{latency:>6.2f} ms] {query:<35} -> {response}")

    print("\n" + "="*40)
    print("           METRICS SUMMARY")
    print("="*40)
    print(f"Total Requests : {len(queries)}")
    print(f"Cache Hits     : {hits}")
    print(f"Cache Misses   : {misses}")
    print(f"Hit Rate       : {(hits / len(queries)) * 100:.1f}%")

    # Call the STATS terminal command
    print("\nFetching Server Stats...")
    _, stats_res, _ = send_query("STATS")
    print(stats_res)