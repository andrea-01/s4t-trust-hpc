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
    std::string out_csv = "results/m13/v1_device_gen_cost.csv";
    if (argc > 1) {
        out_csv = argv[1];
    }

    std::vector<size_t> batch_sizes = {1000, 5000, 20000};
    constexpr int REPEATS = 10;

    std::ofstream csv(out_csv);
    if (!csv.is_open()) {
        std::cerr << "[-] Error opening " << out_csv << "\n";
        return 1;
    }
    csv << "batch,rep,time_seconds,us_per_device\n";

    std::cout << "==========================================================\n";
    std::cout << " V1.2: Isolated Device Generation Benchmark\n";
    std::cout << " Function: DeviceGenerator::generate_devices(N, seed)\n";
    std::cout << " Output:   " << out_csv << "\n";
    std::cout << "==========================================================\n\n";

    for (size_t N : batch_sizes) {
        std::cout << "[*] Benchmarking N = " << N << " (1 warmup + " << REPEATS << " repeats)...\n";
        // Warmup
        {
            auto w = DeviceGenerator::generate_devices(std::min(N, (size_t)1000), 1234);
            (void)w;
        }

        std::vector<double> times_s(REPEATS);
        std::vector<double> us_per_dev(REPEATS);

        for (int rep = 0; rep < REPEATS; ++rep) {
            auto t0 = std::chrono::high_resolution_clock::now();
            auto devs = DeviceGenerator::generate_devices(N, 42 + rep * 100);
            auto t1 = std::chrono::high_resolution_clock::now();

            double sec = std::chrono::duration<double>(t1 - t0).count();
            double us_dev = (sec * 1e6) / static_cast<double>(N);

            times_s[rep] = sec;
            us_per_dev[rep] = us_dev;

            csv << N << "," << rep << "," << std::fixed << std::setprecision(6) << sec
                << "," << std::setprecision(2) << us_dev << "\n";
            csv.flush();
        }

        // Compute median & IQR
        std::vector<double> sorted_s = times_s;
        std::sort(sorted_s.begin(), sorted_s.end());
        double med_s = (sorted_s[4] + sorted_s[5]) / 2.0;
        double p25_s = sorted_s[2];
        double p75_s = sorted_s[7];
        double iqr_s = p75_s - p25_s;

        std::vector<double> sorted_us = us_per_dev;
        std::sort(sorted_us.begin(), sorted_us.end());
        double med_us = (sorted_us[4] + sorted_us[5]) / 2.0;
        double p25_us = sorted_us[2];
        double p75_us = sorted_us[7];
        double iqr_us = p75_us - p25_us;

        std::cout << "  N = " << std::setw(5) << N << " | Time: median=" << std::setprecision(4) << med_s
                  << "s (IQR=" << iqr_s << "s) | Cost: median=" << std::setprecision(2) << med_us
                  << " us/device (IQR=" << iqr_us << " us)\n";
    }

    csv.close();
    std::cout << "\n[+] Results successfully written to " << out_csv << "\n";
    return 0;
}
