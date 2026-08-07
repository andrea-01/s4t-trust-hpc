#include "signature_bench.hpp"
#include <chrono>
#include <iostream>
#include <omp.h>

BenchResult SignatureBench::run_sequential(const std::vector<Device>& devices) {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    size_t valid_count = 0;
    
    for (const auto& dev : devices) {
        EVP_MD_CTX_ptr mdctx(EVP_MD_CTX_new());
        if (!mdctx) {
            continue;
        }

        if (EVP_DigestVerifyInit(mdctx.get(), nullptr, EVP_sha256(), nullptr, dev.keypair.get()) <= 0) {
            continue;
        }

        if (EVP_DigestVerify(mdctx.get(), dev.signature.data(), dev.signature.size(), dev.message.data(), dev.message.size()) == 1) {
            valid_count++;
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> diff = end_time - start_time;
    
    BenchResult res;
    res.batch_size = devices.size();
    res.num_threads = 1;
    res.time_seconds = diff.count();
    res.throughput = (res.time_seconds > 0) ? (devices.size() / res.time_seconds) : 0.0;
    
    if (valid_count != devices.size()) {
        std::cerr << "Warning: not all signatures were valid in sequential run (" 
                  << valid_count << "/" << devices.size() << ")\n";
    }
    
    return res;
}

BenchResult SignatureBench::run_parallel(const std::vector<Device>& devices, int num_threads) {
    omp_set_num_threads(num_threads);
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    size_t valid_count = 0;
    
    #pragma omp parallel for reduction(+:valid_count)
    for (size_t i = 0; i < devices.size(); ++i) {
        const auto& dev = devices[i];
        
        EVP_MD_CTX_ptr mdctx(EVP_MD_CTX_new());
        if (!mdctx) {
            continue;
        }

        if (EVP_DigestVerifyInit(mdctx.get(), nullptr, EVP_sha256(), nullptr, dev.keypair.get()) <= 0) {
            continue;
        }

        if (EVP_DigestVerify(mdctx.get(), dev.signature.data(), dev.signature.size(), dev.message.data(), dev.message.size()) == 1) {
            valid_count++;
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> diff = end_time - start_time;
    
    BenchResult res;
    res.batch_size = devices.size();
    res.num_threads = num_threads;
    res.time_seconds = diff.count();
    res.throughput = (res.time_seconds > 0) ? (devices.size() / res.time_seconds) : 0.0;
    
    if (valid_count != devices.size()) {
        std::cerr << "Warning: not all signatures were valid in parallel run (" 
                  << valid_count << "/" << devices.size() << ")\n";
    }
    
    return res;
}
