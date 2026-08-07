#include "csv_writer.hpp"
#include <fstream>
#include <iostream>

void CSVWriter::write_results(const std::string& filename, const std::vector<BenchResult>& results) {
    std::ofstream out(filename);
    if (!out) {
        std::cerr << "Failed to open " << filename << " for writing\n";
        return;
    }
    
    out << "batch_size,num_threads,time_seconds,throughput\n";
    for (const auto& res : results) {
        out << res.batch_size << ","
            << res.num_threads << ","
            << res.time_seconds << ","
            << res.throughput << "\n";
    }
}
