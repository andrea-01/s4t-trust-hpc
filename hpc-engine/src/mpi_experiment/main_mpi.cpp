#include <mpi.h>
#include <iostream>
#include <vector>
#include <fstream>
#include <chrono>
#include <string>
#include <openssl/evp.h>
#include "device_generator.hpp"
#include "signature_bench.hpp"

// Sanity check function
bool run_sanity_check() {
    auto devices = DeviceGenerator::generate_devices(1, 42);
    auto& dev = devices[0];

    auto verify = [](const Device& d) {
        EVP_MD_CTX_ptr mdctx(EVP_MD_CTX_new());
        if (!mdctx || EVP_DigestVerifyInit(mdctx.get(), nullptr, EVP_sha256(), nullptr, d.keypair.get()) <= 0) {
            return false;
        }
        return EVP_DigestVerify(mdctx.get(), d.signature.data(), d.signature.size(), d.message.data(), d.message.size()) == 1;
    };

    // 1. Verify valid signature
    if (!verify(dev)) {
        std::cerr << "[Sanity Check] Failed to verify valid signature.\n";
        return false;
    }
    
    // 2. Tamper with the signature and verify it fails
    dev.signature[0] ^= 0xFF; // Flip bits
    if (verify(dev)) {
        std::cerr << "[Sanity Check] Verification accepted tampered signature!\n";
        return false;
    }

    std::cout << "[Sanity Check] Passed: Valid signature accepted, tampered signature rejected.\n";
    return true;
}

int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (rank == 0) {
        if (!run_sanity_check()) {
            std::cerr << "Sanity check failed, aborting.\n";
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
    }

    // Wait for rank 0 to finish sanity check
    MPI_Barrier(MPI_COMM_WORLD);

    const size_t total_batch_size = 10000;
    
    // Determine this rank's share
    size_t local_batch_size = total_batch_size / size;
    size_t remainder = total_batch_size % size;
    if (static_cast<size_t>(rank) < remainder) {
        local_batch_size++;
    }

    // Generate local devices using deterministic seed per rank
    unsigned int base_seed = 1000;
    auto local_devices = DeviceGenerator::generate_devices(local_batch_size, base_seed + rank);

    // Wait for all ranks to generate data so the timing reflects just the verification phase
    MPI_Barrier(MPI_COMM_WORLD);

    // Run verification on local data using sequential function from M5
    BenchResult local_res = SignatureBench::run_sequential(local_devices);

    // Reduce results
    size_t total_verified = 0;
    double max_time = 0.0;

    MPI_Reduce(&local_res.batch_size, &total_verified, 1, MPI_UNSIGNED_LONG_LONG, MPI_SUM, 0, MPI_COMM_WORLD);
    MPI_Reduce(&local_res.time_seconds, &max_time, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        double global_throughput = (max_time > 0) ? (total_verified / max_time) : 0.0;
        std::cout << "--- MPI Run Complete ---\n";
        std::cout << "Ranks: " << size << "\n";
        std::cout << "Total Devices: " << total_verified << "\n";
        std::cout << "Max Time (s): " << max_time << "\n";
        std::cout << "Global Throughput (sig/s): " << global_throughput << "\n";

        // Append to results_mpi.csv
        std::ofstream out("results_mpi.csv", std::ios::app);
        if (out) {
            // Write header if file is empty
            out.seekp(0, std::ios::end);
            if (out.tellp() == 0) {
                out << "model,batch_size,num_threads,time_seconds,throughput\n";
            }
            out << "mpi,"
                << total_verified << ","
                << size << ","
                << max_time << ","
                << global_throughput << "\n";
        } else {
            std::cerr << "Failed to write to results_mpi.csv\n";
        }
    }

    MPI_Finalize();
    return 0;
}
