#include "CacheEngine.hpp"

#include <iostream>
#include <string>
#include <limits>
#include <chrono>
#include <thread>

void clearScreen() {
    std::system("clear");
}

int main() {

    // ─────────────────────────────────────────────
    // Terminal colors
    // ─────────────────────────────────────────────

    const std::string DARK_BLUE   = "\033[0;34m";
    const std::string BRIGHT_BLUE = "\033[1;34m";
    const std::string GREEN       = "\033[0;32m";
    const std::string RED         = "\033[0;31m";
    const std::string YELLOW      = "\033[0;33m";
    const std::string RESET       = "\033[0m";


    // ─────────────────────────────────────────────
    // Startup banner
    // ─────────────────────────────────────────────

    clearScreen();

    std::cout << BRIGHT_BLUE;
    std::cout << "============================================\n";
    std::cout << "          ANEMO SERVER ADMIN CONSOLE        \n";
    std::cout << "============================================\n";
    std::cout << RESET;


    // ─────────────────────────────────────────────
    // Database configuration
    // ─────────────────────────────────────────────

    std::cout << "\n" << YELLOW;
    std::cout << "[ Database Configuration ]\n";
    std::cout << RESET;

    std::string dbName;
    std::string dbUser;
    std::string dbPassword;
    std::string dbHost;
    int dbPort;

    std::cout << "Database name : ";
    std::getline(std::cin, dbName);

    std::cout << "Database user : ";
    std::getline(std::cin, dbUser);

    std::cout << "Database password : ";
    std::getline(std::cin, dbPassword);

    std::cout << "Database host [127.0.0.1] : ";
    std::getline(std::cin, dbHost);

    if (dbHost.empty()) {
        dbHost = "127.0.0.1";
    }

    std::cout << "Database port [5432] : ";

    std::string dbPortInput;
    std::getline(std::cin, dbPortInput);

    if (dbPortInput.empty()) {
        dbPort = 5432;
    } else {
        try {
            dbPort = std::stoi(dbPortInput);
        } catch (...) {
            std::cout << RED << "Invalid database port.\n" << RESET;
            return 1;
        }
    }


    // ─────────────────────────────────────────────
    // Server configuration
    // ─────────────────────────────────────────────

    std::cout << "\n" << YELLOW;
    std::cout << "[ Cache Server Configuration ]\n";
    std::cout << RESET;

    int cacheCapacity;
    int workerThreads;
    int serverPort;

    std::string input;

    std::cout << "Cache capacity [50] : ";
    std::getline(std::cin, input);

    if (input.empty()) {
        cacheCapacity = 50;
    } else {
        try {
            cacheCapacity = std::stoi(input);
        } catch (...) {
            std::cout << RED << "Invalid cache capacity.\n" << RESET;
            return 1;
        }
    }


    std::cout << "Worker threads [8] : ";
    std::getline(std::cin, input);

    if (input.empty()) {
        workerThreads = 8;
    } else {
        try {
            workerThreads = std::stoi(input);
        } catch (...) {
            std::cout << RED << "Invalid thread count.\n" << RESET;
            return 1;
        }
    }


    std::cout << "Server port [8080] : ";
    std::getline(std::cin, input);

    if (input.empty()) {
        serverPort = 8080;
    } else {
        try {
            serverPort = std::stoi(input);
        } catch (...) {
            std::cout << RED << "Invalid server port.\n" << RESET;
            return 1;
        }
    }

    int ttlSeconds;
    std::cout << "Cache TTL (seconds) [60] : ";
    std::getline(std::cin, input);

    if (input.empty()) {
        ttlSeconds = 60;
    } else {
        try {
            ttlSeconds = std::stoi(input);
        } catch (...) {
            std::cout << RED << "Invalid TTL.\n" << RESET;
            return 1;
        }
    }


    // ─────────────────────────────────────────────
    // Build PostgreSQL connection string
    // ─────────────────────────────────────────────

    std::string conn_str =
        "dbname=" + dbName +
        " user=" + dbUser +
        " password=" + dbPassword +
        " host=" + dbHost +
        " port=" + std::to_string(dbPort);


    // ─────────────────────────────────────────────
    // Display configuration
    // ─────────────────────────────────────────────

    std::cout << "\n" << BRIGHT_BLUE;
    std::cout << "--------------------------------------------\n";
    std::cout << "Starting Cache Server...\n";
    std::cout << "--------------------------------------------\n";
    std::cout << RESET;

    std::cout << "Database : " << dbName << "\n";
    std::cout << "Host     : " << dbHost << "\n";
    std::cout << "DB Port  : " << dbPort << "\n";
    std::cout << "Cache    : " << cacheCapacity << " entries\n";
    std::cout << "Threads  : " << workerThreads << "\n";
    std::cout << "Server   : " << serverPort << "\n";
    std::cout << "TTL      : " << ttlSeconds << " seconds\n";

    std::cout << "\n";


    // ─────────────────────────────────────────────
    // Start server
    // ─────────────────────────────────────────────

    try {

        CacheEngine server(
            cacheCapacity,
            workerThreads,
            serverPort,
            conn_str,
            ttlSeconds // NEW
        );

        std::this_thread::sleep_for(
            std::chrono::milliseconds(400)
        );

        std::cout << GREEN;
        std::cout << "\nServer initialized successfully.\n";
        std::cout << RESET;

        std::cout << "\nAvailable commands:\n";
        std::cout << "  showstats  - View cache statistics\n";
        std::cout << "  clear      - Clear terminal\n";
        std::cout << "  help       - Show available commands\n";
        std::cout << "  stop       - Shutdown server\n";


        // ─────────────────────────────────────────
        // Interactive terminal
        // ─────────────────────────────────────────

        std::string command;

        while (true) {

            std::cout << "\n";
            std::cout << DARK_BLUE
                      << "admin@cache_server> "
                      << RESET;

            if (!std::getline(std::cin, command)) {
                break;
            }


            // Remove accidental leading/trailing spaces
            if (!command.empty()) {

                const auto first = command.find_first_not_of(" \t");
                const auto last  = command.find_last_not_of(" \t");

                if (first != std::string::npos) {
                    command = command.substr(
                        first,
                        last - first + 1
                    );
                }
            }


            // ─────────────────────────────────────
            // Commands
            // ─────────────────────────────────────

            if (command == "stop" || command == "exit" ||
                command == "quit") {

                std::cout << YELLOW
                          << "Shutting down server...\n"
                          << RESET;

                break;
            }

            else if (command == "showstats") {

                std::cout << "\n";
                std::cout << server.generateStatsReport();
                std::cout << "\n";
            }

            else if (command == "clear") {

                clearScreen();
            }

            else if (command == "help") {

                std::cout << "\n";
                std::cout << "Available commands:\n";
                std::cout << "  showstats  - View cache statistics\n";
                std::cout << "  clear      - Clear terminal\n";
                std::cout << "  help       - Show this help message\n";
                std::cout << "  stop       - Shutdown server\n";
            }

            else if (!command.empty()) {

                std::cout << RED
                          << "Unknown command: "
                          << command
                          << "\n"
                          << RESET;
            }
        }

    }
    catch (const std::exception& e) {

        std::cout << RED
                  << "\nServer failed to start:\n"
                  << e.what()
                  << "\n"
                  << RESET;

        return 1;
    }


    // ─────────────────────────────────────────────
    // Shutdown
    // ─────────────────────────────────────────────

    std::cout << "\n"
              << GREEN
              << "Cache server stopped.\n"
              << RESET;

    return 0;
}