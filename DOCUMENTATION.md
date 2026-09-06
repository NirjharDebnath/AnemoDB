# Anemo DB - Technical Documentation

## 1. System Purpose

Anemo DB is a learning-oriented cache server that sits between query clients and PostgreSQL. It targets repeated read-query workloads where cache reuse can reduce DB pressure and improve latency.

The server accepts SQL-like text requests over TCP, caches query-to-response mappings in memory, and returns cached or freshly-fetched results using a delimiter-framed protocol.

---

## 2. High-Level Components

## 2.1 Cache Server (C++)

Location: `/home/runner/work/AnemoDB/AnemoDB/Cache Components`

- `main.cpp`: interactive admin startup console and runtime command loop
- `CacheEngine.hpp`: listener thread, worker pool, DB fetch path, telemetry generation
- `Cache.hpp`: in-memory cache state, LRU ordering, TTL, coalescing primitives
- `ConnectionPool.hpp`: fixed-size pool of `pqxx::connection`
- `ThreadSafeQueue.hpp`: bounded producer/consumer queue for incoming requests

## 2.2 Monitoring and UI

- Terminal monitor: `/home/runner/work/AnemoDB/AnemoDB/Cache Monitor/monitor_cache.py`
- Web dashboard backend: `/home/runner/work/AnemoDB/AnemoDB/Web Dashboard/web_dashboard.py`
- Dashboard load generator: `/home/runner/work/AnemoDB/AnemoDB/Web Dashboard/traffic_generator.py`
- Dashboard frontend: HTML/CSS/JS in `/home/runner/work/AnemoDB/AnemoDB/Web Dashboard`

## 2.3 Benchmark and Data Tooling

Location: `/home/runner/work/AnemoDB/AnemoDB/Cache Benchmark`

- SQL schema/data/index/query scripts in `create_db/`
- Concurrent benchmark scripts for direct DB vs cache comparisons

---

## 3. Request/Response Protocol

All clients communicate over TCP using `<EOQ>` as end-of-query / end-of-response marker.

## 3.1 Request frame

`<QUERY_TEXT>\n<EOQ>\n`

## 3.2 Response frame

`<RESPONSE_TEXT>\n<EOQ>\n`

## 3.3 Supported request types

1. SQL query text (normal cache path)
2. `STATS` (human-readable telemetry report)
3. `STATS_JSON` (JSON telemetry payload)

---

## 4. Runtime Flow

1. `CacheEngine` starts worker threads and a listener thread.
2. Listener accepts sockets, reads until `<EOQ>`, and enqueues tasks.
3. If queue is full, server immediately replies `[ERROR] SERVER_BUSY_QUEUE_FULL`.
4. Worker pops task:
   - for `STATS` or `STATS_JSON`, it responds with generated telemetry
   - for SQL query, it executes cache logic:
     - lookup existing cache line
     - perform lazy TTL expiration check
     - reserve placeholder if miss
5. On miss, leader thread queries PostgreSQL and fills cache line.
6. Waiting follower threads are released and reuse leader result.
7. Worker appends `<EOQ>` to output, writes response, closes socket.

---

## 5. Core Cache Design

## 5.1 Data structures

- `std::list<std::shared_ptr<CacheNode>> cacheLines`
  - maintains LRU order
- `std::unordered_map<std::string, list::iterator> cacheDirectory`
  - maps key to list node for `O(1)` access

## 5.2 Cache node state machine

`NodeState`:

- `IN_PROGRESS`: reservation exists; leader is fetching DB result
- `READY`: value is available for reads
- `FAILED`: leader failed; followers receive error

Each node has:

- key, value
- per-node mutex + condition variable
- expiration timestamp

## 5.3 LRU behavior

- Hits/matches move node to front of list.
- When capacity is reached, eviction scans from tail and removes first `READY` node.
- `IN_PROGRESS` nodes are protected from eviction.

## 5.4 TTL behavior (lazy expiration)

- No background cleanup thread.
- Expiration is checked during lookup.
- Expired `READY` nodes are removed on-demand, then treated as miss.

---

## 6. Concurrency Model

## 6.1 Listener and workers

- 1 listener thread handles accept/read/enqueue.
- `N` worker threads process tasks from queue.

