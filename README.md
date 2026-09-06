# Anemo DB

**A multi-threaded C++ read-through cache server for PostgreSQL workloads**

<div style="text-align: right;">──── As Fast As The Winds....</div>

![Anemo banner](/assets/mondstadt2.jpg)

![Anemo architecture (light)](/assets/Anemo-system-design-light.png)

<div style="text-align: center;">May the winds of Freedom guide you.<br><br></div>

Anemo DB is a learning-focused systems project that places a TCP cache layer in front of PostgreSQL. It is designed to reduce repeated read-query load, absorb traffic bursts, and expose real-time telemetry for monitoring.

## What Anemo DB Implements

- Multi-threaded TCP server for SQL-over-socket requests
- Read-through cache with `O(1)` lookup + LRU ordering
- TTL-based lazy expiration (no cleanup background thread)
- Request coalescing (single DB fetch for concurrent misses on same key)
- Bounded request queue with fast rejection when overloaded
- Fixed-size PostgreSQL connection pool (`libpqxx`)
- Telemetry endpoints via in-band commands (`STATS`, `STATS_JSON`)
- Flask + Chart.js dashboard for live status and load simulation
- Benchmark and dataset tooling for cache-vs-DB comparisons

## Repository Structure

- `/home/runner/work/AnemoDB/AnemoDB/Cache Components`
  - Core C++ engine: `main.cpp`, `CacheEngine.hpp`, `Cache.hpp`, `ConnectionPool.hpp`, `ThreadSafeQueue.hpp`
- `/home/runner/work/AnemoDB/AnemoDB/Cache Benchmark`
  - SQL schema/data scripts + Python benchmark clients
- `/home/runner/work/AnemoDB/AnemoDB/Cache Monitor`
  - Terminal monitor that polls server stats
- `/home/runner/work/AnemoDB/AnemoDB/Web Dashboard`
  - Flask backend, traffic generator, HTML/CSS/JS dashboard UI
- `/home/runner/work/AnemoDB/AnemoDB/Bash Control`
  - Helper shell scripts to start/stop/check PostgreSQL and run server

## Architecture at a Glance

1. Client sends a SQL query over TCP, terminated with `<EOQ>`.
2. Listener thread accepts and enqueues requests.
3. Worker thread processes request:
   - `STATS`/`STATS_JSON` => telemetry response
   - SQL query => cache lookup/reservation
4. On miss, leader thread fetches from PostgreSQL using pooled connection.
5. Cache line is fulfilled and waiting followers are notified.
6. Response is returned with trailing `<EOQ>` delimiter.

For deeper internals, see `/home/runner/work/AnemoDB/AnemoDB/DOCUMENTATION.md`.

## Protocol

- Request format:
  - `<SQL_QUERY>\n<EOQ>\n`
- Response format:
  - `<PAYLOAD>\n<EOQ>\n`
- Special commands:
  - `STATS`
  - `STATS_JSON`

## Prerequisites

- Linux environment (scripts use `systemctl` + `sudo`)
- PostgreSQL running locally or reachable over network
- C++17 compiler (`g++`)
- `libpqxx` and `libpq`
- Python 3
- Python packages: `flask`, `psycopg2`

## Setup and Run

### 1) Prepare benchmark database (optional but recommended)

```bash
psql -U postgres -d college_db -f "Cache Benchmark/create_db/01_schema.sql"
psql -U postgres -d college_db -f "Cache Benchmark/create_db/02_generate_data.sql"
psql -U postgres -d college_db -f "Cache Benchmark/create_db/03_indexes.sql"
```

### 2) Build server

```bash
g++ -std=c++17 "Cache Components/main.cpp" -o anemo_db -lpqxx -lpq -pthread
```

Or run helper script:

```bash
bash "Bash Control/anemo_db.sh"
```

### 3) Start server

```bash
./anemo_db
```

The admin console prompts for DB and server configuration, then accepts commands:

- `showstats`
- `clear`
- `help`
- `stop`

### 4) Run dashboard

```bash
cd "Web Dashboard"
python web_dashboard.py
```

Open `http://127.0.0.1:5000`.

### 5) Run monitor and benchmarks

```bash
python "Cache Monitor/monitor_cache.py"
python "Cache Benchmark/client_test.py"
python "Cache Benchmark/benchmark_script.py"
python "Cache Benchmark/benchmark_script2.py"
python "Cache Benchmark/benchmark_script3.py"
```

## Dashboard Capabilities

- Live server connectivity status
- Hit rate, throughput, average latency, queue depth, memory, threads
- Throughput and hit/miss charts
- Live cache vs direct-DB latency comparison
- Interactive traffic controls:
  - target mode (`cache`, `db`, `both`)
  - dynamic thread count
  - start/stop load generation

## Benchmark and Dataset Notes

- SQL scripts create a college-style schema with:
  - 6 departments
  - 120 courses
  - 300 faculty rows
  - 1,000,000 students
  - 5,000,000 enrollments
  - 5,000,000 marks
- Benchmarks include mixed query workloads (point lookups, joins, aggregations).

## Current Limitations (from current code)

- Cache server query path is read-focused and intended for benchmark-style read workloads.
- Query result serialization currently returns the first row’s columns as a pipe-separated string.
- Security hardening (auth/TLS/input policy) is not implemented.
- Shell helper scripts are Linux/systemd specific.

## License

No explicit license file is currently present in this repository.
