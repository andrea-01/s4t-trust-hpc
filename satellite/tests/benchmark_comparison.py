#!/usr/bin/env python3
"""
Benchmark Comparison: Isolated gRPC Dispatch vs Real S4T/IoTronic Chain
Stage 11.4 - Multi-run Statistical Evaluation with Individual Runs Logging
"""

import asyncio
import time
import csv
import sys
import os
import statistics
from typing import List, Dict, Any

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))
sys.path.insert(0, '/app/app')
sys.path.insert(0, '/app')

import grpc
import pipeline_pb2
import pipeline_pb2_grpc

from node_registry import registry
from pipeline_client import run_parallel_verification, iotronic_client

WORKER_ADDRS = {
    "worker-1": "worker-1:50051",
    "worker-2": "worker-2:50051",
    "worker-3": "worker-3:50051"
}

async def dispatch_isolated_single_worker(addr: str, batch_size: int, num_threads: int, seed: int):
    async with grpc.aio.insecure_channel(addr) as channel:
        stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
        req = pipeline_pb2.TaskRequest(
            operation=pipeline_pb2.OperationType.VERIFY_SIGNATURES_BATCH,
            batch_size=batch_size,
            num_threads=num_threads,
            seed=seed,
            pipeline_id="bench-isolated"
        )
        t0 = time.perf_counter()
        res = await stub.ExecuteTask(req)
        t1 = time.perf_counter()
        return {
            "node_id": res.node_id,
            "valid_count": res.valid_count,
            "worker_time_seconds": res.time_seconds,
            "worker_throughput": res.throughput,
            "rpc_latency_seconds": t1 - t0
        }

async def run_isolated_parallel_batch(nodes: List[str], total_batch: int, num_threads: int = 1, base_seed: int = 42):
    num_nodes = len(nodes)
    base_chunk = total_batch // num_nodes
    remainder = total_batch % num_nodes
    chunks = [base_chunk + (1 if i < remainder else 0) for i in range(num_nodes)]

    tasks = [
        dispatch_isolated_single_worker(WORKER_ADDRS[node], chunk_size, num_threads, base_seed + i)
        for i, (node, chunk_size) in enumerate(zip(nodes, chunks))
    ]

    t_start = time.perf_counter()
    responses = await asyncio.gather(*tasks)
    t_end = time.perf_counter()

    total_time = t_end - t_start
    total_valid = sum(r["valid_count"] for r in responses)
    if total_valid != total_batch:
        raise ValueError(f"Isolated check failed: {total_valid} != {total_batch}")

    throughput = total_batch / total_time if total_time > 0 else 0.0
    return {
        "nodes": num_nodes,
        "total_batch": total_batch,
        "total_valid": total_valid,
        "total_time_seconds": total_time,
        "throughput": throughput,
        "responses": responses
    }

