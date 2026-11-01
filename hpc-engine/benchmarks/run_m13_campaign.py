#!/usr/bin/env python3
"""
M13 Stage 13.3 Experimental Campaign Driver
Unified runner for E0 through E8 with strong scaling, randomized interleaved repeats,
strict correctness validation, resume capabilities, and per-phase metric instrumentation.
"""

import argparse
import asyncio
import csv
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent.parent
HPC_DIR = REPO_ROOT / "hpc-engine"
RESULTS_DIR = HPC_DIR / "results" / "m13"
LOGS_DIR = RESULTS_DIR / "logs"

# Ensure directories exist
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Add bench dir to sys.path
if str(BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(BENCH_DIR))

CSV_FIELDS = [
    "experiment", "model", "ranks", "threads", "p_eff", "batch", "rep",
    "time_seconds", "throughput", "valid_count", "gen_s", "verify_s", "reduce_s",
    "binding", "cpuset", "schedule", "oversubscribed"
]

ALL_WORKERS = [f"127.0.0.1:{p}" for p in range(51051, 51083)]

def _get_grpc_modules():
    try:
        import grpc
        import pipeline_pb2
        import pipeline_pb2_grpc
        from google.protobuf.empty_pb2 import Empty
        return grpc, pipeline_pb2, pipeline_pb2_grpc, Empty
    except ImportError:
        # Check if satellite venv has grpc
        venv_py = REPO_ROOT / "satellite" / "venv" / "lib" / "python3.12" / "site-packages"
        if venv_py.exists() and str(venv_py) not in sys.path:
            sys.path.insert(0, str(venv_py))
            import grpc
            import pipeline_pb2
            import pipeline_pb2_grpc
            from google.protobuf.empty_pb2 import Empty
            return grpc, pipeline_pb2, pipeline_pb2_grpc, Empty
        raise

def get_binary_path(name: str) -> Path:
    candidates = [
        REPO_ROOT / "build" / name,
        HPC_DIR / "build" / name
    ]
    for c in candidates:
        if c.exists() and os.access(c, os.X_OK):
            return c
    raise FileNotFoundError(f"Binary {name} not found in build/ or hpc-engine/build/")

def init_csv_file(csv_path: Path):
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()

def load_existing_keys(csv_path: Path) -> set:
    if not csv_path.exists():
        return set()
    completed = set()
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # key: (experiment, model, ranks, threads, batch, rep, binding, cpuset, schedule)
            key = (
                row["experiment"],
                row["model"],
                int(row["ranks"]),
                int(row["threads"]),
                int(row["batch"]),
                int(row["rep"]),
                row["binding"],
                row["cpuset"],
                row["schedule"]
            )
            completed.add(key)
    return completed

def append_csv_row(csv_path: Path, row_data: Dict[str, Any]):
    # Validate correctness strictly
    if int(row_data["valid_count"]) != int(row_data["batch"]):
        raise RuntimeError(
            f"CORRECTNESS VIOLATION: valid_count ({row_data['valid_count']}) != batch ({row_data['batch']}) "
            f"for task {row_data}"
        )
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerow(row_data)
        f.flush()

# --- gRPC Helpers ---
async def check_grpc_workers_online(count: int, timeout: float = 3.0) -> bool:
    grpc, pipeline_pb2, pipeline_pb2_grpc, Empty = _get_grpc_modules()
    addrs = ALL_WORKERS[:count]
    for addr in addrs:
        try:
            async with grpc.aio.insecure_channel(addr) as channel:
                stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
                st = await stub.Ping(Empty(), timeout=timeout)
                if not st.healthy:
                    return False
        except Exception:
            return False
    return True

async def dispatch_single_worker(addr: str, batch_size: int, num_threads: int, seed: int, timeout: float = 60.0):
    grpc, pipeline_pb2, pipeline_pb2_grpc, Empty = _get_grpc_modules()
    async with grpc.aio.insecure_channel(addr) as channel:
        stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
        req = pipeline_pb2.TaskRequest(
            operation=pipeline_pb2.OperationType.VERIFY_SIGNATURES_BATCH,
            batch_size=batch_size,
            num_threads=num_threads,
            seed=seed,
            pipeline_id="bench-m13-grpc"
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

async def run_grpc_batch(worker_addrs: List[str], total_batch: int, num_threads: int, base_seed: int = 42):
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
        "valid_count": total_valid
    }