## 6.2 Queue backpressure

- `ThreadSafeQueue` has configurable bounded capacity (default 5000).
- Prevents unbounded memory growth during bursts.

## 6.3 Request coalescing

For identical concurrent misses:

- First thread creates `IN_PROGRESS` reservation (leader).
- Followers wait on reservation node condition variable.
- Leader stores value and `notify_all()` on completion.
- DB load reduces from many duplicate queries to one per key per miss window.

## 6.4 Metrics without heavy locking

Server tracks counters using atomics (e.g., total requests, hits, misses, active workers, processing time).

---

## 7. PostgreSQL Integration

- Connection pool size equals worker-thread count.
- Worker acquires one pooled connection for DB fetch on miss.
- Query execution uses `pqxx::nontransaction`.
- On completion/failure, connection is returned to pool.

---

## 8. Telemetry System

## 8.1 `STATS` (formatted output)

Includes:

- uptime
- throughput (sliding calculation)
- average latency
- active/total worker count
- queue depth
- cache line usage and directory size
- payload bytes, node overhead, estimated memory
- total requests, hits, misses, hit rate

## 8.2 `STATS_JSON` (dashboard payload)

Returns structured metrics for API consumers and dashboard rendering.

## 8.3 Monitor script

`monitor_cache.py` polls `STATS` every 4 seconds and renders terminal dashboard panels.

---

## 9. Web Dashboard

Backend (`web_dashboard.py`):

- `GET /api/stats`: combines cache telemetry + traffic generator metrics
- `POST /api/traffic/control`: starts/stops traffic generation; configures mode + threads

Traffic generator (`traffic_generator.py`):

- modes: `cache`, `db`, `both`
- tracks per-target average latencies and request counts
- manages dynamic worker threads for synthetic load

Frontend (`templates/index.html`, `static/script.js`, `static/style.css`):

- connectivity indicator
- metric cards
- throughput chart
- hit/miss doughnut chart
- latency comparison chart (cache vs PostgreSQL)
- theme toggle (dark/light)
- live load controls

---

## 10. Benchmark and Dataset Tooling

## 10.1 SQL data setup (`create_db/`)

- `01_schema.sql`: creates 6-table college schema
- `02_generate_data.sql`: inserts large synthetic data
- `03_indexes.sql`: adds query-supporting indexes
- `04_test_queries.sql`: representative workload mix
- `reset.sql`: full schema reset

## 10.2 Python benchmark scripts

- `benchmark_script.py`: 50 mixed queries, 10 threads, 3-phase comparison
- `benchmark_script2.py`: 500 mixed queries, 20 threads, heavier workload
- `benchmark_script3.py`: interactive traffic simulation to cache or DB
- `client_test.py`: concurrent cache query test + hit/miss summary + stats fetch

---

## 11. Operational Commands

## 11.1 Build

```bash
g++ -std=c++17 "Cache Components/main.cpp" -o anemo_db -lpqxx -lpq -pthread
```

## 11.2 Helper scripts

- `Bash Control/anemo_db.sh` - start PostgreSQL service, build, run server
- `Bash Control/check_status_db.sh` - PostgreSQL service status
- `Bash Control/stop_db.sh` - stop PostgreSQL service

---

## 12. Known Behavior and Limitations

- Cache path is read-oriented and intended for query result reuse.
- Current DB result serialization returns first row fields as pipe-separated output.
- Cache endpoint accepts raw SQL text over plain TCP (no auth/TLS/policy enforcement).
- Helper shell scripts assume Linux + `systemctl` + `sudo`.
- Dashboard auto-refresh loop runs at very high frequency in current JS configuration.

---

## 13. Dependency Summary

### C++ side

- C++17 toolchain
- POSIX sockets
- `libpqxx`, `libpq`
- `pthread`

### Python side

- `flask`
- `psycopg2`
- Python stdlib (`socket`, `threading`, `time`, `json`, etc.)

### Frontend side

- Chart.js (CDN)

---

## 14. Intended Scope

This repository is implemented as a concept-learning systems project (caching, concurrency, sockets, telemetry, and benchmarking), prioritizing architectural clarity and behavior visibility.
