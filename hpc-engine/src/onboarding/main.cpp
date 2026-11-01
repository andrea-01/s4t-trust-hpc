#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include "device_generator.hpp"
#include "signature_bench.hpp"
#include "csv_writer.hpp"

std::vector<int> parse_comma_separated(const std::string& str) {
    std::vector<int> result;
    std::stringstream ss(str);
    std::string item;
    while (std::getline(ss, item, ',')) {
        if (!item.empty()) {
            result.push_back(std::stoi(item));
        }
    }
    return result;
}

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "Usage: " << argv[0] << " <dataset_size> <batch_sizes_csv> <thread_counts_csv> [output_csv] [mode: for|taskloop] [grainsize]\n";
        std::cerr << "Example: " << argv[0] << " 500 100,250,500 1,2,4 results.csv taskloop 25\n";
        return 1;
    }

    size_t dataset_size = std::stoull(argv[1]);
    std::vector<int> batch_sizes = parse_comma_separated(argv[2]);
    std::vector<int> thread_counts = parse_comma_separated(argv[3]);
    std::string output_csv = (argc > 4) ? argv[4] : "results.csv";
    std::string mode = (argc > 5) ? argv[5] : "for";
    size_t grainsize = 0;
    if (argc > 6) {
        try {
            grainsize = std::stoull(argv[6]);
        } catch (...) {
            grainsize = 0;
        }
    }

    std::cout << "Generating " << dataset_size << " devices (this may take a while)...\n";
    auto devices = DeviceGenerator::generate_devices(dataset_size, 42); // deterministic seed

    std::vector<BenchResult> all_results;

    for (int batch_size : batch_sizes) {
        if (batch_size <= 0 || static_cast<size_t>(batch_size) > dataset_size) {
            std::cerr << "Skipping invalid batch_size " << batch_size << "\n";
            continue;
        }

        bool skip_seq = (mode == "taskloop" || mode == "for" || std::getenv("SKIP_SEQUENTIAL") != nullptr);
        if (mode == "seq") {
            skip_seq = false;
        }

        if (!skip_seq) {
            std::cout << "Running sequential (batch: " << batch_size << ")...\n";
            all_results.push_back(SignatureBench::run_sequential(devices, static_cast<size_t>(batch_size)));
        }

        if (mode != "seq") {
            // Parallel runs
            for (int threads : thread_counts) {
                if (threads <= 0) continue;
                std::cout << "Running parallel [" << mode << "] (batch: " << batch_size << ", threads: " << threads << ")...\n";
                if (mode == "taskloop") {
                    all_results.push_back(SignatureBench::run_parallel_taskloop(devices, threads, static_cast<size_t>(batch_size), grainsize));
                } else {
                    all_results.push_back(SignatureBench::run_parallel(devices, threads, static_cast<size_t>(batch_size)));
                }
            }
        }
    }

    CSVWriter::write_results(output_csv, all_results);
    std::cout << "Results written to " << output_csv << "\n";

    return 0;
}