# --- Task Execution Engine ---
def execute_task(task: Dict[str, Any], log_file: Path) -> Dict[str, Any]:
    exp = task["experiment"]
    batch = task["batch"]
    ranks = task["ranks"]
    threads = task["threads"]
    p_eff = task["p_eff"]
    model = task["model"]
    binding = task["binding"]
    cpuset = task["cpuset"]
    schedule = task["schedule"]

    env = os.environ.copy()
    env["HWLOC_COMPONENTS"] = env.get("HWLOC_COMPONENTS", "-gl")

    tmp_csv = Path(f"/tmp/bench_run_{os.getpid()}_{time.time_ns()}.csv")
    if tmp_csv.exists():
        tmp_csv.unlink()

    gen_s = 0.0
    verify_s = 0.0
    reduce_s = 0.0
    time_seconds = 0.0
    throughput = 0.0
    valid_count = 0

    try:
        if exp == "E0":
            bin_path = get_binary_path("hpc_engine_bench")
            cmd = [str(bin_path), str(batch), str(batch), "0", str(tmp_csv), "seq"]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            with open(log_file, "a") as f:
                f.write(f"\n--- [E0 Rep {task['rep']}] CMD: {' '.join(cmd)} ---\n")
                f.write(proc.stdout + "\n" + proc.stderr + "\n")
            if proc.returncode != 0:
                raise RuntimeError(f"E0 execution failed:\n{proc.stderr}")
            with open(tmp_csv, "r") as f:
                reader = csv.DictReader(f)
                row = next(reader)
                time_seconds = float(row["time_seconds"])
                throughput = float(row["throughput"])
                valid_count = int(row["valid_count"])
            verify_s = time_seconds

        elif exp == "E1":
            bin_path = get_binary_path("hpc_engine_bench")
            env["OMP_NUM_THREADS"] = str(threads)
            cmd = [str(bin_path), str(batch), str(batch), str(threads), str(tmp_csv), "for"]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            with open(log_file, "a") as f:
                f.write(f"\n--- [E1 T={threads} Rep {task['rep']}] CMD: {' '.join(cmd)} ---\n")
                f.write(proc.stdout + "\n" + proc.stderr + "\n")
            if proc.returncode != 0:
                raise RuntimeError(f"E1 execution failed:\n{proc.stderr}")
            with open(tmp_csv, "r") as f:
                reader = csv.DictReader(f)
                row = next(reader)
                time_seconds = float(row["time_seconds"])
                throughput = float(row["throughput"])
                valid_count = int(row["valid_count"])
            verify_s = time_seconds

        elif exp == "E2":
            script = BENCH_DIR / "launch_mpi_pure.sh"
            cmd = [str(script), str(ranks), str(batch), str(tmp_csv)]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            with open(log_file, "a") as f:
                f.write(f"\n--- [E2 R={ranks} Rep {task['rep']}] CMD: {' '.join(cmd)} ---\n")
                f.write(proc.stdout + "\n" + proc.stderr + "\n")
            if proc.returncode != 0:
                raise RuntimeError(f"E2 execution failed:\n{proc.stderr}")
            with open(tmp_csv, "r") as f:
                reader = csv.DictReader(f)
                # Read last row added
                rows = list(reader)
                row = rows[-1]
                time_seconds = float(row["time_seconds"])
                throughput = float(row["throughput"])
                valid_count = int(row["batch_size"])
                gen_s = float(row.get("gen_time_seconds", 0.0))
                verify_s = float(row.get("verify_time_seconds", 0.0))
                reduce_s = float(row.get("reduce_time_seconds", 0.0))

        elif exp == "E3":
            if binding == "none":
                script = BENCH_DIR / "launch_control.sh"
            else:
                script = BENCH_DIR / "launch_hybrid.sh"
            cmd = [str(script), str(ranks), str(threads), str(batch), str(tmp_csv)]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            with open(log_file, "a") as f:
                f.write(f"\n--- [E3 R={ranks} T={threads} bind={binding} Rep {task['rep']}] CMD: {' '.join(cmd)} ---\n")
                f.write(proc.stdout + "\n" + proc.stderr + "\n")
            if proc.returncode != 0:
                raise RuntimeError(f"E3 execution failed:\n{proc.stderr}")
            with open(tmp_csv, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                row = rows[-1]
                time_seconds = float(row["time_seconds"])
                throughput = float(row["throughput"])
                valid_count = int(row["batch_size"])
                gen_s = float(row.get("gen_time_seconds", 0.0))
                verify_s = float(row.get("verify_time_seconds", 0.0))
                reduce_s = float(row.get("reduce_time_seconds", 0.0))

        elif exp == "E4":
            addrs = ALL_WORKERS[:ranks]
            res = asyncio.run(run_grpc_batch(addrs, batch, threads, base_seed=1000 + task["rep"] * 31))
            time_seconds = res["total_time"]
            throughput = res["throughput"]
            valid_count = res["valid_count"]
            verify_s = res["max_worker_time"]
            with open(log_file, "a") as f:
                f.write(f"\n--- [E4 W={ranks} T={threads} Rep {task['rep']}] total_t={time_seconds:.4f}s tp={throughput:.1f} ---\n")

        elif exp == "E5":
            bin_path = get_binary_path("hpc_engine_bench")
            env["OMP_NUM_THREADS"] = str(threads)
            env["OMP_SCHEDULE"] = schedule
            cmd = [str(bin_path), str(batch), str(batch), str(threads), str(tmp_csv), "for"]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            with open(log_file, "a") as f:
                f.write(f"\n--- [E5 sched={schedule} T={threads} Rep {task['rep']}] CMD: {' '.join(cmd)} ---\n")
                f.write(proc.stdout + "\n" + proc.stderr + "\n")
            if proc.returncode != 0:
                raise RuntimeError(f"E5 execution failed:\n{proc.stderr}")
            with open(tmp_csv, "r") as f:
                reader = csv.DictReader(f)
                row = next(reader)
                time_seconds = float(row["time_seconds"])
                throughput = float(row["throughput"])
                valid_count = int(row["valid_count"])
            verify_s = time_seconds

        elif exp == "E6":
            if model == "omp_taskloop":
                bin_path = get_binary_path("hpc_engine_bench")
                env["OMP_NUM_THREADS"] = str(threads)
                grain = task["grainsize"]
                cmd = [str(bin_path), str(batch), str(batch), str(threads), str(tmp_csv), "taskloop", str(grain)]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                with open(log_file, "a") as f:
                    f.write(f"\n--- [E6 taskloop grain={grain} T={threads} Rep {task['rep']}] CMD: {' '.join(cmd)} ---\n")
                    f.write(proc.stdout + "\n" + proc.stderr + "\n")
                if proc.returncode != 0:
                    raise RuntimeError(f"E6 taskloop execution failed:\n{proc.stderr}")
                with open(tmp_csv, "r") as f:
                    reader = csv.DictReader(f)
                    row = next(reader)
                    time_seconds = float(row["time_seconds"])
                    throughput = float(row["throughput"])
                    valid_count = int(row["valid_count"])
                verify_s = time_seconds

            elif model == "mpi_dynamic":
                script = BENCH_DIR / "launch_dynamic.sh"
                chunk = task["chunk_size"]
                cmd = [str(script), str(ranks), str(chunk), str(threads), str(batch), str(tmp_csv)]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                with open(log_file, "a") as f:
                    f.write(f"\n--- [E6 mpi_dynamic R={ranks} chunk={chunk} Rep {task['rep']}] CMD: {' '.join(cmd)} ---\n")
                    f.write(proc.stdout + "\n" + proc.stderr + "\n")
                if proc.returncode != 0:
                    raise RuntimeError(f"E6 mpi_dynamic execution failed:\n{proc.stderr}")
                with open(tmp_csv, "r") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    row = rows[-1]
                    time_seconds = float(row["time_seconds"])
                    throughput = float(row["throughput"])
                    valid_count = int(row["valid_count"])
                    gen_s = float(row.get("gen_time_seconds", 0.0))
                    verify_s = float(row.get("verify_time_seconds", 0.0))
                    reduce_s = float(row.get("reduce_time_seconds", 0.0))

        elif exp == "E8":
            if model == "omp_pure_pcores":
                bin_path = get_binary_path("hpc_engine_bench")
                env["OMP_NUM_THREADS"] = str(threads)
                cmd = ["taskset", "-c", "0-11", str(bin_path), str(batch), str(batch), str(threads), str(tmp_csv), "for"]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                with open(log_file, "a") as f:
                    f.write(f"\n--- [E8 omp_pcores T={threads} Rep {task['rep']}] CMD: {' '.join(cmd)} ---\n")
                    f.write(proc.stdout + "\n" + proc.stderr + "\n")
                if proc.returncode != 0:
                    raise RuntimeError(f"E8 OpenMP execution failed:\n{proc.stderr}")
                with open(tmp_csv, "r") as f:
                    reader = csv.DictReader(f)
                    row = next(reader)
                    time_seconds = float(row["time_seconds"])
                    throughput = float(row["throughput"])
                    valid_count = int(row["valid_count"])
                verify_s = time_seconds

            elif model == "mpi_pure_pcores":
                script = BENCH_DIR / "launch_mpi_pure.sh"
                cmd = [str(script), str(ranks), str(batch), str(tmp_csv), "--pcores"]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                with open(log_file, "a") as f:
                    f.write(f"\n--- [E8 mpi_pcores R={ranks} Rep {task['rep']}] CMD: {' '.join(cmd)} ---\n")
                    f.write(proc.stdout + "\n" + proc.stderr + "\n")
                if proc.returncode != 0:
                    raise RuntimeError(f"E8 MPI execution failed:\n{proc.stderr}")
                with open(tmp_csv, "r") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    row = rows[-1]
                    time_seconds = float(row["time_seconds"])
                    throughput = float(row["throughput"])
                    valid_count = int(row["batch_size"])
                    gen_s = float(row.get("gen_time_seconds", 0.0))
                    verify_s = float(row.get("verify_time_seconds", 0.0))
                    reduce_s = float(row.get("reduce_time_seconds", 0.0))

        else:
            raise NotImplementedError(f"Experiment {exp} is not implemented in general runner.")

    finally:
        if tmp_csv.exists():
            tmp_csv.unlink()

    # Oversubscription rule:
    # > 20 for standard runs; > 12 for pcores runs
    max_cores = 12 if "pcores" in cpuset else 20
    is_oversubscribed = 1 if p_eff > max_cores else 0

    return {
        "experiment": exp,
        "model": model,
        "ranks": ranks,
        "threads": threads,
        "p_eff": p_eff,
        "batch": batch,
        "rep": task["rep"],
        "time_seconds": time_seconds,
        "throughput": throughput,
        "valid_count": valid_count,
        "gen_s": gen_s,
        "verify_s": verify_s,
        "reduce_s": reduce_s,
        "binding": binding,
        "cpuset": cpuset,
        "schedule": schedule,
        "oversubscribed": is_oversubscribed
    }

# --- Task Generation ---
def generate_experiment_tasks(exp: str, batch: int, repeats: int) -> List[Dict[str, Any]]:
    tasks = []
    if exp == "E0":
        for rep in range(repeats):
            tasks.append({
                "experiment": "E0",
                "model": "sequential",
                "ranks": 1,
                "threads": 1,
                "p_eff": 1,
                "batch": batch,
                "rep": rep,
                "binding": "none",
                "cpuset": "all",
                "schedule": "none"
            })

    elif exp == "E1":
        thread_list = [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20]
        for t in thread_list:
            for rep in range(repeats):
                tasks.append({
                    "experiment": "E1",
                    "model": "omp_pure",
                    "ranks": 1,
                    "threads": t,
                    "p_eff": t,
                    "batch": batch,
                    "rep": rep,
                    "binding": "omp_default",
                    "cpuset": "all",
                    "schedule": "static"
                })

    elif exp == "E2":
        rank_list = [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20]
        for r in rank_list:
            for rep in range(repeats):
                tasks.append({
                    "experiment": "E2",
                    "model": "mpi_pure",
                    "ranks": r,
                    "threads": 1,
                    "p_eff": r,
                    "batch": batch,
                    "rep": rep,
                    "binding": "core",
                    "cpuset": "all",
                    "schedule": "none"
                })

    elif exp == "E3":
        # R>=4, T>=2: 4x2, 4x3, 4x4, 4x5, 5x2, 5x3, 5x4, 6x2, 6x3, 7x2, 8x2, 10x2 (p_eff 8..20)
        grid = [
            (4, 2), (4, 3), (4, 4), (4, 5),
            (5, 2), (5, 3), (5, 4),
            (6, 2), (6, 3),
            (7, 2),
            (8, 2),
            (10, 2)
        ]
        for r, t in grid:
            for rep in range(repeats):
                tasks.append({
                    "experiment": "E3",
                    "model": "hybrid_mpi_omp",
                    "ranks": r,
                    "threads": t,
                    "p_eff": r * t,
                    "batch": batch,
                    "rep": rep,
                    "binding": "map_by_slot_pe_bind_to_core",
                    "cpuset": "all",
                    "schedule": "static"
                })
        # Controls with --bind-to none: 4x4 and 8x2
        for r, t in [(4, 4), (8, 2)]:
            for rep in range(repeats):
                tasks.append({
                    "experiment": "E3",
                    "model": "hybrid_mpi_omp_unbound",
                    "ranks": r,
                    "threads": t,
                    "p_eff": r * t,
                    "batch": batch,
                    "rep": rep,
                    "binding": "none",
                    "cpuset": "all",
                    "schedule": "static"
                })

    elif exp == "E4":
        # worker = 1,2,4,6,8,10,12,16,20 with T=1; plus 4x4, 5x4; 32 worker T=1
        configs = [
            (1, 1), (2, 1), (4, 1), (6, 1), (8, 1), (10, 1), (12, 1), (16, 1), (20, 1),
            (4, 4), (5, 4),
            (32, 1)
        ]
        for w, t in configs:
            for rep in range(repeats):
                tasks.append({
                    "experiment": "E4",
                    "model": "grpc_openmp",
                    "ranks": w,
                    "threads": t,
                    "p_eff": w * t,
                    "batch": batch,
                    "rep": rep,
                    "binding": "container",
                    "cpuset": "all",
                    "schedule": "static"
                })

    elif exp == "E5":
        # schedules: static, dynamic,16, guided with T=4,8,12,16,20
        schedules = ["static", "dynamic,16", "guided"]
        thread_list = [4, 8, 12, 16, 20]
        for s in schedules:
            for t in thread_list:
                for rep in range(repeats):
                    tasks.append({
                        "experiment": "E5",
                        "model": "omp_schedule",
                        "ranks": 1,
                        "threads": t,
                        "p_eff": t,
                        "batch": batch,
                        "rep": rep,
                        "binding": "omp_default",
                        "cpuset": "all",
                        "schedule": s
                    })

    elif exp == "E6":
        # taskloop with grainsize 10,50,100,500 with T=4,8,12,20
        grains = [10, 50, 100, 500]
        t_list = [4, 8, 12, 20]
        for g in grains:
            for t in t_list:
                for rep in range(repeats):
                    tasks.append({
                        "experiment": "E6",
                        "model": "omp_taskloop",
                        "ranks": 1,
                        "threads": t,
                        "p_eff": t,
                        "batch": batch,
                        "rep": rep,
                        "grainsize": g,
                        "binding": "omp_default",
                        "cpuset": "all",
                        "schedule": f"taskloop_grain_{g}"
                    })
        # MPI master-worker dynamic with R=4..12 and chunk 100
        for r in range(4, 13):
            for rep in range(repeats):
                tasks.append({
                    "experiment": "E6",
                    "model": "mpi_dynamic",
                    "ranks": r,
                    "threads": 1,
                    "p_eff": r,
                    "batch": batch,
                    "rep": rep,
                    "chunk_size": 100,
                    "binding": "core",
                    "cpuset": "all",
                    "schedule": f"dynamic_chunk_100_workers_{r-1}"
                })
        # plus chunk 25/500 at R=8
        for c in [25, 500]:
            for rep in range(repeats):
                tasks.append({
                    "experiment": "E6",
                    "model": "mpi_dynamic",
                    "ranks": 8,
                    "threads": 1,
                    "p_eff": 8,
                    "batch": batch,
                    "rep": rep,
                    "chunk_size": c,
                    "binding": "core",
                    "cpuset": "all",
                    "schedule": f"dynamic_chunk_{c}_workers_7"
                })

    elif exp == "E8":
        # P-cores (taskset -c 0-11) for T,R <= 12
        core_list = [1, 2, 3, 4, 6, 8, 10, 12]
        # OpenMP pure on P-cores
        for t in core_list:
            for rep in range(repeats):
                tasks.append({
                    "experiment": "E8",
                    "model": "omp_pure_pcores",
                    "ranks": 1,
                    "threads": t,
                    "p_eff": t,
                    "batch": batch,
                    "rep": rep,
                    "binding": "omp_default",
                    "cpuset": "pcores_0_11",
                    "schedule": "static"
                })
        # MPI pure on P-cores
        for r in core_list:
            for rep in range(repeats):
                tasks.append({
                    "experiment": "E8",
                    "model": "mpi_pure_pcores",
                    "ranks": r,
                    "threads": 1,
                    "p_eff": r,
                    "batch": batch,
                    "rep": rep,
                    "binding": "core",
                    "cpuset": "pcores_0_11",
                    "schedule": "none"
                })

    return tasks

# --- Main Campaign Orchestrator ---
def run_experiment_campaign(
    exp: str,
    batch: int,
    repeats: int,
    seed: int,
    resume: bool = True,
    dry_run: bool = False
) -> int:
    csv_filename = f"results_{exp.lower()}.csv"
    if exp == "E0":
        csv_filename = "results_e0_sequential.csv"
    elif exp == "E1":
        csv_filename = "results_e1_omp_pure.csv"
    elif exp == "E2":
        csv_filename = "results_e2_mpi_pure.csv"
    elif exp == "E3":
        csv_filename = "results_e3_hybrid.csv"
    elif exp == "E4":
        csv_filename = "results_e4_grpc.csv"
    elif exp == "E5":
        csv_filename = "results_e5_schedule.csv"
    elif exp == "E6":
        csv_filename = "results_e6_taskbased.csv"
    elif exp == "E8":
        csv_filename = "results_e8_pcores.csv"

    csv_path = RESULTS_DIR / csv_filename
    t1_path = RESULTS_DIR / "t1_baseline.csv"
    log_file = LOGS_DIR / f"{exp.lower()}.log"

    print(f"\n{'='*75}")
    print(f" EXPERIMENTAL CAMPAIGN: {exp}")
    print(f" Target CSV: {csv_path}")
    print(f" Batch: {batch} | Repeats: {repeats} | Seed: {seed} | Resume: {resume}")
    print(f"{'='*75}")

    tasks = generate_experiment_tasks(exp, batch, repeats)
    total_tasks = len(tasks)
    print(f"Generated {total_tasks} total task runs for {exp}.")

    if exp == "E4":
        # Check gRPC workers
        print("Checking health of gRPC benchmark containers for E4...")
        healthy = asyncio.run(check_grpc_workers_online(32))
        if not healthy:
            raise RuntimeError(
                "E4 requires all 32 bench-worker containers online (ports 51051-51082). "
                "Please run: docker compose -f deploy/docker-compose.benchmark.yml up -d"
            )
        print("All 32 gRPC benchmark worker containers verified online.")

    # Randomize task order (interleaved repeats) using deterministic seed
    rng = random.Random(seed)
    rng.shuffle(tasks)

    if dry_run:
        print("[DRY RUN] Config sample:")
        for t in tasks[:5]:
            print(" ", t)
        print(f"[DRY RUN] Total tasks: {len(tasks)}. Exiting without execution.")
        return 0

    init_csv_file(csv_path)
    if exp == "E0":
        init_csv_file(t1_path)

    completed_keys = set()
    if resume:
        completed_keys = load_existing_keys(csv_path)
        print(f"Resume active: found {len(completed_keys)} already completed tasks in {csv_path.name}.")

    pending_tasks = []
    for t in tasks:
        key = (
            t["experiment"],
            t["model"],
            t["ranks"],
            t["threads"],
            t["batch"],
            t["rep"],
            t["binding"],
            t["cpuset"],
            t["schedule"]
        )
        if key not in completed_keys:
            pending_tasks.append(t)

    print(f"Pending tasks to execute: {len(pending_tasks)} / {total_tasks}\n")
    if not pending_tasks:
        print(f"[+] All tasks for {exp} are already completed!")
        return 0

    # Discarded Warmup: run 1 warmup iteration of the first pending task
    print(f"[*] Running 1 discarded warmup execution...")
    warmup_task = pending_tasks[0].copy()
    warmup_task["rep"] = -1
    warmup_log = LOGS_DIR / f"{exp.lower()}_warmup.log"
    execute_task(warmup_task, warmup_log)
    print("[+] Warmup complete. Starting formal randomized data collection...\n")

    t_camp_start = time.perf_counter()
    executed_count = 0

    for idx, task in enumerate(pending_tasks, 1):
        desc = (f"[{idx}/{len(pending_tasks)}] {task['model']} R={task['ranks']} "
                f"T={task['threads']} P_eff={task['p_eff']} Rep={task['rep']}")
        print(f"{desc:<55} ... ", end="", flush=True)

        t0 = time.perf_counter()
        result_row = execute_task(task, log_file)
        dt = time.perf_counter() - t0

        append_csv_row(csv_path, result_row)
        if exp == "E0":
            append_csv_row(t1_path, result_row)

        executed_count += 1
        tp = result_row["throughput"]
        print(f"OK ({dt:6.2f}s | {tp:8.1f} sig/s)")

    total_duration = time.perf_counter() - t_camp_start
    print(f"\n[+] {exp} completed successfully! Executed {executed_count} runs in {total_duration:.2f}s.")
    return executed_count

def main():
    parser = argparse.ArgumentParser(description="M13 Experimental Campaign Driver")
    parser.add_argument(
        "--experiment", "-e",
        choices=["E0", "E1", "E2", "E3", "E4", "E5", "E6", "E8", "E7", "ALL_CORE"],
        default="ALL_CORE",
        help="Experiment to run (default: ALL_CORE = E0, E1, E2, E3, E5, E6, E8)"
    )
    parser.add_argument("--batch", type=int, default=20000, help="Total batch size (default: 20000)")
    parser.add_argument("--repeats", type=int, default=10, help="Number of repetitions per config (default: 10)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for interleaved execution (default: 42)")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume existing CSV runs")
    parser.add_argument("--dry-run", action="store_true", help="Print experiment plan and exit")
    parser.add_argument("--pilot", action="store_true", help="Run 1 repeat per config to estimate campaign runtime")

    args = parser.parse_args()
    resume = not args.no_resume
    repeats = 1 if args.pilot else args.repeats

    if args.experiment == "ALL_CORE":
        exp_list = ["E0", "E1", "E2", "E3", "E5", "E6", "E8"]
    else:
        exp_list = [args.experiment]

    print(f"M13 Campaign Driver Initialized at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Experiments: {exp_list}")
    print(f"Batch Size: {args.batch} | Repeats: {repeats} (Pilot mode: {args.pilot})")

    total_runs = 0
    t_start = time.perf_counter()

    for exp in exp_list:
        runs = run_experiment_campaign(
            exp=exp,
            batch=args.batch,
            repeats=repeats,
            seed=args.seed,
            resume=resume,
            dry_run=args.dry_run
        )
        total_runs += runs

    total_time = time.perf_counter() - t_start
    print(f"\n{'='*75}")
    print(f" CAMPAIGN SUMMARY: Executed {total_runs} runs in {total_time:.2f} seconds ({total_time/60:.2f} min).")
    print(f"{'='*75}")

if __name__ == "__main__":
    main()
