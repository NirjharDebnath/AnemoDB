# AnemoDB

AnemoDB is a C++ in-memory concurrent cache server with an LRU policy and a built-in strategy to prevent duplicate backend work for the same key (thundering herd protection).

It accepts TCP requests, processes them through a worker pool, and returns:
- `[CACHE MISS] ...` when one thread fetches a key for the first time
- `[CACHE HIT] ...` when later requests reuse cached data
- `[ERROR] ...` on failures

## Current implementation highlights

- In-memory LRU cache (`Cache.hpp`)
- Per-key reservation states: `IN_PROGRESS`, `READY`, `FAILED`
- Follower waiting via per-node condition variable while a leader fetches data
- Thread-safe task queue for request dispatch (`ThreadSafeQueue.hpp`)
- TCP listener + worker thread pool engine (`CacheEngine.hpp`)
- Python concurrent client test script (`client_test.py`)

## Project structure

- `/home/runner/work/AnemoDB/AnemoDB/main.cpp`  
  Starts `CacheEngine(10, 4, 8080)` and keeps the server alive.
- `/home/runner/work/AnemoDB/AnemoDB/CacheEngine.hpp`  
  Networking, worker loop, queue consumption, and simulated DB lookup.
- `/home/runner/work/AnemoDB/AnemoDB/Cache.hpp`  
  LRU cache directory/list and reservation lifecycle.
- `/home/runner/work/AnemoDB/AnemoDB/ThreadSafeQueue.hpp`  
  Blocking queue used between listener and workers.
- `/home/runner/work/AnemoDB/AnemoDB/client_test.py`  
  Fires concurrent requests and prints hit/miss metrics.

## Request flow

1. Listener accepts a TCP client connection and reads one query string.
2. Request is pushed into the shared queue.
3. A worker pops the task and checks cache:
   - miss: reserves key (`IN_PROGRESS`) and becomes leader
   - hit while `IN_PROGRESS`: waits as follower
   - hit while `READY`: returns cached value
4. Leader performs backend fetch (currently simulated) and marks `READY` or `FAILED`.
5. Waiting followers are notified and respond accordingly.

## Requirements

- Linux-like environment (uses POSIX sockets: `sys/socket.h`, `netinet/in.h`, `unistd.h`)
- C++17-compatible compiler
- Python 3 (for `client_test.py`)

## Build and run

From `/home/runner/work/AnemoDB/AnemoDB`:

```bash
g++ -std=c++17 -pthread main.cpp -o anemodb_server
./anemodb_server
```

The server listens on port `8080` by default.

## Load/concurrency test

In a second terminal, from `/home/runner/work/AnemoDB/AnemoDB`:

```bash
python3 client_test.py
```

The script sends 50 concurrent requests over a smaller key space and prints latency, cache hit/miss counts, and hit rate.

## Protocol notes

- Send plain text query bytes over TCP (single request per connection).
- Special query: `STATS` returns a basic server status message.

## Limitations (current code)

- Cache is in-memory only (no persistence)
- Backend lookup is mocked (`queryDatabase` sleeps then returns formatted text)
- No authentication, encryption, or distributed replication
