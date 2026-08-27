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

struct Request{
    int client_fd; // client tcp ip or socket descriptor
    std::string query;
};

class CacheEngine
{
private:
    Cache cache;
    ThreadSafeQueue<Request> taskQueue;
    std::vector<std::thread> workers;
    std::thread listener_thread;
    size_t n_threads;

    int port;
    int server_fd = -1;
    std::atomic<bool> is_running{true};

    // Simulated DB query
    std::string queryDatabase(const std::string& query) {
        std::this_thread::sleep_for(std::chrono::milliseconds(200)); // Simulated DB latency
        return "DB_RESULT_FOR[" + query + "]";
    }

    // worker function to be executed by each threads
    void workerLoop(size_t worker_id) {
        while(true) {
            auto task = taskQueue.pop();
            if (!task) {
                break; // if empty queue
            }

            std::string final_response;

            // stats check command
            if (task->query =="STATS") {
                final_response = "STATS: Cache is still running.... \n";
            }

            else{

                auto [cacheline, is_leader] = cache.lookupOrReserve(task->query);

                if(is_leader){
                    // leader went for db query after reservation in cache memory
                    std::cout << "[Worker " << worker_id << "] Cache MISS (Leader) for Client " 
                            << task->client_fd << " -> Fetching from DB...\n";

                    try {
                        std::string dbResult = queryDatabase(task->query);
                        cache.completeReservation(cacheline, dbResult);

                        final_response = "[CACHE MISS] " + dbResult;
                    } catch (...) {
                        cache.cancelReservation(cacheline);
                        final_response = "[ERROR] DB Fetch Failed";
                    }
                }

                else{
                    // follower thread hits the cache and checks if its cacheline value is in IN_PROGRESS or READY state
                    // Lock this specific node to check or wait for completion
                    std::unique_lock<std::mutex> node_lock(cacheline->node_mtx);

                    if (cacheline->state == NodeState::IN_PROGRESS) {
                        std::cout << "[Worker " << worker_id << "] IN-FLIGHT wait (Follower) for Client " << task->client_fd << " on query: " << task->query << "\n";
                        
                        // Sleep until the leader completes or fails the fetch
                        cacheline->node_cv.wait(node_lock, [&]() {
                            return cacheline->state != NodeState::IN_PROGRESS;
                        });
                    }

                    if (cacheline->state == NodeState::READY) {
                        final_response = "[CACHE HIT] " + cacheline->value;
                    } else {
                        final_response = "[ERROR] Request Failed";
                    }
                }
            }

            final_response += "\n";
            write(task->client_fd, final_response.c_str(), final_response.length());
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
            ssize_t bytes_read = read(client_socket, buffer, sizeof(buffer) - 1);

            if (bytes_read > 0)
            {
                std::string query(buffer);
                // Strip newline characters sent by telnet or python sockets
                query.erase(query.find_last_not_of(" \n\r\t") + 1);

                taskQueue.push({client_socket, query});
            }
            else
            {
                close(client_socket); // Close if empty request
            }
        }
    }

public:
    CacheEngine(size_t total_cachelines, size_t n_threads, int port) : cache(total_cachelines), n_threads(n_threads), port(port) {
        for(size_t i=0; i < n_threads; ++i){
            workers.emplace_back(&CacheEngine::workerLoop, this, i+1);
        }
        // Spawn network listener
        listener_thread = std::thread(&CacheEngine::listenerLoop, this);
    }

    ~CacheEngine()
    {
        std::cout << "Initiating shutdown...\n";
        is_running = false;

        // Force accept() to unblock by shutting down the socket
        if (server_fd >= 0)
        {
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