
# Architecture & System Design Documentation

## 1. Introduction & System Context

Modern web applications heavily rely on relational databases. Under extreme load, high-frequency read queries can exhaust database CPU, memory, and connection limits. Anemo DB solves this by introducing a localized, in-memory caching tier. It accepts SQL queries as TCP string payloads, computes a hash map lookup, and returns the cached result.

To achieve production-grade stability, Anemo DB must navigate critical concurrency challenges: race conditions, unbounded queue scaling, lock contention, and the Thundering Herd problem.

## 2. Request Coalescing (Solving the Thundering Herd)

### The Problem

When a highly popular query (e.g., an aggregation query returning average department marks) expires from the cache, hundreds of worker threads might simultaneously register a "cache miss". If all threads blindly forward the query to PostgreSQL, the database is instantly paralyzed by duplicate heavy computations.

### The Solution: Leader Election

Anemo DB implements a "lookup or reserve" synchronization primitive.

1. When a thread misses the cache, it atomically inserts a `CacheNode` with the state `NodeState::IN_PROGRESS`.


2. This first thread becomes the **Leader** and proceeds to query PostgreSQL.


3. Subsequent threads querying the same key discover the `IN_PROGRESS` node. Instead of querying the database, they wait on a node-specific condition variable (`std::condition_variable node_cv`).


4. When the Leader completes the DB fetch, it writes the payload to the node, sets the state to `NodeState::READY`, and calls `node_cv.notify_all()`, instantly fulfilling all waiting threads.



### Mathematical Benefit

If $N$ concurrent requests hit an expired key, the database load is reduced from $O(N)$ to $O(1)$.

## 3. Memory Management: $O(1)$ LRU Eviction & Lazy TTL

### The Problem

An unbounded cache will eventually consume all system RAM. Conversely, a cache that never expires data will serve stale information.

### LRU Eviction Architecture

Anemo DB maintains a maximum cacheline capacity (e.g., 50 entries). It combines two data structures:

* A doubly-linked list (`std::list<std::shared_ptr<CacheNode>>`) to maintain chronological order.


* A Hash Map (`std::unordered_map`) storing iterators to the linked list for $O(1)$ lookup.



When a capacity threshold is reached, the `evictReadyNode()` function targets the tail of the list. It iterates backward using a standard forward iterator (`--it`) to safely avoid `std::reverse_iterator` segmentation faults.

### Lazy Expiration (TTL)

Active TTL countdowns require background threads that constantly lock the cache to delete nodes, ruining read performance. Instead, Anemo DB uses **Passive Lazy Expiration**.
When a cache hit occurs, the engine evaluates:


$$\text{isValid} = (\text{CurrentTime} \leq \text{ExpirationTime})$$


If the node is expired, the worker thread silently erases the iterators, deducts the payload memory from the atomic tracker, and falls through to the "Cache Miss" leader-election logic. Un-requested expired nodes simply sink to the bottom of the LRU list and are efficiently garbage-collected during standard eviction.

## 4. Stability via Bounded Queues & Load Shedding

### The Problem

During catastrophic traffic spikes, a non-blocking TCP listener will push tasks into the `ThreadSafeQueue` faster than worker threads can clear them. An unbounded queue grows infinitely, causing the OS to invoke the OOM Killer.

### The Solution: Queue Bounds and Fast Rejection

The `ThreadSafeQueue` is strictly bounded by a `max_capacity`. Using Little's Law ($L = \lambda W$), establishing a hard limit on queue size ($L$) forces a mathematical bound on maximum wait time ($W$).

If the listener thread attempts to `push()` a task when `queue.size() >= max_capacity`, the operation returns `false`. The networking engine immediately executes a **Load Shedding** maneuver: sending `[ERROR] SERVER_BUSY_QUEUE_FULL` to the client and closing the TCP socket. This fail-fast mechanism prevents memory exhaustion and keeps the server responsive.

## 5. Telemetry & Lock-Free Accounting

To provide real-time dashboard analytics without slowing down the caching engine, Anemo DB avoids locking for metrics.
Variables such as `total_requests`, `cache_hits`, `total_processing_time_us`, and `active_workers` are strictly declared as `std::atomic`.

When the dashboard requests metrics via the `STATS_JSON` TCP command, the server generates a structured JSON payload detailing throughput, memory utilization, average latency, and hit rates. This data is seamlessly plotted over time by the `web_dashboard.py` utility via Chart.js.