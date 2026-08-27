#include "CacheEngine.hpp"

int main()
{
    // Capacity = 10, Workers = 4, Port = 8080
    CacheEngine server(10, 4, 8080);

    std::cout << "Server is running. Press Enter to terminate...\n";
    std::cin.get();

    return 0;
}