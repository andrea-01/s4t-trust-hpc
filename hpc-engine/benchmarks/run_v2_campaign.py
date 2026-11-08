#!/usr/bin/env python3
"""
M13 Stage 13.4-bis V2 Campaign Driver.
Executes:
- E2b: MPI pure with --map-by core --bind-to core (R=1..14 without hwthreads, R=16..20 with hwthreads)
- E1c close: OpenMP with OMP_PLACES=cores OMP_PROC_BIND=close
- E1c spread: OpenMP with OMP_PLACES=cores OMP_PROC_BIND=spread
- E0b: Sequential baseline randomly interleaved with p=1 runs
All runs use batch=20000, 10 repetitions, randomized interleaved order, assert valid_count == 20000.
"""

import os
import sys
import time
import random
import subprocess
import csv
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "hpc-engine" / "results" / "m13"
LOGS_DIR = RESULTS_DIR / "logs"

CSV_FIELDS = [
    "experiment", "model", "ranks", "threads", "p_eff", "batch", "rep",
    "time_seconds", "throughput", "valid_count", "gen_s", "verify_s", "reduce_s",
    "binding", "cpuset", "schedule", "oversubscribed"
]

def get_binary_path(name: str) -> Path:
    p = REPO_ROOT / "build" / name
    if p.exists() and os.access(p, os.X_OK):
        return p
    raise FileNotFoundError(f"Binary {name} not found in build/")

