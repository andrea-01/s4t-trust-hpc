#!/usr/bin/env python3
"""
Full Campaign Runner for Stage 11.5
Executes:
- Task B: Extended Grid (gRPC + OpenMP)
- Task B: Extended Grid (MPI + OpenMP Hybrid)
- Task C: Amdahl Anomaly & Straggler Network vs Compute Decomposition
"""

import asyncio
import csv
import math
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent.parent
HPC_DIR = REPO_ROOT / "hpc-engine"
RESULTS_DIR = HPC_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

if str(BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(BENCH_DIR))

import grpc
import pipeline_pb2
import pipeline_pb2_grpc
from google.protobuf.empty_pb2 import Empty

ENV_ID = "i7_12700h_20260908"
MAX_LOGICAL_CORES = 20  # Host hardware constraint: 14 cores, 20 threads

# Worker ports: 51051 to 51082
ALL_WORKERS = [f"127.0.0.1:{p}" for p in range(51051, 51083)]

async def ping_worker(addr: str, timeout: float = 5.0) -> bool:
    try:
        async with grpc.aio.insecure_channel(addr) as channel:
            stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
            status = await stub.Ping(Empty(), timeout=timeout)
            return status.healthy
    except Exception as e:
        print(f"[!] Ping failed for {addr}: {e}")
        return False

async def dispatch_single_worker(addr: str, batch_size: int, num_threads: int, seed: int, timeout: float = 60.0):
    async with grpc.aio.insecure_channel(addr) as channel:
        stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
        req = pipeline_pb2.TaskRequest(
            operation=pipeline_pb2.OperationType.VERIFY_SIGNATURES_BATCH,
            batch_size=batch_size,
            num_threads=num_threads,
            seed=seed,
            pipeline_id="bench-task-parallel"
        )
        t_start = time.perf_counter()
        res = await stub.ExecuteTask(req, timeout=timeout)
        t_end = time.perf_counter()
        rpc_latency = t_end - t_start
        worker_time = res.time_seconds
        network_overhead = max(0.0, rpc_latency - worker_time)
        return {
            "node_id": res.node_id,
            "valid_count": res.valid_count,
            "worker_time_seconds": worker_time,
            "worker_throughput": res.throughput,
            "rpc_latency_seconds": rpc_latency,
            "network_overhead_seconds": network_overhead
        }

async def run_parallel_batch(
    worker_addrs: List[str],
    total_batch: int,
    num_threads: int,
    base_seed: int = 42
) -> Dict[str, Any]:
    num_nodes = len(worker_addrs)
    base_chunk = total_batch // num_nodes
    remainder = total_batch % num_nodes
    chunks = [base_chunk + (1 if i < remainder else 0) for i in range(num_nodes)]
    
    tasks = []
    for i, (addr, chunk_size) in enumerate(zip(worker_addrs, chunks)):
        seed = base_seed + i
        tasks.append(dispatch_single_worker(addr, chunk_size, num_threads, seed))
        
    t_start = time.perf_counter()
    responses = await asyncio.gather(*tasks)
    t_end = time.perf_counter()
    
    total_time = t_end - t_start
    total_valid = sum(r["valid_count"] for r in responses)
    
    if total_valid != total_batch:
        raise ValueError(
            f"CORRECTNESS CHECK FAILED: Expected {total_batch} valid signatures, "
            f"but workers returned {total_valid} valid signatures!"
        )
        
    throughput = total_batch / total_time if total_time > 0 else 0.0
    effective_parallelism = num_nodes * num_threads
    is_oversubscribed = effective_parallelism > MAX_LOGICAL_CORES
    
    return {
        "nodes": num_nodes,
        "threads_per_node": num_threads,
        "effective_parallelism": effective_parallelism,
        "is_oversubscribed": is_oversubscribed,
        "total_batch_size": total_batch,
        "total_valid_count": total_valid,
        "total_time_seconds": total_time,
        "aggregate_throughput": throughput,
        "responses": responses
    }

