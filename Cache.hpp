#pragma once
#include <iostream>
#include <string>
#include <optional>
#include <list>
#include <unordered_map>
#include <mutex>

// using namespace std;

class Cache {
private:
    struct CacheNode{
        std::string key; //query
        std::string value; //result of query
    };

    mutable std::mutex cache_mutex;

    size_t total_cachelines;

    std::list<CacheNode> cacheLines; // LRU cache list

    std::unordered_map<std::string, std::list<CacheNode>::iterator> cacheDirectory; // actual cache hash map

    void moveToFront(std::list<CacheNode>::iterator p){
        cacheLines.splice(cacheLines.begin(), cacheLines, p);
    }
public:
    explicit Cache(size_t total_cachelines) : total_cachelines(total_cachelines == 0 ? 1 : total_cachelines){}

    std::optional<std::string> get(std::string& key){
        std::lock_guard<std::mutex> lock(cache_mutex);
        auto mapIt = cacheDirectory.find(key); //O(1)
        if (mapIt == cacheDirectory.end()) return std::nullopt; // cache miss

        moveToFront(mapIt->second); // LRU update cachelines list after hit
        return mapIt->second->value; // always dereference to print
    }

    void put(const std::string& key, const std::string& value){
        std::lock_guard<std::mutex> lock(cache_mutex);
        auto mapIt = cacheDirectory.find(key); //O(1)

        // if key(query) exists in cacheDirectory then update its value and update its position in LRU cacheLines
        if (mapIt != cacheDirectory.end()){
            mapIt->second->value = value;
            moveToFront(mapIt->second);
            return;
        }

        // cache is full then evict
        if (cacheLines.size() >= total_cachelines){
            std::string lastkey = cacheLines.back().key;
            cacheDirectory.erase(lastkey);
            cacheLines.pop_back();
        }

        // insert into the cacheLines list and the cacheDirectory
        cacheLines.push_front({key, value});
        cacheDirectory[key] = cacheLines.begin();   
    }

    // debug print cacheLines
    void debugPrint() const {
        std::lock_guard<std::mutex> lock(cache_mutex);
        std::cout << "Cache (MRU -> LRU): ";
        for (const auto& node : cacheLines) {
            std::cout << "[" << node.key << ": " << node.value << "] ";
        }
        std::cout << "\n";
    }
    
    
};

// int main(){
//     Cache cache(3);
//     cache.put("user_1", "Alice");
//     cache.put("user_2", "Bob");
//     cache.put("user_3", "Charlie");
//     cache.debugPrint();

//     auto res1 = cache.get("user_1");
//     std::cout << "Get user_1: " << (res1 ? *res1 : "NOT FOUND") << "\n";
//     cache.debugPrint();

//     cache.put("user_4", "David");
//     cache.debugPrint();

//     auto res2 = cache.get("user_2");
//     std::cout << "Get user_2: " << (res2 ? *res2 : "NOT FOUND") << "\n";

//     return 0;
// }
