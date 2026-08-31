#pragma once
#include <iostream>
#include <string>
#include <optional>
#include <list>
#include <unordered_map>
#include <mutex>

// using namespace std;

enum class NodeState { IN_PROGRESS, READY, FAILED };

struct CacheNode{
    std::string key; //query
    std::string value; //result of query
    NodeState state = NodeState::IN_PROGRESS; // to prevent eviction in progressing conditions

    // per node synchronization
    std::mutex node_mtx;
    std::condition_variable node_cv;
    
    CacheNode(const std::string& k) : key(k) {}
};

class Cache {
private:
    
    mutable std::mutex cache_mutex;

    size_t total_cachelines;

    std::atomic<size_t> payload_bytes{0}; // Tracks dynamic string memory

    std::list<std::shared_ptr<CacheNode>> cacheLines; // LRU cache list

    std::unordered_map<std::string, std::list<std::shared_ptr<CacheNode>>::iterator> cacheDirectory; // actual cache hash map

    void moveToFront(std::list<std::shared_ptr<CacheNode>>::iterator p){
        cacheLines.splice(cacheLines.begin(), cacheLines, p);
    }

    // function to evict only READY nodes if present in cacheLines from the tail
    bool evictReadyNode() {
        if (cacheLines.size() <total_cachelines) return true;

        for (auto it = cacheLines.rbegin(); it != cacheLines.rend(); ++it) {
            if ((*it)->state == NodeState::READY) {
                // Deduct the memory of the evicted node's strings
                payload_bytes -= ((*it)->key.size() + (*it)->value.size());
                
                cacheDirectory.erase((*it)->key);
                cacheLines.erase(std::next(it).base());
                return true;
            }
        }
        return false; // entire cache is in progress
    }
public:
    explicit Cache(size_t total_cachelines) : total_cachelines(total_cachelines == 0 ? 1 : total_cachelines){}

    struct CacheMetrics {
        size_t current_lines;
        size_t max_capacity;
        size_t directory_size;
        size_t total_payload_bytes;
    };

    CacheMetrics getMetrics() {
        std::lock_guard<std::mutex> lock(cache_mutex);
        return { cacheLines.size(), total_cachelines, cacheDirectory.size(), payload_bytes.load() };
    }

    // {Node Pointer, is_leader boolean}, thread comes and tries to find it requested data. If fails then it reserves a slot in cacheDirectory and cacheLines both and then releases the global cache_mtx
    std::pair<std::shared_ptr<CacheNode>, bool> lookupOrReserve(const std::string& key) {
        std::lock_guard<std::mutex> lock(cache_mutex);

        auto mapIt = cacheDirectory.find(key); //O(1)
        if (mapIt != cacheDirectory.end()) {
            moveToFront(mapIt->second); // LRU update cachelines list after hit
            return { *(mapIt->second), false }; // cache hit, not the leader thread
        } 

        evictReadyNode();

        auto newcacheline = std::make_shared<CacheNode>(key);
        cacheLines.push_front(newcacheline); // take care of the LRU update
        cacheDirectory[key] = cacheLines.begin();

        return { newcacheline, true }; // make this thread a reservation for the upcoming db query result and also the leader of the threads who requested the same cache data. Solves Thundering Heard Problem.
    }

    // Called by the leader thread after DB fetch is successful
    void completeReservation(std::shared_ptr<CacheNode> node, const std::string& value) {
        {
            std::lock_guard<std::mutex> node_lock(node->node_mtx); // lock only the node_mtx and not the cache_mtx cause only the reserved cacheLine is modified and following threads are the only ones to be blocked
            node->value = value; // write the value from the db to the reserved cacheline;
            node->state = NodeState::READY;
        }

        node->node_cv.notify_all(); // wake up all the following threads of the leader thread
    }

    // Called by the leader if the DB query fails
    void cancelReservation(std::shared_ptr<CacheNode> node) {
        {
            std::lock_guard<std::mutex> lock(cache_mutex);
            auto it = cacheDirectory.find(node->key);
            if (it != cacheDirectory.end() && it->second->get() == node.get()) {
                cacheLines.erase(it->second);
                cacheDirectory.erase(it);
            }
        }
        {
            std::lock_guard<std::mutex> node_lock(node->node_mtx);
            node->state = NodeState::FAILED;
        }

        node->node_cv.notify_all();
    }
    
};