async def execute_task_b_grpc():
    out_csv = RESULTS_DIR / f"grid_grpc_{ENV_ID}.csv"
    if out_csv.exists() and out_csv.stat().st_size > 500:
        print(f"[*] Task B (gRPC) results already exist at {out_csv} ({out_csv.stat().st_size} bytes). Skipping to save time.")
        return []

    print("\n" + "="*80)
    print("TASK B: EXTENDED GRID — ISOLATED gRPC + OPENMP")
    print(f"Host Max Cores: {MAX_LOGICAL_CORES} | env_id: {ENV_ID}")
    print("="*80)
    
    node_counts = [1, 2, 4, 8, 16, 32]
    thread_counts = [1, 2, 4, 8]
    batch_sizes = [1000, 5000]
    repeats = 3
    
    # Check all workers online
    for addr in ALL_WORKERS:
        if not await ping_worker(addr):
            raise RuntimeError(f"Worker {addr} is not reachable!")
    print(f"[+] All {len(ALL_WORKERS)} worker nodes verified healthy.\n")
    
    results = []
    
    for batch_size in batch_sizes:
        print(f"\n>>> Batch Size: {batch_size} <<<")
        for nodes in node_counts:
            selected_workers = ALL_WORKERS[:nodes]
            for threads in thread_counts:
                peff = nodes * threads
                oversub_str = "[OVERSUBSCRIBED]" if peff > MAX_LOGICAL_CORES else "[CLEAN]"
                print(f" -> {nodes:2d} nodes x {threads} threads (P_eff={peff:3d}) {oversub_str:16s}... ", end="", flush=True)
                
                # Warmup
                await run_parallel_batch(selected_workers, batch_size, threads, base_seed=999)
                
                times = []
                throughputs = []
                for r in range(repeats):
                    res = await run_parallel_batch(selected_workers, batch_size, threads, base_seed=42 + r*17)
                    times.append(res["total_time_seconds"])
                    throughputs.append(res["aggregate_throughput"])
                    
                best_t = min(times)
                avg_t = statistics.mean(times)
                stddev_t = statistics.stdev(times) if len(times) > 1 else 0.0
                best_tp = max(throughputs)
                avg_tp = statistics.mean(throughputs)
                
                print(f"Avg: {avg_t*1000:6.2f} ms (±{stddev_t*1000:5.2f}) | Throughput: {avg_tp:8.1f} sig/s (Best: {best_tp:8.1f})")
                
                results.append({
                    "env_id": ENV_ID,
                    "batch_size": batch_size,
                    "nodes": nodes,
                    "threads_per_node": threads,
                    "effective_parallelism": peff,
                    "is_oversubscribed": peff > MAX_LOGICAL_CORES,
                    "best_time_seconds": best_t,
                    "avg_time_seconds": avg_t,
                    "stddev_seconds": stddev_t,
                    "best_throughput": best_tp,
                    "avg_throughput": avg_tp
                })
                
    out_csv = RESULTS_DIR / f"grid_grpc_{ENV_ID}.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "env_id", "batch_size", "nodes", "threads_per_node", "effective_parallelism",
            "is_oversubscribed", "best_time_seconds", "avg_time_seconds", "stddev_seconds",
            "best_throughput", "avg_throughput"
        ])
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"\n[+] Task B (gRPC) results written to: {out_csv}")
    return results

