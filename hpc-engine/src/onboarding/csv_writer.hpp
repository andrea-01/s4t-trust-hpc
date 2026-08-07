#pragma once
#include <vector>
#include <string>
#include "signature_bench.hpp"

class CSVWriter {
public:
    static void write_results(const std::string& filename, const std::vector<BenchResult>& results);
};