async def run_comparison_campaign():
    # Warmup Keystone token
    await iotronic_client.get_token(force_refresh=True)

    test_configs = [
        # (nodes_count, batch_size, threads_per_node)
        (1, 1000, 1),
        (2, 1000, 1),
        (3, 1000, 1),
        (1, 5000, 1),
        (2, 5000, 1),
        (3, 5000, 1),
    ]

    NUM_REPETITIONS = 6
    results = []

    print("=" * 80)
    print("CONTROLLED STATISTICAL COMPARISON: ISOLATED gRPC vs REAL S4T/IOTRONIC CHAIN")
    print(f"Configurations: {len(test_configs)}, Repetitions per config: {NUM_REPETITIONS}")
    print("=" * 80)

    for node_count, batch_size, num_threads in test_configs:
        print(f"\n---> Config: {node_count} node(s), batch={batch_size}, threads={num_threads}")
        
        # 1. Lease nodes on-chain via Registry/Gateway
        pipeline_id = await registry.lease_nodes(node_count)
        nodes = await registry.get_pipeline_nodes(pipeline_id)
        print(f"     Leased on-chain nodes: {nodes}")

        try:
            # 2. Run Isolated Benchmark (direct gRPC)
            iso_times = []
            iso_throughputs = []
            for rep in range(NUM_REPETITIONS):
                res_iso = await run_isolated_parallel_batch(nodes, batch_size, num_threads, base_seed=100 + rep*10)
                iso_times.append(res_iso["total_time_seconds"])
                iso_throughputs.append(res_iso["throughput"])

            best_iso_time = min(iso_times)
            avg_iso_time = statistics.mean(iso_times)
            best_iso_tput = max(iso_throughputs)
            avg_iso_tput = statistics.mean(iso_throughputs)

            # 3. Run Real Chain Benchmark (Satellite -> Keystone/IoTronic REST -> WAMP -> Plugin -> Worker)
            real_times = []
            real_throughputs = []
            worker_times = []
            for rep in range(NUM_REPETITIONS):
                res_real = await run_parallel_verification(pipeline_id, nodes, batch_size, num_threads, base_seed=200 + rep*10)
                real_times.append(res_real["total_time_seconds"])
                real_throughputs.append(res_real["aggregate_throughput"])
                max_w_time = max(r["worker_time_seconds"] for r in res_real["node_results"])
                worker_times.append(max_w_time)
                print(f"     [Real Rep {rep+1}] Total: {res_real['total_time_seconds']:.4f}s (Tput: {res_real['aggregate_throughput']:.1f} sig/s), Max Worker Compute: {max_w_time:.4f}s")

            best_real_time = min(real_times)
            avg_real_time = statistics.mean(real_times)
            stdev_real_time = statistics.stdev(real_times) if len(real_times) > 1 else 0.0
            best_real_tput = max(real_throughputs)
            avg_real_tput = statistics.mean(real_throughputs)
            avg_worker_time = statistics.mean(worker_times)

            # Overhead metrics
            delta_time_avg = avg_real_time - avg_iso_time
            overhead_ratio_avg = avg_real_time / avg_iso_time if avg_iso_time > 0 else 1.0

            row = {
                "nodes": node_count,
                "batch_size": batch_size,
                "threads_per_node": num_threads,
                "iso_best_time_s": best_iso_time,
                "iso_avg_time_s": avg_iso_time,
                "iso_best_tput": best_iso_tput,
                "iso_avg_tput": avg_iso_tput,
                "real_best_time_s": best_real_time,
                "real_avg_time_s": avg_real_time,
                "real_stdev_time_s": stdev_real_time,
                "real_best_tput": best_real_tput,
                "real_avg_tput": avg_real_tput,
                "avg_worker_compute_time_s": avg_worker_time,
                "delta_time_avg_s": delta_time_avg,
                "overhead_ratio_avg": overhead_ratio_avg,
                "individual_real_times_s": ";".join(f"{t:.4f}" for t in real_times),
                "individual_iso_times_s": ";".join(f"{t:.4f}" for t in iso_times)
            }
            results.append(row)

            print(f"     => SUMMARY: Isolated={avg_iso_time:.4f}s ({avg_iso_tput:.1f} sig/s) | Real={avg_real_time:.4f}s +/- {stdev_real_time:.4f}s ({avg_real_tput:.1f} sig/s) | Delta={delta_time_avg:.4f}s ({overhead_ratio_avg:.2f}x)")

        finally:
            await registry.release_nodes(pipeline_id)

    # Output CSV
    csv_path = "/tmp/real_chain_overhead_comparison.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"\n[+] Saved detailed results to {csv_path}")

    # Print summary Markdown table
    print("\n" + "=" * 100)
    print("FINAL MULTI-RUN STATISTICAL COMPARISON TABLE")
    print("=" * 100)
    print("| Batch | Nodi | T_isolato (avg) | T_reale (avg +/- std) | T_worker puro | Overhead delta | Overhead Ratio | Tput Isolato | Tput Reale |")
    print("|-------|------|-----------------|-----------------------|---------------|----------------|----------------|--------------|------------|")
    for r in results:
        real_str = f"{r['real_avg_time_s']:.4f}s +/- {r['real_stdev_time_s']:.3f}s"
        print(f"| {r['batch_size']:<5} | {r['nodes']:<4} | {r['iso_avg_time_s']:>13.4f}s | {real_str:>21} | {r['avg_worker_compute_time_s']:>11.4f}s | {r['delta_time_avg_s']:>12.4f}s | {r['overhead_ratio_avg']:>12.2f}x | {r['iso_avg_tput']:>10.1f}/s | {r['real_avg_tput']:>8.1f}/s |")

if __name__ == "__main__":
    asyncio.run(run_comparison_campaign())