def execute_task_b_mpi():
    print("\n" + "="*80)
    print("TASK B: EXTENDED GRID — HYBRID MPI + OPENMP")
    print(f"Host Max Cores: {MAX_LOGICAL_CORES} | env_id: {ENV_ID}")
    print("="*80)
    
    rank_counts = [1, 2, 4, 8, 16, 32]
    thread_counts = [1, 2, 4, 8]
    batch_sizes = [1000, 5000]
    repeats = 3
    
    results = []
    
    for batch_size in batch_sizes:
        print(f"\n>>> Batch Size: {batch_size} <<<")
        for ranks in rank_counts:
            for threads in thread_counts:
                peff = ranks * threads
                oversub_str = "[OVERSUBSCRIBED]" if peff > MAX_LOGICAL_CORES else "[CLEAN]"
                print(f" -> {ranks:2d} ranks x {threads} threads (P_eff={peff:3d}) {oversub_str:16s}... ", end="", flush=True)
                
                times = []
                throughputs = []
                
                for r in range(repeats):
                    cmd = [
                        "docker", "run", "--rm",
                        "--entrypoint", "mpirun",
                        "deploy-bench-worker-1:latest",
                        "--allow-run-as-root", "--bind-to", "none", "--oversubscribe",
                        "-np", str(ranks),
                        "./build/hpc_engine_mpi",
                        str(batch_size), str(threads), "/tmp/run.csv"
                    ]
                    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if proc.returncode != 0:
                        raise RuntimeError(f"mpirun failed with code {proc.returncode}:\n{proc.stderr}")
                        
                    # Parse stdout
                    out = proc.stdout
                    m_dev = re.search(r"Total Devices:\s*(\d+)", out)
                    m_time = re.search(r"Max Time \(s\):\s*([\d\.]+)", out)
                    m_tp = re.search(r"Global Throughput \(sig/s\):\s*([\d\.]+)", out)
                    
                    if not (m_dev and m_time and m_tp):
                        raise RuntimeError(f"Failed to parse MPI output:\n{out}")
                        
                    total_dev = int(m_dev.group(1))
                    if total_dev != batch_size:
                        raise ValueError(f"CORRECTNESS FAILED in MPI: expected {batch_size}, got {total_dev}")
                        
                    t_val = float(m_time.group(1))
                    tp_val = float(m_tp.group(1))
                    times.append(t_val)
                    throughputs.append(tp_val)
                    
                best_t = min(times)
                avg_t = statistics.mean(times)
                stddev_t = statistics.stdev(times) if len(times) > 1 else 0.0
                best_tp = max(throughputs)
                avg_tp = statistics.mean(throughputs)
                
                print(f"Avg: {avg_t*1000:6.2f} ms (±{stddev_t*1000:5.2f}) | Throughput: {avg_tp:8.1f} sig/s (Best: {best_tp:8.1f})")
                
                results.append({
                    "env_id": ENV_ID,
                    "batch_size": batch_size,
                    "mpi_ranks": ranks,
                    "omp_threads": threads,
                    "effective_parallelism": peff,
                    "is_oversubscribed": peff > MAX_LOGICAL_CORES,
                    "best_time_seconds": best_t,
                    "avg_time_seconds": avg_t,
                    "stddev_seconds": stddev_t,
                    "best_throughput": best_tp,
                    "avg_throughput": avg_tp
                })
                
    out_csv = RESULTS_DIR / f"grid_mpi_omp_{ENV_ID}.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "env_id", "batch_size", "mpi_ranks", "omp_threads", "effective_parallelism",
            "is_oversubscribed", "best_time_seconds", "avg_time_seconds", "stddev_seconds",
            "best_throughput", "avg_throughput"
        ])
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"\n[+] Task B (MPI+OpenMP) results written to: {out_csv}")
    return results

