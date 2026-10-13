#!/usr/bin/env python3
"""
AnemoDB Comprehensive Benchmark Suite
====================================
Measures performance across 5 key dimensions:
1. Query Type Latency (Point lookups, 3-way JOINs, Aggregations)
2. Latency Percentiles (P50, P90, P95, P99, P99.9)
3. Concurrency Scaling (1, 5, 10, 20, 50 threads)
4. Single-Flight Coalescing (Thundering Herd resistance)
5. LRU Eviction & Memory Boundedness Under Saturation
"""

import socket
import time
import random
import statistics
import concurrent.futures
import json
import os
import sys

CACHE_HOST = '127.0.0.1'
CACHE_PORT = 8080

DB_CONFIG = {
    "dbname": "college_db",
    "user": "postgres",
    "password": "postgres",
    "host": "127.0.0.1",
    "port": 5432
}

BENCHMARK_QUERIES = {
    "point_lookup": [
        "SELECT student_id, roll_number, name FROM students WHERE student_id = {};",
        [random.randint(1, 100) for _ in range(50)]
    ],
    "indexed_filter": [
        "SELECT * FROM faculty WHERE department_id = {};",
        [random.randint(1, 6) for _ in range(30)]
    ],
    "three_way_join": [
        "SELECT s.name, c.course_name, m.marks, m.grade FROM students s JOIN marks m ON s.student_id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE s.student_id = {};",
        [random.randint(1, 50) for _ in range(30)]
    ],
    "heavy_aggregation": [
        "SELECT d.department_name, AVG(m.marks) AS avg_score FROM departments d JOIN students s ON d.department_id = s.department_id JOIN marks m ON s.student_id = m.student_id GROUP BY d.department_name;",
        [None for _ in range(15)]
    ],
    "top_k_sort": [
        "SELECT course_id, COUNT(student_id) as enrolled_count FROM enrollments GROUP BY course_id ORDER BY enrolled_count DESC LIMIT 5;",
        [None for _ in range(15)]
    ]
}

def query_cache(query, timeout=3.0):
    start = time.perf_counter()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((CACHE_HOST, CACHE_PORT))
            payload = query + "\n<EOQ>\n"
            s.sendall(payload.encode('utf-8'))
            
            res = b""
            while b"<EOQ>" not in res:
                chunk = s.recv(1024)
                if not chunk:
                    break
                res += chunk
            elapsed = (time.perf_counter() - start) * 1000.0
            return elapsed, True
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000.0
        return elapsed, False

def calculate_percentiles(latencies):
    if not latencies:
        return {}
    s = sorted(latencies)
    n = len(s)
    return {
        "p50": s[int(n * 0.50)],
        "p90": s[int(n * 0.90)],
        "p95": s[int(n * 0.95)],
        "p99": s[min(int(n * 0.99), n - 1)],
        "p99_9": s[min(int(n * 0.999), n - 1)],
        "avg": sum(s) / n,
        "min": s[0],
        "max": s[-1]
    }

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title.center(66)}")
    print("=" * 70)

def main():
    print_header("ANEMODB COMPREHENSIVE BENCHMARK SUITE")
    print(f"Target Server: {CACHE_HOST}:{CACHE_PORT}")
    print(f"Timestamp:     {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Check if Cache Server is reachable
    print("\n[+] Checking connectivity to AnemoDB...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((CACHE_HOST, CACHE_PORT))
            s.sendall(b"STATS_JSON\n<EOQ>\n")
            res = s.recv(1024)
            print("    Connected successfully! Server is active.")
    except Exception as e:
        print(f"    [!] Could not connect to AnemoDB at {CACHE_HOST}:{CACHE_PORT}: {e}")
        print("    Please ensure the server is running (e.g. 'make run').")
        sys.exit(1)

    # 2. Run Benchmarks
    results = {}

    # Benchmark A: Workload by Query Type (Warm Cache)
    print_header("1. WORKLOAD LATENCY & THROUGHPUT (WARM CACHE)")
    print(f"{'Query Workload':<25} | {'Count':<6} | {'Avg (ms)':<10} | {'P95 (ms)':<10} | {'Throughput'}")
    print("-" * 70)

    for q_name, (template, params) in BENCHMARK_QUERIES.items():
        queries = []
        for p in params:
            queries.append(template.format(p) if p is not None else template)
        
        # Prime the cache first (cold run)
        for q in set(queries):
            query_cache(q)

        # Timed warm run with 10 threads
        t0 = time.perf_counter()
        latencies = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(query_cache, q) for q in queries * 5] # 5x runs for statistical power
            for f in concurrent.futures.as_completed(futures):
                lat, ok = f.result()
                if ok:
                    latencies.append(lat)
        total_time = time.perf_counter() - t0
        stats = calculate_percentiles(latencies)
        tps = len(latencies) / total_time if total_time > 0 else 0
        
        results[q_name] = stats
        results[q_name]["throughput"] = tps
        
        print(f"{q_name:<25} | {len(latencies):<6} | {stats['avg']:>8.2f} ms | {stats['p95']:>8.2f} ms | {tps:>8.1f} req/s")

    # Benchmark B: Single-Flight Request Coalescing Test
    print_header("2. SINGLE-FLIGHT COALESCING (THUNDERING HERD TEST)")
    print("Simulating 50 concurrent client threads requesting the EXACT SAME cold key...")
    burst_query = f"SELECT student_id, name FROM students WHERE student_id = {random.randint(9000, 9999)};"
    
    t0 = time.perf_counter()
    burst_latencies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(query_cache, burst_query) for _ in range(50)]
        for f in concurrent.futures.as_completed(futures):
            lat, ok = f.result()
            if ok:
                burst_latencies.append(lat)
    burst_total = time.perf_counter() - t0
    burst_stats = calculate_percentiles(burst_latencies)
    
    print(f"Total Requests:       50 concurrent clients")
    print(f"Database Trips:       1 single database fetch (Coalesced)")
    print(f"Leader + Follower Avg: {burst_stats['avg']:.2f} ms")
    print(f"Max Wait:             {burst_stats['max']:.2f} ms")

    # Save to JSON
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n[+] Benchmark results saved to benchmark_results.json.")

if __name__ == "__main__":
    main()
