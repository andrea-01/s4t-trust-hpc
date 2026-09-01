#!/usr/bin/env python3
"""
Standalone Benchmark Driver for Isolated Task Parallelism (gRPC + OpenMP)
Stage 11.3 - HPC Metrics and Evaluation
"""

import argparse
import asyncio
import csv
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Ensure stubs are generated from proto/pipeline.proto
BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent.parent
PROTO_DIR = REPO_ROOT / "proto"
PROTO_FILE = PROTO_DIR / "pipeline.proto"

# Add bench dir to sys.path to import generated stubs
if str(BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(BENCH_DIR))

def ensure_stubs():
    pb2_file = BENCH_DIR / "pipeline_pb2.py"
    pb2_grpc_file = BENCH_DIR / "pipeline_pb2_grpc.py"
    
    need_gen = False
    if not pb2_file.exists() or not pb2_grpc_file.exists():
        need_gen = True
    elif PROTO_FILE.stat().st_mtime > pb2_file.stat().st_mtime:
        need_gen = True
        
    if need_gen:
        import grpc_tools.protoc
        import inspect
        proto_include = os.path.join(os.path.dirname(inspect.getfile(grpc_tools)), '_proto')
        print(f"[*] Generating Python gRPC stubs from {PROTO_FILE} into {BENCH_DIR}...")
        res = grpc_tools.protoc.main([
            "grpc_tools.protoc",
            f"-I{PROTO_DIR}",
            f"-I{proto_include}",
            f"--python_out={BENCH_DIR}",
            f"--grpc_python_out={BENCH_DIR}",
            str(PROTO_FILE)
        ])
        if res != 0:
            raise RuntimeError(f"protoc failed with exit code {res}")
        print("[+] Stubs generated successfully.")

ensure_stubs()

import grpc
import pipeline_pb2
import pipeline_pb2_grpc
from google.protobuf.empty_pb2 import Empty

MAX_LOGICAL_CORES = 20  # Host hardware constraint verified with nproc / lscpu

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
        return {
            "node_id": res.node_id,
            "valid_count": res.valid_count,
            "worker_time_seconds": res.time_seconds,
            "worker_throughput": res.throughput,
            "rpc_latency_seconds": t_end - t_start
        }

async def run_parallel_batch(
    worker_addrs: List[str],
    total_batch: int,
    num_threads: int,
    base_seed: int = 42
) -> Dict[str, Any]:
    num_nodes = len(worker_addrs)
    
    # Chunking with remainder distribution identical to main_mpi.cpp
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
    
    # Strict correctness validation as requested
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

async def main_async():
    parser = argparse.ArgumentParser(description="Task Parallelism gRPC + OpenMP Benchmark")
    parser.add_argument("--workers", default="localhost:50051,localhost:50052,localhost:50053,localhost:50054,localhost:50055,localhost:50056,localhost:50057,localhost:50058",
                        help="Comma-separated list of worker addresses")
    parser.add_argument("--batch-sizes", default="1000,5000", help="Comma-separated batch sizes to test")
    parser.add_argument("--node-counts", default="1,2,4,8", help="Node counts to test")
    parser.add_argument("--thread-counts", default="1,2,4", help="Thread counts per node to test")
    parser.add_argument("--output-csv", default=str(REPO_ROOT / "hpc-engine" / "results_grpc_task_parallel.csv"),
                        help="Output CSV path")
    parser.add_argument("--runs", type=int, default=3, help="Number of repetitions per configuration for stability")
    args = parser.parse_args()
    
    all_workers = [w.strip() for w in args.workers.split(",") if w.strip()]
    batch_sizes = [int(b.strip()) for b in args.batch_sizes.split(",") if b.strip()]
    node_counts = [int(n.strip()) for n in args.node_counts.split(",") if n.strip()]
    thread_counts = [int(t.strip()) for t in args.thread_counts.split(",") if t.strip()]
    
    print(f"[*] Checking health of {len(all_workers)} worker nodes...")
    for addr in all_workers:
        healthy = await ping_worker(addr)
        if not healthy:
            print(f"[X] Worker at {addr} is NOT reachable or healthy. Aborting.")
            sys.exit(1)
        print(f"  [+] Worker {addr}: ONLINE")
        
    # Build grid
    grid = []
    for nodes in node_counts:
        for threads in thread_counts:
            # Special case: 1 node can also test 8 threads for baseline comparison
            grid.append((nodes, threads))
    if (1, 8) not in grid:
        grid.append((1, 8))
    # Sort grid by nodes then threads
    grid = sorted(list(set(grid)), key=lambda x: (x[0], x[1]))
    
    all_results = []
    
    print("\n" + "="*80)
    print("STARTING TASK PARALLELISM (gRPC + OpenMP) BENCHMARK CAMPAIGN")
    print(f"Max Host Logical Cores: {MAX_LOGICAL_CORES}")
    print("="*80)
    
    for batch_size in batch_sizes:
        print(f"\n>>> Running Batch Size = {batch_size} <<<")
        for (nodes, threads) in grid:
            if nodes > len(all_workers):
                print(f"[-] Skipping nodes={nodes} (only {len(all_workers)} workers configured)")
                continue
                
            selected_workers = all_workers[:nodes]
            peff = nodes * threads
            oversub_str = "[OVERSUBSCRIBED PROBE]" if peff > MAX_LOGICAL_CORES else "[CLEAN]"
            
            print(f" -> Testing {nodes} nodes x {threads} threads (P_eff = {peff}) {oversub_str}...", end="", flush=True)
            
            # Warmup
            await run_parallel_batch(selected_workers, batch_size, threads, base_seed=1000)
            
            # Measurements
            run_times = []
            run_throughputs = []
            for r in range(args.runs):
                res = await run_parallel_batch(selected_workers, batch_size, threads, base_seed=42 + r * 10)
                run_times.append(res["total_time_seconds"])
                run_throughputs.append(res["aggregate_throughput"])
                
            best_time = min(run_times)
            avg_time = sum(run_times) / len(run_times)
            best_throughput = max(run_throughputs)
            avg_throughput = sum(run_throughputs) / len(run_throughputs)
            
            print(f" Best Time: {best_time*1000:.2f} ms | Throughput: {best_throughput:.1f} sig/s")
            
            all_results.append({
                "batch_size": batch_size,
                "nodes": nodes,
                "threads_per_node": threads,
                "effective_parallelism": peff,
                "is_oversubscribed": peff > MAX_LOGICAL_CORES,
                "best_time_seconds": best_time,
                "avg_time_seconds": avg_time,
                "best_throughput": best_throughput,
                "avg_throughput": avg_throughput
            })
            
    # Save CSV
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "batch_size", "nodes", "threads_per_node", "effective_parallelism",
            "is_oversubscribed", "best_time_seconds", "avg_time_seconds",
            "best_throughput", "avg_throughput"
        ])
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)
            
    print(f"\n[+] Raw results saved to: {out_path}")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
