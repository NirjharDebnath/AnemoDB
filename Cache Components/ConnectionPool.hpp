#pragma once
#include <iostream>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <memory>
#include <string>
#include <chrono>
#include <stdexcept>
#include <pqxx/pqxx>

class ConnectionPool {
private:
    std::mutex pool_mtx;
    std::condition_variable pool_cv;
    std::queue<std::unique_ptr<pqxx::connection>> connections;
    size_t pool_size;              // Declared first
    std::string connection_string; // Declared second (matches init order)

public:
    ConnectionPool(size_t size, const std::string& conn_str) 
        : pool_size(size), connection_string(conn_str) {
        
        size_t successful_connections = 0;

        for (size_t i = 0; i < pool_size; ++i) {
            try {
                auto conn = std::make_unique<pqxx::connection>(connection_string);
                if (conn->is_open()) {
                    connections.push(std::move(conn));
                    successful_connections++;
                }
            } catch (const std::exception& e) {
                std::cerr << "[ConnectionPool] Connection " << (i + 1) 
                          << " failed: " << e.what() << "\n";
            }
        }

        // Fail-Fast: If not a single connection could be made, fail server startup
        if (successful_connections == 0) {
            throw std::runtime_error("Failed to connect to PostgreSQL database. Check credentials and service status.");
        }

        std::cout << "[ConnectionPool] Initialized " << successful_connections 
                  << "/" << pool_size << " database connections.\n";
    }

    // Acquires a connection from the pool with timeout and health check
    std::unique_ptr<pqxx::connection> acquire() {
        std::unique_lock<std::mutex> lock(pool_mtx);

        // Wait up to 5 seconds for an available connection
        bool acquired = pool_cv.wait_for(lock, std::chrono::seconds(5), [this]() {
            return !connections.empty();
        });

        if (!acquired) {
            throw std::runtime_error("Database connection pool timeout (all connections busy)");
        }

        auto conn = std::move(connections.front());
        connections.pop();

        // Health Check & Auto-Reconnect:
        // If connection dropped while idle, re-establish it
        if (!conn || !conn->is_open()) {
            try {
                conn = std::make_unique<pqxx::connection>(connection_string);
            } catch (const std::exception& e) {
                // Return a slot back to the pool so capacity doesn't permanently shrink
                connections.push(nullptr);
                pool_cv.notify_one();
                throw std::runtime_error(std::string("Database reconnection failed: ") + e.what());
            }
        }

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