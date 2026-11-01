#include <mpi.h>
#include <iostream>
#include <vector>
#include <fstream>
#include <string>
#include <thread>
#include <algorithm>
#include <cstdlib>
#include <openssl/evp.h>
#include "device_generator.hpp"
#include "signature_bench.hpp"

// Message tags for dynamic master-worker protocol
enum MsgTag {
    TAG_REQUEST = 1,     // Worker -> Master: request work (includes previous chunk report: {processed, valid})
    TAG_WORK = 2,        // Master -> Worker: chunk assignment {start_index, count}
    TAG_TERMINATE = 3    // Master -> Worker: no more work available, terminate
};

// Sanity check function for signature verification
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

    if (!verify(dev)) {
        std::cerr << "[Sanity Check] Failed to verify valid signature.\n";
        return false;
    }
    
    dev.signature[0] ^= 0xFF;
    if (verify(dev)) {
        std::cerr << "[Sanity Check] Verification accepted tampered signature!\n";
        return false;
    }

    std::cout << "[Sanity Check] Passed: Valid signature accepted, tampered signature rejected.\n";
    return true;
}

int main(int argc, char** argv) {
    // Initialize MPI with thread support (MPI_THREAD_FUNNELED: MPI calls only from master thread)
    int provided = 0;
    int init_status = MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);
    if (init_status != MPI_SUCCESS || provided < MPI_THREAD_FUNNELED) {
        std::cerr << "Fatal: MPI implementation does not provide required MPI_THREAD_FUNNELED support. "
                  << "Provided level: " << provided << ", required: " << MPI_THREAD_FUNNELED << ". Aborting.\n";
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (size < 2) {
        if (rank == 0) {
            std::cerr << "Fatal: Dynamic master-worker requires at least 2 MPI ranks (1 master + >= 1 worker). "
                      << "Provided: " << size << " ranks. Aborting.\n";
        }
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    if (rank == 0) {
        if (!run_sanity_check()) {
            std::cerr << "Sanity check failed, aborting.\n";
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
    }

    MPI_Barrier(MPI_COMM_WORLD);

    // CLI Arguments:
    // argv[1]: total_batch_size (default: 500)
    // argv[2]: chunk_size (default: 50)
    // argv[3]: num_threads (default: auto)
    // argv[4]: csv_file (default: "results_mpi_dynamic.csv")
    const size_t total_batch_size = (argc > 1) ? std::stoull(argv[1]) : 500;
    const size_t chunk_size = (argc > 2) ? std::stoull(argv[2]) : 50;

    int num_threads = 0;
    if (argc > 3) {
        try {
            num_threads = std::stoi(argv[3]);
        } catch (...) {
            num_threads = 0;
        }
    }
    if (num_threads <= 0) {
        const char* env_threads = std::getenv("OMP_NUM_THREADS");
        if (!env_threads) {
            env_threads = std::getenv("NUM_THREADS");
        }
        if (env_threads) {
            try {
                num_threads = std::stoi(env_threads);
            } catch (...) {
                num_threads = 0;
            }
        }
    }
    if (num_threads <= 0) {
        unsigned int hw_threads = std::thread::hardware_concurrency();
        if (hw_threads == 0) {
            hw_threads = 1;
        }
        num_threads = std::max(1, static_cast<int>(hw_threads / static_cast<unsigned int>(size - 1)));
    }

    const std::string csv_file = (argc > 4) ? argv[4] : "results_mpi_dynamic.csv";

    // 1. Generation Phase: Pre-generate all devices BEFORE timed region.
    // Rank 0 is dedicated coordinator and does not need dataset in memory.
    // Worker ranks (1..size-1) generate deterministic dataset using fixed base seed.
    double t_gen_start = MPI_Wtime();
    std::vector<Device> all_devices;
    unsigned int base_seed = 5000;
    if (rank != 0) {
        all_devices = DeviceGenerator::generate_devices(total_batch_size, base_seed);
    }
    double t_gen_local = MPI_Wtime() - t_gen_start;

    // Synchronize all ranks after generation so timing excludes setup/keygen
    MPI_Barrier(MPI_COMM_WORLD);

    double worker_total_time = 0.0;
    double worker_verify_time = 0.0;
    size_t worker_valid_count = 0;
    size_t worker_processed_count = 0;

    if (rank == 0) {
        // --- MASTER PROCESS ---
        // Explicitly declared: Rank 0 does NOT verify signatures; it distributes tasks dynamically.
        // With R total ranks, there are R-1 worker processes.
        std::cout << "[MPI Dynamic Master-Worker] Rank 0 is dedicated coordinator (does NOT verify signatures).\n";
        std::cout << "[MPI Dynamic Master-Worker] Total MPI ranks: " << size 
                  << " (1 Master + " << (size - 1) << " Workers)\n";
        std::cout << "[MPI Dynamic Master-Worker] Chunk size: " << chunk_size 
                  << ", Total batch: " << total_batch_size << ", Threads/Worker: " << num_threads << "\n";

        size_t next_index = 0;
        size_t active_workers = static_cast<size_t>(size - 1);
        size_t total_processed = 0;
        size_t total_valid = 0;

        while (active_workers > 0) {
            MPI_Status status;
            long report[2] = {0, 0}; // {processed_count, valid_count}
            MPI_Recv(report, 2, MPI_LONG, MPI_ANY_SOURCE, TAG_REQUEST, MPI_COMM_WORLD, &status);
            int worker_rank = status.MPI_SOURCE;

            total_processed += static_cast<size_t>(report[0]);
            total_valid += static_cast<size_t>(report[1]);

            if (next_index < total_batch_size) {
                size_t current_chunk = std::min(chunk_size, total_batch_size - next_index);
                long work[2] = {
                    static_cast<long>(next_index),
                    static_cast<long>(current_chunk)
                };
                MPI_Send(work, 2, MPI_LONG, worker_rank, TAG_WORK, MPI_COMM_WORLD);
                next_index += current_chunk;
            } else {
                long terminate_msg[2] = {0, 0};
                MPI_Send(terminate_msg, 2, MPI_LONG, worker_rank, TAG_TERMINATE, MPI_COMM_WORLD);
                active_workers--;
            }
        }

        // Cross-check: valid_count must strictly equal total_batch_size
        if (total_valid != total_batch_size || total_processed != total_batch_size) {
            std::cerr << "Fatal Error: Verification count mismatch! total_valid=" << total_valid 
                      << ", total_processed=" << total_processed 
                      << ", expected=" << total_batch_size << ". Aborting.\n";
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
    } else {
        // --- WORKER PROCESS ---
        // Workers request chunks dynamically from Master (Rank 0)
        double t_worker_start = MPI_Wtime();
        long report[2] = {0, 0}; // Initial request has 0 processed, 0 valid

        while (true) {
            MPI_Send(report, 2, MPI_LONG, 0, TAG_REQUEST, MPI_COMM_WORLD);

            MPI_Status status;
            long work[2];
            MPI_Recv(work, 2, MPI_LONG, 0, MPI_ANY_TAG, MPI_COMM_WORLD, &status);

            if (status.MPI_TAG == TAG_TERMINATE) {
                break;
            }

            size_t start_idx = static_cast<size_t>(work[0]);
            size_t count = static_cast<size_t>(work[1]);

            // Execute parallel verification on pre-generated devices
            BenchResult res = SignatureBench::run_parallel_range(all_devices, start_idx, count, num_threads);
            worker_verify_time += res.time_seconds;
            worker_processed_count += res.batch_size;
            worker_valid_count += res.valid_count;

            report[0] = static_cast<long>(res.batch_size);
            report[1] = static_cast<long>(res.valid_count);
        }

        worker_total_time = MPI_Wtime() - t_worker_start;
    }

    // Synchronize completion of all worker activity
    MPI_Barrier(MPI_COMM_WORLD);

    // Reduction phase to compute global metrics consistent with main_mpi.cpp
    double t_reduce_start = MPI_Wtime();
    double max_gen_time = 0.0;
    double max_worker_time = 0.0;
    double max_verify_time = 0.0;
    size_t total_verified = 0;

    MPI_Reduce(&worker_total_time, &max_worker_time, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&worker_verify_time, &max_verify_time, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&t_gen_local, &max_gen_time, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&worker_valid_count, &total_verified, 1, MPI_UNSIGNED_LONG_LONG, MPI_SUM, 0, MPI_COMM_WORLD);

    double t_reduce_end = MPI_Wtime();
    double reduce_time = t_reduce_end - t_reduce_start;

    if (rank == 0) {
        // Denominator is max worker time (excluding setup/keygen), matching main_mpi.cpp
        double throughput = (max_worker_time > 0) ? (static_cast<double>(total_verified) / max_worker_time) : 0.0;

        std::cout << "--- MPI Dynamic Master-Worker Complete ---\n";
        std::cout << "MPI Ranks: " << size << " (1 Master + " << (size - 1) << " Workers)\n";
        std::cout << "Worker Threads: " << num_threads << "\n";
        std::cout << "Chunk Size: " << chunk_size << "\n";
        std::cout << "Total Devices Verified: " << total_verified << "\n";
        std::cout << "Valid Signatures: " << total_verified << " (100% Match: YES)\n";
        std::cout << "Max Worker Time (s): " << max_worker_time << "\n";
        std::cout << "Global Throughput (sig/s): " << throughput << "\n";
        std::cout << "Phase Breakdown (s): Gen=" << max_gen_time
                  << " Verify=" << max_verify_time
                  << " Reduce=" << reduce_time << "\n";

        // Append to CSV
        std::ofstream out(csv_file, std::ios::app);
        if (out) {
            out.seekp(0, std::ios::end);
            if (out.tellp() == 0) {
                out << "model,batch_size,mpi_ranks,omp_threads,time_seconds,throughput,chunk_size,worker_ranks,valid_count,gen_time_seconds,verify_time_seconds,reduce_time_seconds\n";
            }
            out << "mpi_dynamic,"
                << total_batch_size << ","
                << size << ","
                << num_threads << ","
                << max_worker_time << ","
                << throughput << ","
                << chunk_size << ","
                << (size - 1) << ","
                << total_verified << ","
                << max_gen_time << ","
                << max_verify_time << ","
                << reduce_time << "\n";
        } else {
            std::cerr << "Failed to write to " << csv_file << "\n";
        }
    }

    MPI_Finalize();
    return 0;
}
