#!/usr/bin/env python3
"""
E4c: Discriminative benchmark SMT vs E-cores on gRPC containers.
7 Configurations:
1. p2_pcores: {0, 2} (two distinct P-cores)
2. p2_smt: {0, 1} (SMT on same P-core)
3. p6_pcores: {0, 2, 4, 6, 8, 10} (one per P-core)
4. p8_ecores: {0, 2, 4, 6, 8, 10, 12, 14} (6 P + 2 E)
5. p8_smt: {0, 2, 4, 6, 8, 10, 1, 3} (6 P + 2 SMT)
6. p12_ecores: {0, 2, 4, 6, 8, 10, 12, 13, 14, 15, 16, 17} (6 P + 6 E)
7. p14_ecores: {0, 2, 4, 6, 8, 10, 12, 13, 14, 15, 16, 17, 18, 19} (6 P + 8 E)

For each config, creates a dedicated docker-compose override file, applies it,
measures 10 repeats of batch=20,000, records T_wall, verify_s, estimated gen, ping, residual.
Saves to hpc-engine/results/m13/results_e4c_smt_ecore_discrim.csv.
"""

import os
import sys
import time
import random
import asyncio
import csv
import subprocess
from pathlib import Path
from typing import List, Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEPLOY_DIR = REPO_ROOT / "deploy"
RESULTS_DIR = REPO_ROOT / "hpc-engine" / "results" / "m13"
BENCH_COMPOSE = DEPLOY_DIR / "docker-compose.benchmark.yml"

sys.path.insert(0, str(REPO_ROOT / "hpc-engine" / "benchmarks"))
import grpc
import pipeline_pb2
import pipeline_pb2_grpc
from google.protobuf.empty_pb2 import Empty

CONFIGS = [
    {
        "name": "p2_pcores",
        "p": 2,
        "cpus": [0, 2],
        "desc": "2 P-cores distinti {0, 2}"
    },
    {
        "name": "p2_smt",
        "p": 2,
        "cpus": [0, 1],
        "desc": "SMT stesso P-core {0, 1}"
    },
    {
        "name": "p6_pcores",
        "p": 6,
        "cpus": [0, 2, 4, 6, 8, 10],
        "desc": "6 P-cores {0, 2, 4, 6, 8, 10}"
    },
    {
        "name": "p8_ecores",
        "p": 8,
        "cpus": [0, 2, 4, 6, 8, 10, 12, 14],
        "desc": "6 P-cores + 2 E-cores {0, 2, 4, 6, 8, 10, 12, 14}"
    },
    {
        "name": "p8_smt",
        "p": 8,
        "cpus": [0, 2, 4, 6, 8, 10, 1, 3],
        "desc": "6 P-cores + 2 SMT {0, 2, 4, 6, 8, 10, 1, 3}"
    },
    {
        "name": "p12_ecores",
        "p": 12,
        "cpus": [0, 2, 4, 6, 8, 10, 12, 13, 14, 15, 16, 17],
        "desc": "6 P-cores + 6 E-cores {0, 2, 4, 6, 8, 10, 12..17}"
    },
    {
        "name": "p14_ecores",
        "p": 14,
        "cpus": [0, 2, 4, 6, 8, 10, 12, 13, 14, 15, 16, 17, 18, 19],
        "desc": "6 P-cores + 8 E-cores {0, 2, 4, 6, 8, 10, 12..19}"
    }
]

def check_governor():
    gov_files = list(Path("/sys/devices/system/cpu").glob("cpu*/cpufreq/scaling_governor"))
    for gf in gov_files:
        gov = gf.read_text().strip()
        if gov != "performance":
            raise RuntimeError(f"CPU governor is '{gov}' on {gf}, must be 'performance'!")
    print(f"[OK] All {len(gov_files)} CPU governors set to 'performance'.")

def apply_compose_config(cfg: Dict[str, Any]):
    override_file = DEPLOY_DIR / f"docker-compose.override.e4c_{cfg['name']}.yml"
    lines = ["services:\n"]
    for i, cpu in enumerate(cfg["cpus"], 1):
        lines.append(f"  bench-worker-{i}:\n")
        lines.append(f'    cpuset: "{cpu}"\n')
    
    with open(override_file, "w") as f:
        f.writelines(lines)
    
    print(f"\n[*] Applying config '{cfg['name']}': {cfg['desc']} -> {override_file.name}")
    services = [f"bench-worker-{i}" for i in range(1, cfg["p"] + 1)]
    cmd = [
        "docker", "compose",
        "-f", str(BENCH_COMPOSE),
        "-f", str(override_file),
        "up", "-d"
    ] + services
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Docker compose failed:\n{proc.stderr}")

