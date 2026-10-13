cmake_minimum_required(VERSION 3.12)
project(AnemoDB VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Optimization and warning flags
if(MSVC)
    add_compile_options(/W4 /O2)
else()
    add_compile_options(-Wall -Wextra -O3)
endif()

# Threading support
find_package(Threads REQUIRED)

# Include directory
include_directories("${CMAKE_CURRENT_SOURCE_DIR}/Cache Components")

# Executable target
add_executable(anemo_db
    "Cache Components/main.cpp"
    "Cache Components/CacheEngine.hpp"
    "Cache Components/Cache.hpp"
    "Cache Components/ConnectionPool.hpp"
    "Cache Components/ThreadSafeQueue.hpp"
)

# Link required libraries
target_link_libraries(anemo_db PRIVATE
    Threads::Threads
    pqxx
    pq
)

# Install target: installs to bin/ (e.g. /usr/local/bin)
install(TARGETS anemo_db DESTINATION bin)
