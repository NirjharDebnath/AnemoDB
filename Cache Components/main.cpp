#include "CacheEngine.hpp"
#include <iostream>
#include <string>

int main() {
    std::string conn_str = "dbname=college_db user=postgres password=postgres host=127.0.0.1 port=5432";
    
    CacheEngine server(50, 8, 8080, conn_str); // Increased capacity to 50 and threads to 8

    std::cout << "\nServer initialized. Interactive terminal ready.\n"; 
    std::cout << "Available commands: 'showstats', 'stop', 'help'\n\n";

    std::string command;
    while (true) {
        std::cout << "admin@cache_server> ";
        std::getline(std::cin, command);

        if (command == "stop" || command == "exit") {
            break;
        } 
        else if (command == "showstats") {
            std::cout << server.generateStatsReport() << "\n";
        } 
        else if (command == "help") {
            std::cout << "  showstats  - View live cache telemetry and memory usage\n";
            std::cout << "  stop       - Safely shutdown the server\n";
        } 
        else if (!command.empty()) {
            std::cout << "Unknown command: " << command << "\n";
        }
    }

    return 0;
}