#pragma once
#include <iostream>
#include <queue>
#include <optional>
#include <mutex>
#include <thread>
#include <condition_variable>

template <typename T>
class ThreadSafeQueue {
private:
    std::queue<T> queue; // shared queue between the threads
    std::mutex mtx; // shared mutex lock
    std::condition_variable cv; // synchronization primitive that allows multiple threads to communicate by letting one or more threads sleep (block) until another thread modifies a shared variable and notifies them to resume
    bool is_stopped = false; // shared state for condition_variable
public:
    // used by the Listener to enqueue tasks
    void push(T task){
        {
            std::lock_guard<std::mutex> lock(mtx); // lock the shared mutex lock, automatic locking (no mtx.lock reqd in modern C++)

            queue.push(task);
        } // lock goes out of scope for the declared scope

        cv.notify_one(); // wake one worker thread to take the task and pop it out of the shared queue
    }
    // used by worker Threads to take one tasks for themselves
    std::optional<T> pop(){
        // acquire the lock
        std::unique_lock<std::mutex> lock(mtx);

        // If the queue is empty, it unlocks the mutex and puts the thread to sleep.
        // When cv.notify_one() is called, it wakes up, re-locks the mutex, and checks the condition again.
        cv.wait(lock, [this]() {
            return !queue.empty() || is_stopped;
        });

        // wake up cause the server is the queue is empty and the server is shutting down 
        if(queue.empty() && is_stopped) return std::nullopt;

        // wake up cause there is a task in the shared queue
        T task = queue.front();
        queue.pop();

        return task;
    }

    // used to cleanly shut down the server
    void stop(){
        {
            std::lock_guard<std::mutex> lock(mtx); // so that current threads in any condition either sleeping or working get locked of from using the shared queue
            is_stopped = true; // and no thread misses the condition and gets deadlocked for ever untill the os finally terminates the calling function waiting for join
        }

        cv.notify_all(); // wake up all the threads so that they can check in pop() about the server shutting down condition in cv.wait() and properly join to the calling thread

    }
};


// optional part
// A simple worker function that runs in a thread
void worker_loop(ThreadSafeQueue<std::string>& ts_queue, int worker_id) {
    while (true) {
        // This will block (sleep) until an item is available or stop() is called
        std::optional<std::string> task = ts_queue.pop();
        
        if (!task) {
            std::cout << "Worker " << worker_id << " shutting down.\n";
            break; // Exit the loop because the queue is stopped and empty
        }

        std::cout << "Worker " << worker_id << " processing: " << *task << "\n";
        
        // Simulate work taking time
        std::this_thread::sleep_for(std::chrono::milliseconds(500)); 
    }
}

// int main() {
//     ThreadSafeQueue<std::string> ts_queue;

//     // Create 2 worker threads
//     std::thread worker1(worker_loop, std::ref(ts_queue), 1);
//     std::thread worker2(worker_loop, std::ref(ts_queue), 2);

//     // Producer (Main Thread) adds tasks slowly
//     for (int i = 1; i <= 5; ++i) {
//         std::cout << "Listener pushing Task " << i << "\n";
//         ts_queue.push("Task_" + std::to_string(i));
//         std::this_thread::sleep_for(std::chrono::milliseconds(200)); 
//     }

//     // Shut down sequence
//     std::cout << "Listener sending stop signal...\n";
//     ts_queue.stop();

//     // Wait for worker threads to finish before exiting main
//     worker1.join();
//     worker2.join();

//     std::cout << "System closed cleanly.\n";
//     return 0;
// }