#include <iostream>
#include "device_generator.hpp"
#include "signature_bench.hpp"

int main() {
    std::cout << "[Test Taskloop] Generating 100 test devices...\n";
    size_t batch_size = 100;
    auto devices = DeviceGenerator::generate_devices(batch_size, 42);
    if (devices.size() != batch_size) {
        std::cerr << "Failed to generate expected device count\n";
        return 1;
    }

    std::cout << "[Test Taskloop] 1. Sequential baseline...\n";
    BenchResult res_seq = SignatureBench::run_sequential(devices, batch_size);
    if (res_seq.valid_count != batch_size) {
        std::cerr << "Sequential valid_count mismatch: " << res_seq.valid_count << " != " << batch_size << "\n";
        return 1;
    }

    std::cout << "[Test Taskloop] 2. Parallel for (2 threads)...\n";
    BenchResult res_for = SignatureBench::run_parallel(devices, 2, batch_size);
    if (res_for.valid_count != batch_size) {
        std::cerr << "Parallel for valid_count mismatch: " << res_for.valid_count << " != " << batch_size << "\n";
        return 1;
    }

    std::cout << "[Test Taskloop] 3. Parallel taskloop (2 threads, default grainsize)...\n";
    BenchResult res_task_default = SignatureBench::run_parallel_taskloop(devices, 2, batch_size, 0);
    if (res_task_default.valid_count != batch_size || res_task_default.valid_count != res_for.valid_count) {
        std::cerr << "Taskloop default valid_count mismatch!\n";
        return 1;
    }

    std::cout << "[Test Taskloop] 4. Parallel taskloop (2 threads, grainsize=15)...\n";
    BenchResult res_task_g15 = SignatureBench::run_parallel_taskloop(devices, 2, batch_size, 15);
    if (res_task_g15.valid_count != batch_size || res_task_g15.valid_count != res_for.valid_count) {
        std::cerr << "Taskloop grainsize=15 valid_count mismatch!\n";
        return 1;
    }

    std::cout << "[Test Taskloop] 5. Parallel taskloop (4 threads, grainsize=7)...\n";
    BenchResult res_task_g7 = SignatureBench::run_parallel_taskloop(devices, 4, batch_size, 7);
    if (res_task_g7.valid_count != batch_size || res_task_g7.valid_count != res_for.valid_count) {
        std::cerr << "Taskloop grainsize=7 valid_count mismatch!\n";
        return 1;
    }

    std::cout << "[Test Taskloop] 6. Tamper one signature and verify rejection...\n";
    devices[0].signature[0] ^= 0xFF;
    BenchResult res_tampered_for = SignatureBench::run_parallel(devices, 2, batch_size);
    BenchResult res_tampered_task = SignatureBench::run_parallel_taskloop(devices, 2, batch_size, 10);
    if (res_tampered_for.valid_count != batch_size - 1 || res_tampered_task.valid_count != batch_size - 1) {
        std::cerr << "Tampered rejection mismatch!\n";
        return 1;
    }

    std::cout << "[Test Taskloop] All taskloop tests passed successfully! (valid_count == batch validated)\n";
    return 0;
}
