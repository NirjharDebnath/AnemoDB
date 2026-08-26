#pragma once
#include <iostream>
#include <string>
#include <queue>
#include <optional>
#include <mutex>
#include <thread>
#include <condition_variable>
#include <chrono> //optional for now

#include "Cache.hpp"
#include "ThreadSafeQueue.hpp"

struct Request{
    int client_id; // future client tcp ip or socket descriptor
    std::string query;
};

class CacheEngine
{
private:
    Cache cache;
    ThreadSafeQueue<Request> taskQueue;
    std::vector<std::thread> workers;
    size_t n_threads;

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
                break;
            }

            auto cachedResult = cache.get(task->query);

            if(cachedResult){
                std::cout << "[Worker " << worker_id << "] Cache HIT  for Client " << task->client_id << " -> " << *cachedResult << "\n";
            }

            else{

                std::cout << "[Worker " << worker_id << "] Cache MISS for Client " << task->client_id << ". Querying DB...\n";

                std::string dbResult = queryDatabase(task->query);
                cache.put(task->query, dbResult);

                std::cout << "[Worker " << worker_id << "] Cache UPDATED -> " << dbResult << "\n";
            }
        }
    }

public:
    CacheEngine(size_t total_cachelines, size_t n_threads) : cache(total_cachelines), n_threads(n_threads) {
        for(size_t i=0; i < n_threads; ++i){
            workers.emplace_back(&CacheEngine::workerLoop, this, i+1);
        }
    }

    void submitRequest(int client_id, const std::string& query){
        taskQueue.push({client_id, query});
    }
    ~CacheEngine() {
        taskQueue.stop();
        for (auto& worker : workers) {
            if (worker.joinable()) worker.join();
        }
    }
};