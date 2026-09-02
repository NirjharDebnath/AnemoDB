# Anemo DB

**A High-Performance C++ Multi-Threaded LRU Cache Server for PostgreSQL**

<div style="text-align: right;">
    ──── As Fast As The Winds....
</div>


![mondstadt image](./assets/mondstadt.jpg)

<div style="text-align: right;">
    May the winds of Freedom guide you.
</div>


Developed as a systems engineering project. Anemo DB is a robust, lock-optimized, read-only cache layer designed to sit in front of PostgreSQL, capable of absorbing massive traffic spikes, preventing database melt-downs, and serving telemetry in real-time.

## Key Features

* **Thread-Safe Bounded Task Queue:** Prevents Out-Of-Memory (OOM) crashes via fast-rejection load shedding.


* **Request Coalescing (Thundering Herd Protection):** Employs a leader-election model so concurrent cache misses for the same query only hit the database once.


* **$O(1)$ LRU Eviction:** Fast, deterministic memory management using a doubly-linked list and hash map combination.


* **Lazy TTL Expiration:** Efficient, zero-background-thread cache invalidation to maintain data freshness.


* **Persistent Connection Pooling:** Eliminates TCP handshake latency by maintaining a fixed pool of `libpqxx` connections.


* **Real-Time Telemetry & Web Console:** Lock-free atomic metric gathering streamed over TCP to a Flask/Chart.js web dashboard.



## Repository Structure

The project is organized into distinct modules for database management, caching logic, benchmarking, and telemetry monitoring:

* **`/Cache Components`**: Contains the core C++ engine (`Cache.hpp`, `CacheEngine.hpp`, `ConnectionPool.hpp`, `ThreadSafeQueue.hpp`, `main.cpp`).
* **`/Cache Benchmark`**: Holds the PostgreSQL data generation and schema SQL scripts (`01_schema.sql` to `04_test_queries.sql`, `reset.sql`).
* **`/Web Dashboard`**: Contains the Flask telemetry application (`web_dashboard.py`) and its static assets (`script.js`, `style.css`, `index.html`).
* **Root Python Scripts**: Various load-testing tools including `benchmark_script.py`, `benchmark_script2.py`, `benchmark_script3.py`, and `monitor_cache.py`.

## Installation & Setup

### 1. Database Preparation

Initialize the PostgreSQL testing environment using the provided SQL scripts. This generates 1,000,000 students and 5,000,000 enrollment/mark records for heavy load testing:

```bash
psql -U postgres -d college_db -f "Cache Benchmark/01_schema.sql"
psql -U postgres -d college_db -f "Cache Benchmark/02_generate_data.sql"
psql -U postgres -d college_db -f "Cache Benchmark/03_indexes.sql"

```

### 2. Compilation

Compile the C++ server with C++17, ensuring `libpqxx` and `pthread` are linked.

```bash
g++ -std=c++17 "Cache Components/main.cpp" -o anemo_db -lpqxx -lpq -pthread

```

### 3. Running the Server

Execute the binary. You will be prompted via an interactive CLI to configure the database credentials, cache capacity, worker threads (e.g., 8), server port (default 8080), and TTL duration (e.g., 60 seconds).

```bash
./anemo_db

```

### 4. Starting the Telemetry Dashboard

In a separate terminal, launch the Flask monitoring dashboard to visualize throughput, memory usage, and queue length in real time.

```bash
python "Web Dashboard/web_dashboard.py"

```

### 5. Running Benchmarks

Use the multi-threaded Python benchmark scripts to simulate traffic. `benchmark_script2.py` pushes 500 mixed queries (point lookups, heavy JOINs, massive aggregations) across 20 concurrent threads to calculate the cache speedup against direct PostgreSQL.

```bash
python benchmark_script2.py

```

---