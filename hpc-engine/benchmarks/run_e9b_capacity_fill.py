#!/usr/bin/env python3
"""
Capacity Benchmark:
1. E9-detailed: Re-run the 7 isolated configs of E9, recording every individual process time T_i.
2. E9b-fill: Run q = 1..20 along the actual fill order used by the experiments:
   - 6 P-cores primary threads: CPU 0, 2, 4, 6, 8, 10
   - 8 E-cores: CPU 12, 13, 14, 15, 16, 17, 18, 19
   - 6 P-cores secondary threads (SMT): CPU 1, 3, 5, 7, 9, 11
   Zero communication or synchronization between processes.
   Records individual process times T_i, C_static(q) and C_dyn(q).
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

FILL_CPUS = [
    0, 2, 4, 6, 8, 10,       # 6 P-cores (thread 0)
    12, 13, 14, 15, 16, 17, 18, 19, # 8 E-cores
    1, 3, 5, 7, 9, 11         # 6 P-cores (thread 1, SMT)
]

E9_CONFIGS = [
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

def check_governor():
    gov_files = list(Path("/sys/devices/system/cpu").glob("cpu*/cpufreq/scaling_governor"))
    if not gov_files:
        print("[WARN] Unable to check cpufreq scaling governors.")
        return
    for gf in gov_files:
        gov = gf.read_text().strip()
        if gov != "performance":
            raise RuntimeError(f"CPU governor is '{gov}' on {gf}, must be 'performance'!")
    print(f"[OK] All {len(gov_files)} CPU governors are set to 'performance'.")

def run_proc_batch(cpus: List[int], batch: int, tmp_dir: Path) -> Dict[str, Any]:
    procs = []
    tmp_files = []
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "1"

    for i, cpu_id in enumerate(cpus):
        out_f = tmp_dir / f"proc_{os.getpid()}_{time.time_ns()}_{i}_{cpu_id}.csv"
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
    throughput_static = (expected_valid / t_max) if t_max > 0 else 0.0
    throughput_dyn = sum((batch / t) for t in times) if all(t > 0 for t in times) else 0.0

    return {
        "t_max": t_max,
        "t_min": t_min,
        "t_avg": t_avg,
        "throughput_static": throughput_static,
        "throughput_dyn": throughput_dyn,
        "valid_total": valid_total,
        "proc_times": ";".join(f"{t:.6f}" for t in times)
    }

def run_e9_detailed(batch: int, repeats: int, seed: int, tmp_dir: Path):
    out_csv = RESULTS_DIR / "results_e9_capacity_detailed.csv"
    print(f"\n--- Running E9 Detailed (7 isolated configs, {repeats} reps) -> {out_csv} ---")
    tasks = []
    for cfg in E9_CONFIGS:
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

    fields = ["config_id", "q", "description", "rep", "cpus", "t_max", "t_min", "t_avg", "throughput_static", "throughput_dyn", "proc_times", "valid_total"]
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

    t_start = time.perf_counter()
    for idx, t in enumerate(tasks, 1):
        res = run_proc_batch(t["cpus"], batch, tmp_dir)
        row = {
            "config_id": t["config_id"],
            "q": t["q"],
            "description": t["description"],
            "rep": t["rep"],
            "cpus": "_".join(map(str, t["cpus"])),
            "t_max": res["t_max"],
            "t_min": res["t_min"],
            "t_avg": res["t_avg"],
            "throughput_static": res["throughput_static"],
            "throughput_dyn": res["throughput_dyn"],
            "proc_times": res["proc_times"],
            "valid_total": res["valid_total"]
        }
        with open(out_csv, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writerow(row)
        print(f"[{idx:2d}/{len(tasks):2d}] E9 {t['config_id']:16s} (q={t['q']:2d}, rep={t['rep']}) -> t_max={res['t_max']:.4f}s, tp_static={res['throughput_static']:8.1f}, tp_dyn={res['throughput_dyn']:8.1f}")
    print(f"[+] E9 detailed completed in {time.perf_counter() - t_start:.2f}s")

def run_e9b_fill(batch: int, repeats: int, seed: int, tmp_dir: Path):
    out_csv = RESULTS_DIR / "results_e9b_capacity_fill.csv"
    print(f"\n--- Running E9b Fill Order (q=1..20, {repeats} reps) -> {out_csv} ---")
    tasks = []
    for q in range(1, 21):
        cpus = FILL_CPUS[:q]
        for rep in range(repeats):
            tasks.append({
                "q": q,
                "cpus": cpus,
                "rep": rep
            })

    rng = random.Random(seed)
    rng.shuffle(tasks)

    fields = ["q", "rep", "cpus", "t_max", "t_min", "t_avg", "throughput_static", "throughput_dyn", "proc_times", "valid_total"]
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

    t_start = time.perf_counter()
    for idx, t in enumerate(tasks, 1):
        res = run_proc_batch(t["cpus"], batch, tmp_dir)
        row = {
            "q": t["q"],
            "rep": t["rep"],
            "cpus": "_".join(map(str, t["cpus"])),
            "t_max": res["t_max"],
            "t_min": res["t_min"],
            "t_avg": res["t_avg"],
            "throughput_static": res["throughput_static"],
            "throughput_dyn": res["throughput_dyn"],
            "proc_times": res["proc_times"],
            "valid_total": res["valid_total"]
        }
        with open(out_csv, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writerow(row)
        print(f"[{idx:3d}/{len(tasks):3d}] E9b q={t['q']:2d} (rep={t['rep']}) -> t_max={res['t_max']:.4f}s, tp_static={res['throughput_static']:8.1f}, tp_dyn={res['throughput_dyn']:8.1f}")
    print(f"[+] E9b fill completed in {time.perf_counter() - t_start:.2f}s")

def main():
    check_governor()
    batch = 20000
    repeats = 10
    seed = 42
    tmp_dir = Path("/tmp/capacity_bench")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print("==========================================================")
    print(" V3 Re-evaluation: Capacity Benchmarks (E9 detailed + E9b fill)")
    print(f" Batch per proc: {batch} | Repeats: {repeats} interleaved")
    print("==========================================================")

    run_e9_detailed(batch, repeats, seed, tmp_dir)
    run_e9b_fill(batch, repeats, seed, tmp_dir)

if __name__ == "__main__":
    main()