async def measure_ping(addrs: List[str]) -> float:
    pings = []
    for addr in addrs:
        async with grpc.aio.insecure_channel(addr) as channel:
            stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
            t0 = time.perf_counter()
            res = await stub.Ping(Empty(), timeout=5.0)
            t1 = time.perf_counter()
            if not res.healthy:
                raise RuntimeError(f"Node {addr} not healthy")
            pings.append(t1 - t0)
    return float(sum(pings) / len(pings))

async def dispatch_worker(addr: str, chunk_size: int, seed: int, timeout: float = 60.0):
    async with grpc.aio.insecure_channel(addr) as channel:
        stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
        req = pipeline_pb2.TaskRequest(
            operation=pipeline_pb2.OperationType.VERIFY_SIGNATURES_BATCH,
            batch_size=chunk_size,
            num_threads=1,
            seed=seed,
            pipeline_id="bench-m13-e4c"
        )
        t0 = time.perf_counter()
        res = await stub.ExecuteTask(req, timeout=timeout)
        t1 = time.perf_counter()
        return {
            "node_id": res.node_id,
            "valid_count": res.valid_count,
            "worker_time_seconds": res.time_seconds,
            "worker_throughput": res.throughput,
            "rpc_latency": t1 - t0
        }

async def run_batch(addrs: List[str], total_batch: int, rep: int):
    p = len(addrs)
    base_chunk = total_batch // p
    remainder = total_batch % p
    chunks = [base_chunk + (1 if i < remainder else 0) for i in range(p)]

    tasks = [
        dispatch_worker(addr, c, 1000 + rep * 50 + i)
        for i, (addr, c) in enumerate(zip(addrs, chunks))
    ]
    t0 = time.perf_counter()
    responses = await asyncio.gather(*tasks)
    t1 = time.perf_counter()

    tot_valid = sum(r["valid_count"] for r in responses)
    if tot_valid != total_batch:
        raise RuntimeError(f"Validity mismatch: {tot_valid} vs {total_batch}")

    max_verify = max(r["worker_time_seconds"] for r in responses)
    wall_s = t1 - t0
    return {
        "wall_s": wall_s,
        "verify_s": max_verify,
        "throughput": (total_batch / wall_s) if wall_s > 0 else 0.0,
        "worker_times": ";".join(f"{r['worker_time_seconds']:.6f}" for r in responses)
    }

def main():
    check_governor()
    batch = 20000
    repeats = 10
    out_csv = RESULTS_DIR / "results_e4c_smt_ecore_discrim.csv"
    fields = [
        "config_name", "p", "cpus", "batch", "rep",
        "wall_s", "verify_s", "gen_est_s", "ping_s", "residual_s",
        "throughput", "worker_times"
    ]

    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

    print(f"--- Starting E4c Campaign ({len(CONFIGS)} configs x {repeats} reps) -> {out_csv} ---")

    for cfg in CONFIGS:
        apply_compose_config(cfg)
        time.sleep(1.0) # Grace period for gRPC listener ready

        addrs = [f"localhost:{51051 + i}" for i in range(cfg["p"])]

        # Measure baseline ping
        ping_s = asyncio.run(measure_ping(addrs))

        # Determine slowest core generation cost:
        # P-core: ~38.5 us, E-core: ~75 us, SMT: ~61.5 us
        # Slowest core in config:
        has_ecore = any(c >= 12 for c in cfg["cpus"])
        has_smt = any(c in [1, 3, 5, 7, 9, 11] for c in cfg["cpus"])
        chunk_max = (batch + cfg["p"] - 1) // cfg["p"]

        if has_ecore:
            cost_us = 75.0
        elif has_smt:
            cost_us = 61.5
        else:
            cost_us = 38.5
        gen_est_s = (chunk_max * cost_us) / 1e6

        for rep in range(repeats):
            res = asyncio.run(run_batch(addrs, batch, rep))
            residual = res["wall_s"] - res["verify_s"] - ping_s

            rec = {
                "config_name": cfg["name"],
                "p": cfg["p"],
                "cpus": ",".join(str(c) for c in cfg["cpus"]),
                "batch": batch,
                "rep": rep,
                "wall_s": res["wall_s"],
                "verify_s": res["verify_s"],
                "gen_est_s": gen_est_s,
                "ping_s": ping_s,
                "residual_s": residual,
                "throughput": res["throughput"],
                "worker_times": res["worker_times"]
            }

            with open(out_csv, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writerow(rec)

            print(f"[{cfg['name']:<10}] rep={rep:2d} -> wall={res['wall_s']:.4f}s verify={res['verify_s']:.4f}s gen_est={gen_est_s:.4f}s ping={ping_s*1000:.1f}ms resid={residual*1000:.1f}ms tp={res['throughput']:7.1f}")

    print(f"\n[+] E4c benchmark successfully completed! Results saved to {out_csv}")

if __name__ == "__main__":
    main()

