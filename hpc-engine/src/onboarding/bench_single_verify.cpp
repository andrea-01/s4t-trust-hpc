#include <iostream>
#include <vector>
#include <chrono>
#include <algorithm>
#include <numeric>
#include <cmath>
#include <fstream>
#include <iomanip>
#include "device_generator.hpp"

int main(int argc, char* argv[]) {
    size_t batch_size = 20000;
    std::string out_csv = "results/m13/per_verify_cost.csv";
    std::string out_summary = "results/m13/per_verify_summary.csv";

    if (argc > 1) {
        batch_size = std::stoul(argv[1]);
    }
    if (argc > 2) {
        out_csv = argv[2];
    }
    if (argc > 3) {
        out_summary = argv[3];
    }

    std::cout << "[*] bench_single_verify: N=" << batch_size << std::endl;
    std::cout << "[*] Generating " << batch_size << " synthetic devices..." << std::endl;
    auto devices = DeviceGenerator::generate_devices(batch_size, 42);
    if (devices.size() != batch_size) {
        std::cerr << "[-] Error: Failed to generate devices!" << std::endl;
        return 1;
    }

    // 1. Measure timer overhead
    constexpr int TIMER_ITERS = 1000000;
    auto t_timer_start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < TIMER_ITERS; ++i) {
        auto t = std::chrono::high_resolution_clock::now();
        (void)t;
    }
    auto t_timer_end = std::chrono::high_resolution_clock::now();
    double timer_overhead_ns = std::chrono::duration<double, std::nano>(t_timer_end - t_timer_start).count() / TIMER_ITERS;

    // 2. Warmup
    constexpr size_t WARMUP_COUNT = 500;
    for (size_t i = 0; i < std::min(WARMUP_COUNT, batch_size); ++i) {
        const auto& dev = devices[i];
        EVP_MD_CTX_ptr mdctx(EVP_MD_CTX_new());
        EVP_DigestVerifyInit(mdctx.get(), nullptr, EVP_sha256(), nullptr, dev.keypair.get());
        EVP_DigestVerify(mdctx.get(), dev.signature.data(), dev.signature.size(), dev.message.data(), dev.message.size());
    }

    // 3. Timed single-verification loop
    std::vector<double> latencies_ns(batch_size);
    size_t valid_count = 0;

    for (size_t i = 0; i < batch_size; ++i) {
        const auto& dev = devices[i];
        auto t_start = std::chrono::high_resolution_clock::now();

        EVP_MD_CTX_ptr mdctx(EVP_MD_CTX_new());
        EVP_DigestVerifyInit(mdctx.get(), nullptr, EVP_sha256(), nullptr, dev.keypair.get());
        int ret = EVP_DigestVerify(mdctx.get(), dev.signature.data(), dev.signature.size(), dev.message.data(), dev.message.size());

        auto t_end = std::chrono::high_resolution_clock::now();
        double lat_ns = std::chrono::duration<double, std::nano>(t_end - t_start).count();
        latencies_ns[i] = lat_ns;
        if (ret == 1) {
            valid_count++;
        }
    }

    if (valid_count != batch_size) {
        std::cerr << "[-] Error: signature validation mismatch (" << valid_count << "/" << batch_size << " valid)" << std::endl;
        return 2;
    }

    // 4. Compute statistics
    std::vector<double> sorted = latencies_ns;
    std::sort(sorted.begin(), sorted.end());

    double sum_ns = std::accumulate(latencies_ns.begin(), latencies_ns.end(), 0.0);
    double mean_ns = sum_ns / batch_size;

    double sq_diff_sum = 0.0;
    for (double val : latencies_ns) {
        sq_diff_sum += (val - mean_ns) * (val - mean_ns);
    }
    double stddev_ns = std::sqrt(sq_diff_sum / (batch_size - 1));
    double cv = stddev_ns / mean_ns;

    double min_ns = sorted.front();
    double max_ns = sorted.back();
    double p50_ns = sorted[static_cast<size_t>(batch_size * 0.50)];
    double p90_ns = sorted[static_cast<size_t>(batch_size * 0.90)];
    double p99_ns = sorted[static_cast<size_t>(batch_size * 0.99)];

    // Convert to microseconds
    double mean_us = mean_ns / 1000.0;
    double stddev_us = stddev_ns / 1000.0;
    double min_us = min_ns / 1000.0;
    double p50_us = p50_ns / 1000.0;
    double p90_us = p90_ns / 1000.0;
    double p99_us = p99_ns / 1000.0;
    double max_us = max_ns / 1000.0;

    std::cout << "\n================ Single ECDSA Verify Benchmark ================\n";
    std::cout << " Samples:         " << batch_size << "\n";
    std::cout << " Timer overhead:  " << std::fixed << std::setprecision(2) << timer_overhead_ns << " ns\n";
    std::cout << " Mean:            " << mean_us << " us (" << mean_ns << " ns)\n";
    std::cout << " StdDev:          " << stddev_us << " us (" << stddev_ns << " ns)\n";
    std::cout << " CV:              " << std::setprecision(4) << cv << " (" << cv * 100.0 << "%)\n";
    std::cout << " Min:             " << std::setprecision(2) << min_us << " us\n";
    std::cout << " p50 (Median):    " << p50_us << " us\n";
    std::cout << " p90:             " << p90_us << " us\n";
    std::cout << " p99:             " << p99_us << " us\n";
    std::cout << " Max:             " << max_us << " us\n";
    std::cout << " Throughput eq.:  " << std::setprecision(1) << (1000000.0 / mean_us) << " sig/s\n";
    std::cout << "===============================================================\n\n";

    // 5. Output raw distribution CSV
    std::ofstream csv(out_csv);
    if (!csv.is_open()) {
        std::cerr << "[-] Error: Failed to open " << out_csv << " for writing\n";
        return 3;
    }
    csv << "sample_id,latency_ns,latency_us\n";
    for (size_t i = 0; i < batch_size; ++i) {
        csv << i << "," << std::fixed << std::setprecision(1) << latencies_ns[i]
            << "," << std::setprecision(4) << (latencies_ns[i] / 1000.0) << "\n";
    }
    csv.close();
    std::cout << "[+] Raw latencies written to " << out_csv << std::endl;

    // 6. Output summary CSV
    std::ofstream sum(out_summary);
    if (sum.is_open()) {
        sum << "samples,timer_overhead_ns,mean_us,stddev_us,cv,min_us,p50_us,p90_us,p99_us,max_us\n";
        sum << batch_size << "," << timer_overhead_ns << ","
            << mean_us << "," << stddev_us << "," << cv << ","
            << min_us << "," << p50_us << "," << p90_us << "," << p99_us << "," << max_us << "\n";
        sum.close();
        std::cout << "[+] Summary metrics written to " << out_summary << std::endl;
    }

    return 0;
}
