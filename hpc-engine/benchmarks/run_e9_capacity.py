#!/usr/bin/env python3
"""
V3: Machine Capacity Benchmark (E9).
Measures aggregated throughput of q independent sequential processes pinned with taskset -c <cpu>.
Zero inter-process communication or synchronization.

Configurations:
  (a) 1 process on CPU 0 (P-core)
  (b) 1 process on CPU 12 (E-core)
  (c) 2 processes on CPU 0, 1 (SMT on same P-core)
  (d) 6 processes on CPU 0, 2, 4, 6, 8, 10 (one thread per P-core)
  (e) 12 processes on CPU 0-11 (all P-cores with SMT)
  (f) 14 processes on CPU 0, 2, 4, 6, 8, 10, 12-19 (all 14 physical cores)
  (g) 20 processes on CPU 0-19 (full machine)

Batch = 20,000 per process. 10 repeats interleaved.
"""

import os
import sys
import time
import random
import subprocess
import csv
from pathlib import Path
from typing import List, Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "hpc-engine" / "results" / "m13"
BIN_PATH = REPO_ROOT / "build" / "hpc_engine_bench"

CONFIGS = [
    {
        "config_id": "a_pcore_single",
        "description": "1 P-core (CPU 0)",
        "cpus": [0],
        "q": 1
    },
    {
        "config_id": "b_ecore_single",
        "description": "1 E-core (CPU 12)",
        "cpus": [12],
        "q": 1
    },
    {
        "config_id": "c_smt_pair",
        "description": "2 threads on same P-core (CPU 0, 1)",
        "cpus": [0, 1],
        "q": 2
    },
    {
        "config_id": "d_pcores_6",
        "description": "6 P-cores no SMT (CPU 0,2,4,6,8,10)",
        "cpus": [0, 2, 4, 6, 8, 10],
        "q": 6
    },
    {
        "config_id": "e_pcores_12",
        "description": "12 P-cores SMT (CPU 0-11)",
        "cpus": list(range(12)),
        "q": 12
    },
    {
        "config_id": "f_physical_14",
        "description": "14 physical cores (6 P-cores + 8 E-cores)",
        "cpus": [0, 2, 4, 6, 8, 10] + list(range(12, 20)),
        "q": 14
    },
    {
        "config_id": "g_all_20",
        "description": "20 all threads (CPU 0-19)",
        "cpus": list(range(20)),
        "q": 20
    }
]

def run_single_benchmark(cpus: List[int], batch: int, tmp_dir: Path) -> Dict[str, Any]:
    procs = []
    tmp_files = []
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "1"

    for i, cpu_id in enumerate(cpus):
        out_f = tmp_dir / f"proc_{os.getpid()}_{i}_{cpu_id}.csv"
        tmp_files.append(out_f)
        cmd = ["taskset", "-c", str(cpu_id), str(BIN_PATH), str(batch), str(batch), "1", str(out_f), "for"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        procs.append(p)

    for p in procs:
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            raise RuntimeError(f"Process failed:\n{stderr}")

    times = []
    valid_total = 0

    for out_f in tmp_files:
        with open(out_f, "r") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            times.append(float(row["time_seconds"]))
            valid_total += int(row["valid_count"])
        out_f.unlink()

    q = len(cpus)
    expected_valid = q * batch
    if valid_total != expected_valid:
        raise RuntimeError(f"Valid count mismatch: {valid_total} != {expected_valid}")

    t_max = max(times)
    t_min = min(times)
    t_avg = sum(times) / q
    throughput = (expected_valid / t_max) if t_max > 0 else 0.0

    return {
        "t_max": t_max,
        "t_min": t_min,
        "t_avg": t_avg,
        "throughput_agg": throughput,
        "valid_total": valid_total,
        "raw_times": times
    }

def main():
    batch = 20000
    repeats = 10
    seed = 42
    out_csv = RESULTS_DIR / "results_e9_capacity.csv"
    tmp_dir = Path("/tmp/e9_capacity")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print("==========================================================")
    print(" V3: Machine Capacity Benchmark (E9)")
    print(f" Target: {out_csv}")
    print(f" Batch: {batch} per process | Repeats: {repeats}")
    print("==========================================================\n")

    tasks = []
    for cfg in CONFIGS:
        for rep in range(repeats):
            tasks.append({
                "config_id": cfg["config_id"],
                "description": cfg["description"],
                "cpus": cfg["cpus"],
                "q": cfg["q"],
                "rep": rep
            })

    rng = random.Random(seed)
    rng.shuffle(tasks)

    fields = ["config_id", "q", "description", "cpus", "rep", "t_max", "t_min", "t_avg", "throughput_agg", "valid_total"]
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

    t_start = time.perf_counter()
    for idx, t in enumerate(tasks, 1):
        res = run_single_benchmark(t["cpus"], batch, tmp_dir)
        row = {
            "config_id": t["config_id"],
            "q": t["q"],
            "description": t["description"],
            "cpus": "_".join(map(str, t["cpus"])),
            "rep": t["rep"],
            "t_max": res["t_max"],
            "t_min": res["t_min"],
            "t_avg": res["t_avg"],
            "throughput_agg": res["throughput_agg"],
            "valid_total": res["valid_total"]
        }
        with open(out_csv, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writerow(row)

        print(f"[{idx:2d}/{len(tasks):2d}] {t['config_id']:16s} (q={t['q']:2d}, rep={t['rep']}) ... OK: t_max={res['t_max']:.4f}s, Throughput={res['throughput_agg']:8.1f} sig/s")

    total_dur = time.perf_counter() - t_start
    print(f"\n[+] E9 capacity benchmark completed in {total_dur:.2f}s ({total_dur/60:.2f} min).")

if __name__ == "__main__":
    main()

