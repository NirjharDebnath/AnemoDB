#pragma once
#include <iostream>
#include <string>
#include <queue>
#include <optional>
#include <atomic>
#include <mutex>
#include <thread>
#include <condition_variable>
#include <chrono> //optional for now

#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>

#include "Cache.hpp"
#include "ThreadSafeQueue.hpp"
#include "ConnectionPool.hpp"

struct Request{
    int client_fd; // client tcp ip or socket descriptor
    std::string query;
};

class CacheEngine {

private:
    Cache cache;
    ConnectionPool db_pool;
    ThreadSafeQueue<Request> taskQueue;
    std::vector<std::thread> workers;
    std::thread listener_thread;
    size_t n_threads;

    int port;
    int server_fd = -1;
    std::atomic<bool> is_running{true};

    // telemetrics atomics
    std::atomic<size_t> total_requests{0};
    std::atomic<size_t> cache_hits{0};
    std::atomic<size_t> cache_misses{0};
    std::atomic<uint64_t> total_processing_time_us{0}; // stored in microseconds
    std::chrono::time_point<std::chrono::steady_clock> server_start_time;

    std::string queryDatabase(const std::string& query) {
        // 1. Borrow a connection from the pool
        auto conn = db_pool.acquire();
        std::string formatted_result;

        try {
            // 2. Start a read-only transactional scope
            pqxx::nontransaction tx(*conn);
            
            // 3. Execute the SQL query
            pqxx::result res = tx.exec(query);
            
            if (res.empty()) {
                formatted_result = "No records found.";
            } else {
                // Format the first row's columns into a pipe-separated string
                for (auto field : res[0]) {
                    formatted_result += field.c_str();
                    formatted_result += " | ";
                }
            }
        } catch (const std::exception &e) {
            db_pool.release(std::move(conn)); // Ensure connection is returned on error
            throw; // Re-throw to trigger cancelReservation in the worker loop
        }

        // 4. Return connection to the pool
        db_pool.release(std::move(conn));
        return formatted_result;
    }

    bool writeAll(int sock_fd, const std::string& data) {
        const char* ptr = data.c_str();
        size_t remaining = data.length();

        while (remaining > 0) {
            ssize_t written = write(sock_fd, ptr, remaining);
            if (written <= 0) {
                return false; // Connection dropped or error
            }
            ptr += written;
            remaining -= written;
        }
        return true;
    }

    std::string readQuery(int client_socket) {
        std::string buffer;
        char chunk[512];
        const std::string delimiter = "<EOQ>";

        while (true) {
            ssize_t bytes_read = read(client_socket, chunk, sizeof(chunk));
            if (bytes_read <= 0) {
                break; // Client closed connection or error
            }

            buffer.append(chunk, bytes_read);

            size_t delim_pos = buffer.find(delimiter);
            if (delim_pos != std::string::npos) {
                // Extract the query up to the delimiter
                std::string query = buffer.substr(0, delim_pos);
                
                // Clean up leading/trailing whitespace
                query.erase(0, query.find_first_not_of(" \n\r\t"));
                query.erase(query.find_last_not_of(" \n\r\t") + 1);
                return query;
            }
        }

        return ""; // Incomplete transmission or client disconnected early
    }

    // worker function to be executed by each threads
    void workerLoop(size_t worker_id) {
        while(true) {
            auto task = taskQueue.pop();
            if (!task) break; 

            // 1. Start latency timer immediately after taking the task
            auto task_start_time = std::chrono::steady_clock::now();
            std::string final_response;

            if (task->query == "STATS") {
                // Return the generated report over TCP
                final_response = generateStatsReport();
            }
            else {
                total_requests++; // Atomic increment
                auto [cacheline, is_leader] = cache.lookupOrReserve(task->query);

                if(is_leader) {
                    try {
                        std::string dbResult = queryDatabase(task->query);
                        cache.completeReservation(cacheline, dbResult);
                        cache_misses++; // Atomic increment
                        final_response = "[CACHE MISS] " + dbResult;
                    } catch (...) {
                        cache.cancelReservation(cacheline);
                        final_response = "[ERROR] DB Fetch Failed";
                    }
                }
                else {
                    std::unique_lock<std::mutex> node_lock(cacheline->node_mtx);
                    if (cacheline->state == NodeState::IN_PROGRESS) {
                        cacheline->node_cv.wait(node_lock, [&]() {
                            return cacheline->state != NodeState::IN_PROGRESS;
                        });
                    }

                    if (cacheline->state == NodeState::READY) {
                        cache_hits++; // Atomic increment
                        final_response = "[CACHE HIT] " + cacheline->value;
                    } else {
                        final_response = "[ERROR] Request Failed";
                    }
                }
            }

            // 2. Stop latency timer right before network transmission
            auto task_end_time = std::chrono::steady_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::microseconds>(task_end_time - task_start_time).count();
            if (task->query != "STATS") {
                total_processing_time_us += duration; // Atomic add
            }

            // Append delimiter and send over network
            final_response += "\n<EOQ>\n";
            writeAll(task->client_fd, final_response);
            close(task->client_fd);
        }
    }

