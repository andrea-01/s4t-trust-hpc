#!/usr/bin/env python3
"""
E4b Benchmark:
gRPC benchmark with containers restricted to P-cores (cpuset: 0-11).
Tests p = 4, 8, 12 with 10 interleaved repeats.
Batch = 20,000, Threads = 1.
Saves to hpc-engine/results/m13/results_e4b_grpc_pcores.csv.
"""

import os
import sys
import time
import random
import asyncio
import csv
from pathlib import Path
from typing import List, Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "hpc-engine" / "results" / "m13"
LOGS_DIR = RESULTS_DIR / "logs"

sys.path.insert(0, str(REPO_ROOT / "hpc-engine" / "benchmarks"))
import grpc
import pipeline_pb2
import pipeline_pb2_grpc
from google.protobuf.empty_pb2 import Empty

ALL_WORKERS = [f"localhost:{51051 + i}" for i in range(32)]

def check_governor():
    gov_files = list(Path("/sys/devices/system/cpu").glob("cpu*/cpufreq/scaling_governor"))
    for gf in gov_files:
        gov = gf.read_text().strip()
        if gov != "performance":
            raise RuntimeError(f"CPU governor is '{gov}' on {gf}, must be 'performance'!")
    print(f"[OK] All {len(gov_files)} CPU governors set to 'performance'.")

async def check_health(p_max: int, timeout: float = 5.0):
    print(f"Checking health of {p_max} bench-worker containers...")
    for addr in ALL_WORKERS[:p_max]:
        try:
            async with grpc.aio.insecure_channel(addr) as channel:
                stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
                st = await stub.Ping(Empty(), timeout=timeout)
                if not st.healthy:
                    raise RuntimeError(f"Worker {addr} reported unhealthy")
        except Exception as e:
            raise RuntimeError(f"Worker {addr} unhealthy: {e}")
    print(f"[OK] All {p_max} containers online and healthy.")

async def dispatch_single_worker(addr: str, batch_size: int, num_threads: int, seed: int, timeout: float = 60.0):
    async with grpc.aio.insecure_channel(addr) as channel:
        stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
        req = pipeline_pb2.TaskRequest(
            operation=pipeline_pb2.OperationType.VERIFY_SIGNATURES_BATCH,
            batch_size=batch_size,
            num_threads=num_threads,
            seed=seed,
            pipeline_id="bench-m13-grpc-pcores"
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

async def run_grpc_batch(worker_addrs: List[str], total_batch: int, num_threads: int, base_seed: int = 1000):
    num_nodes = len(worker_addrs)
    base_chunk = total_batch // num_nodes
    remainder = total_batch % num_nodes
    chunks = [base_chunk + (1 if i < remainder else 0) for i in range(num_nodes)]

    tasks = []
    for i, (addr, c_size) in enumerate(zip(worker_addrs, chunks)):
        seed = base_seed + i
        tasks.append(dispatch_single_worker(addr, c_size, num_threads, seed))

    t_start = time.perf_counter()
    responses = await asyncio.gather(*tasks)
    t_end = time.perf_counter()

    total_valid = sum(r["valid_count"] for r in responses)
    if total_valid != total_batch:
        raise RuntimeError(f"gRPC correctness error: {total_valid} valid vs {total_batch} expected")

    max_worker_time = max(r["worker_time_seconds"] for r in responses)
    total_time = t_end - t_start
    throughput = (total_batch / total_time) if total_time > 0 else 0.0

    return {
        "total_time": total_time,
        "max_worker_time": max_worker_time,
        "throughput": throughput,
        "valid_count": total_valid,
        "worker_times": ";".join(f"{r['worker_time_seconds']:.6f}" for r in responses),
        "rpc_latencies": ";".join(f"{r['rpc_latency_seconds']:.6f}" for r in responses)
    }

def main():
    check_governor()
    asyncio.run(check_health(12))

    batch = 20000
    threads = 1
    repeats = 10
    seed = 42

    p_list = [4, 8, 12]
    tasks = []
    for p in p_list:
        for rep in range(repeats):
            tasks.append({
                "p": p,
                "rep": rep
            })

    rng = random.Random(seed)
    rng.shuffle(tasks)

    out_csv = RESULTS_DIR / "results_e4b_grpc_pcores.csv"
    fields = [
        "experiment", "model", "ranks", "threads", "p_eff", "batch", "rep",
        "time_seconds", "throughput", "valid_count", "gen_s", "verify_s", "reduce_s",
        "binding", "cpuset", "schedule", "oversubscribed", "worker_times", "rpc_latencies"
    ]
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

    log_file = LOGS_DIR / "e4b.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Running E4b gRPC P-cores ({len(tasks)} tasks: p in [4, 8, 12]) -> {out_csv} ---")
    t0 = time.perf_counter()
    for idx, t in enumerate(tasks, 1):
        p = t["p"]
        rep = t["rep"]
        addrs = ALL_WORKERS[:p]
        res = asyncio.run(run_grpc_batch(addrs, batch, threads, base_seed=1000 + rep * 31))

        rec = {
            "experiment": "E4b",
            "model": "grpc_openmp_pcores",
            "ranks": p,
            "threads": threads,
            "p_eff": p,
            "batch": batch,
            "rep": rep,
            "time_seconds": res["total_time"],
            "throughput": res["throughput"],
            "valid_count": res["valid_count"],
            "gen_s": 0.0,
            "verify_s": res["max_worker_time"],
            "reduce_s": 0.0,
            "binding": "container",
            "cpuset": "0-11",
            "schedule": "static",
            "oversubscribed": 0,
            "worker_times": res["worker_times"],
            "rpc_latencies": res["rpc_latencies"]
        }

        with open(out_csv, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writerow(rec)

        with open(log_file, "a") as lf:
            lf.write(f"[E4b p={p} rep={rep}] wall={res['total_time']:.4f}s verify={res['max_worker_time']:.4f}s tp={res['throughput']:.1f}\n")

        print(f"[{idx:2d}/{len(tasks):2d}] E4b p={p:2d} rep={rep} -> wall={res['total_time']:.4f}s verify={res['max_worker_time']:.4f}s tp={res['throughput']:7.1f} sig/s")

    print(f"\n[+] E4b campaign completed in {time.perf_counter() - t0:.2f}s")

if __name__ == "__main__":
    main()
