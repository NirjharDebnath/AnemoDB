#pragma once
#include <iostream>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <memory>
#include <string>
#include <pqxx/pqxx>

class ConnectionPool {
private:
    std::mutex pool_mtx;
    std::condition_variable pool_cv;
    std::queue<std::unique_ptr<pqxx::connection>> connections;
    std::string connection_string;
    size_t pool_size;

public:
    ConnectionPool(size_t size, const std::string& conn_str) 
        : pool_size(size), connection_string(conn_str) {
        
        for (size_t i = 0; i < pool_size; ++i) {
            try {
                connections.push(std::make_unique<pqxx::connection>(connection_string));
            } catch (const std::exception& e) {
                std::cerr << "Failed to initialize DB connection: " << e.what() << "\n";
            }
        }
    }

    // Blocks until a connection becomes available
    std::unique_ptr<pqxx::connection> acquire() {
        std::unique_lock<std::mutex> lock(pool_mtx);
        pool_cv.wait(lock, [this]() { return !connections.empty(); });

        auto conn = std::move(connections.front());
        connections.pop();
        return conn;
    }

    // Returns the connection to the pool
    void release(std::unique_ptr<pqxx::connection> conn) {
        {
            std::lock_guard<std::mutex> lock(pool_mtx);
            connections.push(std::move(conn));
        }
        pool_cv.notify_one();
    }
};
