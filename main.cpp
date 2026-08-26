#include "CacheEngine.hpp"
#include <vector>

int main() {
    // Cache capacity = 3, Worker threads = 4
    CacheEngine server(3, 4);

    // Simulate incoming client requests with repeated queries
    std::vector<std::string> incoming_queries = {
        "SELECT * FROM users WHERE id = 1",
        "SELECT * FROM users WHERE id = 2",
        "SELECT * FROM users WHERE id = 1", // Should hit cache
        "SELECT * FROM users WHERE id = 3",
        "SELECT * FROM users WHERE id = 4", // Triggers eviction of id = 2
        "SELECT * FROM users WHERE id = 1", // Should hit cache
        "SELECT * FROM users WHERE id = 2"  // Miss (was evicted)
    };

    std::cout << "Starting request simulation...\n\n";

    for (int i = 0; i < incoming_queries.size(); ++i) {
        server.submitRequest(i + 1, incoming_queries[i]);
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    // Give workers time to finish before main exits (destructor handles the rest)
    std::this_thread::sleep_for(std::chrono::seconds(2));

    std::cout << "\nShutting down engine...\n";
    return 0;
}