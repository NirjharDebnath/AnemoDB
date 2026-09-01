#include "CacheEngine.hpp"
#include <iostream>
#include <string>
#include <chrono>
#include <thread>


int main() {

    const std::string DARK_BLUE = "\033[0;34m";
    const std::string BRIGHT_BLUE = "\033[1;34m";
    const std::string RESET = "\033[0m";


    std::cout << DARK_BLUE << "admin@cache_server> " << RESET;



    std::string conn_str = "dbname=college_db user=postgres password=postgres host=127.0.0.1 port=5432";
    
    CacheEngine server(50, 60, 8080, conn_str); // Increased capacity to 50 and threads to 8

    std::cout << "\nServer initialized. Interactive terminal ready.\n"; 
    std::cout << "Available commands: 'showstats', 'stop', 'help'\n\n";

    std::string command;

    std::this_thread::sleep_for(std::chrono::milliseconds(400));

    while (true) {
        std::cout << DARK_BLUE << "admin@cache_server> " << RESET;
        
        // std::cout << BRIGHT_BLUE << "admin@cache_server> " << RESET;

        std::getline(std::cin, command);

        if (command == "stop" || command == "exit") {
            break;
        } 
        else if (command == "showstats") {
            std::cout << server.generateStatsReport() << "\n";
        } 
        else if (command == "clear" ) {
            std::system("clear");
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