async def execute_task_c_investigation():
    print("\n" + "="*80)
    print("TASK C: AMDAHL ANOMALY & STRAGGLER / NETWORK OVERHEAD DECOMPOSITION")
    print(f"10 repetitions per configuration on P in [8, 16, 32]")
    print("="*80)
    
    test_configs = [
        # (nodes, threads, batch)
        (8, 1, 1000),
        (8, 1, 5000),
        (8, 8, 1000),
        (8, 8, 5000),
        (16, 1, 1000),
        (16, 1, 5000),
        (16, 8, 1000),
        (16, 8, 5000),
        (32, 1, 1000),
        (32, 1, 5000),
        (32, 8, 1000),
        (32, 8, 5000),
    ]
    
    repeats = 10
    detail_records = []
    
    for nodes, threads, batch in test_configs:
        selected_workers = ALL_WORKERS[:nodes]
        peff = nodes * threads
        oversub_str = "[OVERSUBSCRIBED]" if peff > MAX_LOGICAL_CORES else "[CLEAN]"
        print(f"\n--- Investigating N={nodes:2d}, T={threads}, Batch={batch} (P_eff={peff:3d}) {oversub_str} [10 runs] ---")
        
        # Warmup
        await run_parallel_batch(selected_workers, batch, threads, base_seed=888)
        
        run_data = []
        for r in range(repeats):
            res = await run_parallel_batch(selected_workers, batch, threads, base_seed=100 + r*13)
            tot_time = res["total_time_seconds"]
            responses = res["responses"]
            
            worker_times = [resp["worker_time_seconds"] for resp in responses]
            rpc_latencies = [resp["rpc_latency_seconds"] for resp in responses]
            network_overheads = [resp["network_overhead_seconds"] for resp in responses]
            
            max_w_t = max(worker_times)
            min_w_t = min(worker_times)
            avg_w_t = statistics.mean(worker_times)
            
            max_rpc_t = max(rpc_latencies)
            min_rpc_t = min(rpc_latencies)
            avg_rpc_t = statistics.mean(rpc_latencies)
            
            max_net_ovh = max(network_overheads)
            avg_net_ovh = statistics.mean(network_overheads)
            
            # Straggler ratio: max / avg
            compute_straggler_ratio = max_w_t / avg_w_t if avg_w_t > 0 else 1.0
            rpc_straggler_ratio = max_rpc_t / avg_rpc_t if avg_rpc_t > 0 else 1.0
            net_fraction = avg_net_ovh / avg_rpc_t if avg_rpc_t > 0 else 0.0
            
            rec = {
                "env_id": ENV_ID,
                "nodes": nodes,
                "threads": threads,
                "batch_size": batch,
                "effective_parallelism": peff,
                "is_oversubscribed": peff > MAX_LOGICAL_CORES,
                "run_index": r + 1,
                "total_time_seconds": tot_time,
                "throughput": res["aggregate_throughput"],
                "max_worker_compute_s": max_w_t,
                "avg_worker_compute_s": avg_w_t,
                "min_worker_compute_s": min_w_t,
                "max_rpc_latency_s": max_rpc_t,
                "avg_rpc_latency_s": avg_rpc_t,
                "avg_network_overhead_s": avg_net_ovh,
                "max_network_overhead_s": max_net_ovh,
                "network_overhead_fraction": net_fraction,
                "compute_straggler_ratio": compute_straggler_ratio,
                "rpc_straggler_ratio": rpc_straggler_ratio
            }
            detail_records.append(rec)
            run_data.append(rec)
            
        all_tot = [d["total_time_seconds"] for d in run_data]
        all_tp = [d["throughput"] for d in run_data]
        all_net_frac = [d["network_overhead_fraction"] for d in run_data]
        all_comp_t = [d["avg_worker_compute_s"] for d in run_data]
        all_net_ovh = [d["avg_network_overhead_s"] for d in run_data]
        
        print(f"  Summary over 10 runs:")
        print(f"    Total Time:    Median={statistics.median(all_tot)*1000:6.2f}ms | Mean={statistics.mean(all_tot)*1000:6.2f}ms (±{statistics.stdev(all_tot)*1000:5.2f}) | Min={min(all_tot)*1000:6.2f}ms | Max={max(all_tot)*1000:6.2f}ms")
        print(f"    Avg Compute:   {statistics.mean(all_comp_t)*1000:6.2f} ms")
        print(f"    Avg Net Ovh:   {statistics.mean(all_net_ovh)*1000:6.2f} ms  ({statistics.mean(all_net_frac)*100:5.1f}% of per-worker time)")
        print(f"    Throughput:    Median={statistics.median(all_tp):8.1f} | Mean={statistics.mean(all_tp):8.1f} sig/s (±{statistics.stdev(all_tp):6.1f})")

    out_csv = RESULTS_DIR / f"amdahl_investigation_{ENV_ID}.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(detail_records[0].keys()))
        writer.writeheader()
        for row in detail_records:
            writer.writerow(row)
    print(f"\n[+] Task C investigation written to: {out_csv}")
    return detail_records

async def main_async():
    await execute_task_b_grpc()
    execute_task_b_mpi()
    await execute_task_c_investigation()

if __name__ == "__main__":
    asyncio.run(main_async())
