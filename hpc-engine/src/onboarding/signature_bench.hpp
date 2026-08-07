#pragma once
#include <vector>
#include "device_generator.hpp"

struct BenchResult {
    size_t batch_size;
    int num_threads;
    double time_seconds;
    double throughput; // signatures per second
};

class SignatureBench {
public:
    // Sequential signature verification baseline
    static BenchResult run_sequential(const std::vector<Device>& devices);
    
    // OpenMP version will be added here
};