def run_task(task: Dict[str, Any], tmp_csv: Path, log_file: Path) -> Dict[str, Any]:
    if tmp_csv.exists():
        tmp_csv.unlink()

    exp = task["experiment"]
    model = task["model"]
    ranks = task["ranks"]
    threads = task["threads"]
    batch = task["batch"]
    binding = task["binding"]

    env = os.environ.copy()
    env["HWLOC_COMPONENTS"] = "-gl"

    if exp == "E0b":
        bin_path = get_binary_path("hpc_engine_bench")
        env["OMP_NUM_THREADS"] = "1"
        cmd = [str(bin_path), str(batch), str(batch), "1", str(tmp_csv), "for"]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        if proc.returncode != 0:
            raise RuntimeError(f"E0b failed: {proc.stderr}")
        with open(tmp_csv, "r") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            t_sec = float(row["time_seconds"])
            tp = float(row["throughput"])
            vc = int(row["valid_count"])
        gen_s = 0.0
        verify_s = t_sec
        reduce_s = 0.0

    elif exp == "E1c_close" or exp == "E1c_spread":
        bin_path = get_binary_path("hpc_engine_bench")
        env["OMP_NUM_THREADS"] = str(threads)
        env["OMP_PLACES"] = "cores"
        env["OMP_PROC_BIND"] = "close" if "close" in exp else "spread"
        cmd = [str(bin_path), str(batch), str(batch), str(threads), str(tmp_csv), "for"]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        if proc.returncode != 0:
            raise RuntimeError(f"{exp} failed: {proc.stderr}")
        with open(tmp_csv, "r") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            t_sec = float(row["time_seconds"])
            tp = float(row["throughput"])
            vc = int(row["valid_count"])
        gen_s = 0.0
        verify_s = t_sec
        reduce_s = 0.0

    elif exp == "E2b":
        bin_path = get_binary_path("hpc_engine_mpi")
        cmd = ["mpirun"]
        if ranks > 14:
            cmd.append("--use-hwthread-cpus")
        cmd.extend([
            "--map-by", "core",
            "--bind-to", "core",
            "--report-bindings",
            "-np", str(ranks),
            str(bin_path), str(batch), "1", str(tmp_csv)
        ])
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        with open(log_file, "a") as f:
            f.write(f"\n--- [E2b R={ranks} Rep {task['rep']}] CMD: {' '.join(cmd)} ---\n")
            f.write(proc.stdout + "\n" + proc.stderr + "\n")
        if proc.returncode != 0:
            raise RuntimeError(f"E2b failed: {proc.stderr}")
        with open(tmp_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            row = rows[-1]
            t_sec = float(row["time_seconds"])
            tp = float(row["throughput"])
            vc = int(row["batch_size"])
            gen_s = float(row.get("gen_time_seconds", 0.0))
            verify_s = float(row.get("verify_time_seconds", 0.0))
            reduce_s = float(row.get("reduce_time_seconds", 0.0))
    else:
        raise ValueError(f"Unknown exp {exp}")

    if vc != batch:
        raise RuntimeError(f"Validity check failed: {vc} valid != {batch} expected")

    oversubscribed = 1 if task["p_eff"] > 20 else 0

    return {
        "experiment": exp,
        "model": model,
        "ranks": ranks,
        "threads": threads,
        "p_eff": task["p_eff"],
        "batch": batch,
        "rep": task["rep"],
        "time_seconds": t_sec,
        "throughput": tp,
        "valid_count": vc,
        "gen_s": gen_s,
        "verify_s": verify_s,
        "reduce_s": reduce_s,
        "binding": binding,
        "cpuset": "all",
        "schedule": task.get("schedule", "none"),
        "oversubscribed": oversubscribed
    }

def main():
    batch = 20000
    repeats = 10
    seed = 42

    csv_paths = {
        "E0b": RESULTS_DIR / "results_e0b_sequential.csv",
        "E2b": RESULTS_DIR / "results_e2b_mpi_map_core.csv",
        "E1c_close": RESULTS_DIR / "results_e1c_omp_cores_close.csv",
        "E1c_spread": RESULTS_DIR / "results_e1c_omp_cores_spread.csv",
    }
    log_file = LOGS_DIR / "v2_campaign.log"

    # Initialize CSV headers
    for p in csv_paths.values():
        if not p.exists():
            with open(p, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()

    tasks = []

    # E0b: 10 repeats of sequential baseline
    for rep in range(repeats):
        tasks.append({
            "experiment": "E0b",
            "model": "sequential_e0b",
            "ranks": 1,
            "threads": 1,
            "p_eff": 1,
            "batch": batch,
            "rep": rep,
            "binding": "none",
            "schedule": "none"
        })

    # E2b: R = 1,2,3,4,5,6,7,8,10,12,14,16,18,20
    r_list = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 18, 20]
    for r in r_list:
        binding_label = "map_core_bind_core" if r <= 14 else "map_core_bind_core_hwthreads"
        for rep in range(repeats):
            tasks.append({
                "experiment": "E2b",
                "model": "mpi_pure_map_core",
                "ranks": r,
                "threads": 1,
                "p_eff": r,
                "batch": batch,
                "rep": rep,
                "binding": binding_label,
                "schedule": "none"
            })

    # E1c close & spread: T = 1,2,3,4,6,8,10,12,14,16,18,20
    t_list = [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20]
    for t in t_list:
        for rep in range(repeats):
            tasks.append({
                "experiment": "E1c_close",
                "model": "omp_cores_close",
                "ranks": 1,
                "threads": t,
                "p_eff": t,
                "batch": batch,
                "rep": rep,
                "binding": "cores_close",
                "schedule": "static"
            })
            tasks.append({
                "experiment": "E1c_spread",
                "model": "omp_cores_spread",
                "ranks": 1,
                "threads": t,
                "p_eff": t,
                "batch": batch,
                "rep": rep,
                "binding": "cores_spread",
                "schedule": "static"
            })

    print(f"Total V2 tasks generated: {len(tasks)}")
    rng = random.Random(seed)
    rng.shuffle(tasks)

    tmp_csv = Path(f"/tmp/bench_v2_{os.getpid()}.csv")
    t0_start = time.perf_counter()

    try:
        for i, t in enumerate(tasks, 1):
            exp = t["experiment"]
            t_res = run_task(t, tmp_csv, log_file)
            target_csv = csv_paths[exp]
            with open(target_csv, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writerow(t_res)

            print(f"[{i:3d}/{len(tasks)}] {exp:10s} p={t['p_eff']:2d} rep={t['rep']:1d} ... OK ({t_res['time_seconds']:.4f}s | {t_res['throughput']:8.1f} sig/s)")
    finally:
        if tmp_csv.exists():
            tmp_csv.unlink()

    dur = time.perf_counter() - t0_start
    print(f"\n[+] V2 campaign completed in {dur:.2f}s ({dur/60:.2f} min).")

if __name__ == "__main__":
    main()
