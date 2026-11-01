#include "signature_bench.hpp"
#include <chrono>
#include <iostream>
#include <cstdlib>
#include <omp.h>

BenchResult SignatureBench::run_sequential(const std::vector<Device>& devices, size_t limit) {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    size_t valid_count = 0;
    size_t actual_limit = (limit == 0 || limit > devices.size()) ? devices.size() : limit;
    
    for (size_t i = 0; i < actual_limit; ++i) {
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
    res.batch_size = actual_limit;
    res.num_threads = 1;
    res.time_seconds = diff.count();
    res.throughput = (res.time_seconds > 0) ? (actual_limit / res.time_seconds) : 0.0;
    res.valid_count = valid_count;
    
    if (valid_count != actual_limit) {
        std::cerr << "Warning: not all signatures were valid in sequential run (" 
                  << valid_count << "/" << actual_limit << ")\n";
    }
    
    return res;
}

BenchResult SignatureBench::run_parallel(const std::vector<Device>& devices, int num_threads, size_t limit) {
    omp_set_num_threads(num_threads);

    // If OMP_SCHEDULE is not explicitly set in the environment, default to static schedule (chunk=0)
    // to preserve backward compatibility with the previous static schedule behavior.
    if (std::getenv("OMP_SCHEDULE") == nullptr) {
        omp_set_schedule(omp_sched_static, 0);
    }
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    size_t valid_count = 0;
    size_t actual_limit = (limit == 0 || limit > devices.size()) ? devices.size() : limit;
    
    #pragma omp parallel for schedule(runtime) reduction(+:valid_count)
    for (size_t i = 0; i < actual_limit; ++i) {
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
    res.batch_size = actual_limit;
    res.num_threads = num_threads;
    res.time_seconds = diff.count();
    res.throughput = (res.time_seconds > 0) ? (actual_limit / res.time_seconds) : 0.0;
    res.valid_count = valid_count;
    
    if (valid_count != actual_limit) {
        std::cerr << "Warning: not all signatures were valid in parallel run (" 
                  << valid_count << "/" << actual_limit << ")\n";
    }
    
    return res;
}

BenchResult SignatureBench::run_parallel_taskloop(const std::vector<Device>& devices, int num_threads, size_t limit, size_t grainsize) {
    omp_set_num_threads(num_threads);
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    size_t valid_count = 0;
    size_t actual_limit = (limit == 0 || limit > devices.size()) ? devices.size() : limit;
    
    #pragma omp parallel
    {
        #pragma omp single
        {
            if (grainsize > 0) {
                #pragma omp taskloop grainsize(grainsize) reduction(+:valid_count)
                for (size_t i = 0; i < actual_limit; ++i) {
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
            } else {
                #pragma omp taskloop reduction(+:valid_count)
                for (size_t i = 0; i < actual_limit; ++i) {
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
            }
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> diff = end_time - start_time;
    
    BenchResult res;
    res.batch_size = actual_limit;
    res.num_threads = num_threads;
    res.time_seconds = diff.count();
    res.throughput = (res.time_seconds > 0) ? (actual_limit / res.time_seconds) : 0.0;
    res.valid_count = valid_count;
    
    if (valid_count != actual_limit) {
        std::cerr << "Warning: not all signatures were valid in taskloop parallel run (" 
                  << valid_count << "/" << actual_limit << ")\n";
    }
    
    return res;
}