    // Network Listener Loop
    void listenerLoop()
    {
        server_fd = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd < 0)
        {
            perror("Socket creation failed");
            return;
        }

        // Allow immediate port reuse after restarting the server
        int opt = 1;
        setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY;
        address.sin_port = htons(port);

        if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0)
        {
            perror("Bind failed");
            return;
        }

        if (listen(server_fd, 1024) < 0)
        {
            perror("Listen failed");
            return;
        }

        std::cout << ">>> Cache Server listening on port " << port << " <<<\n";

        while (is_running)
        {
            sockaddr_in client_addr{};
            socklen_t addrlen = sizeof(client_addr);

            // Blocking wait for a new client
            int client_socket = accept(server_fd, (struct sockaddr *)&client_addr, &addrlen);

            if (client_socket < 0)
            {
                if (!is_running)
                    break; // Expected error during shutdown
                perror("Accept failed");
                continue;
            }

            char buffer[1024] = {0};
            std::string query = readQuery(client_socket);

            if(!query.empty()) {
                taskQueue.push({client_socket, query});
            }
            else {
                close(client_socket);
            }
        }
    }

public:
    CacheEngine(size_t total_cachelines, size_t n_threads, int port, const std::string& db_conn_str) : cache(total_cachelines), n_threads(n_threads), port(port), db_pool(n_threads, db_conn_str) { // Initialize pool
        
        server_start_time = std::chrono::steady_clock::now(); 
        
        for(size_t i=0; i < n_threads; ++i){
            workers.emplace_back(&CacheEngine::workerLoop, this, i+1);
        }
        listener_thread = std::thread(&CacheEngine::listenerLoop, this);
    }

    //generate telemetrics for the running cache server
    std::string generateStatsReport() {
        auto metrics = cache.getMetrics();
        size_t queue_len = taskQueue.size();
        
        auto now = std::chrono::steady_clock::now();
        auto uptime_sec = std::chrono::duration_cast<std::chrono::seconds>(now - server_start_time).count();
        if (uptime_sec == 0) uptime_sec = 1; // Prevent division by zero

        size_t reqs = total_requests.load();
        size_t hits = cache_hits.load();
        size_t misses = cache_misses.load();
        uint64_t total_time = total_processing_time_us.load();

        double hit_rate = (reqs > 0) ? (static_cast<double>(hits) / reqs) * 100.0 : 0.0;
        double avg_latency = (reqs > 0) ? (static_cast<double>(total_time) / reqs) / 1000.0 : 0.0; // ms
        double throughput = static_cast<double>(reqs) / uptime_sec;

        size_t node_overhead = metrics.current_lines * sizeof(CacheNode);
        size_t total_bytes = node_overhead + metrics.total_payload_bytes;
        double total_kb = total_bytes / 1024.0;

        std::string report = "\n=== SERVER STATS ===\n";
        report += "Uptime          : " + std::to_string(uptime_sec) + " seconds\n";
        report += "Throughput      : " + std::to_string(throughput) + " req/sec\n";
        report += "Avg Latency     : " + std::to_string(avg_latency) + " ms\n\n";
        
        report += "--- MEMORY ---\n";
        report += "Queue Length    : " + std::to_string(queue_len) + " pending tasks\n";
        report += "Cache Lines     : " + std::to_string(metrics.current_lines) + " / " + std::to_string(metrics.max_capacity) + " slots filled\n";
        report += "Directory Size  : " + std::to_string(metrics.directory_size) + " keys mapped\n";
        report += "Estimated Size  : " + std::to_string(total_bytes) + " Bytes (" + std::to_string(total_kb) + " KB)\n\n";

        report += "--- METRICS ---\n";
        report += "Total Requests  : " + std::to_string(reqs) + "\n";
        report += "Cache Hits      : " + std::to_string(hits) + "\n";
        report += "Cache Misses    : " + std::to_string(misses) + "\n";
        report += "Hit Rate        : " + std::to_string(hit_rate) + " %\n";
        report += "====================\n";

        return report;
    }

    ~CacheEngine()
    {
        std::cout << "Initiating shutdown...\n";
        is_running = false;

        // Force accept() to unblock by shutting down the socket
        if (server_fd >= 0) {
            shutdown(server_fd, SHUT_RDWR);
            close(server_fd);
        }

        if (listener_thread.joinable())
            listener_thread.join();

        taskQueue.stop();
        for (auto &worker : workers)
        {
            if (worker.joinable())
                worker.join();
        }
    }
};