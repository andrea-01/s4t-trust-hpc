#!/usr/bin/env python3
"""
Add missing odd ranks (R = 9, 11, 13) to E2b with --map-by core --bind-to core.
10 interleaved repeats, batch = 20000.
"""

import os
import sys
import time
import random
import subprocess
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "hpc-engine" / "results" / "m13"
BIN_MPI = REPO_ROOT / "build" / "hpc_engine_mpi"
CSV_PATH = RESULTS_DIR / "results_e2b_mpi_map_core.csv"

def check_governor():
    gov_files = list(Path("/sys/devices/system/cpu").glob("cpu*/cpufreq/scaling_governor"))
    for gf in gov_files:
        gov = gf.read_text().strip()
        if gov != "performance":
            raise RuntimeError(f"CPU governor is '{gov}' on {gf}, must be 'performance'!")
    print(f"[OK] All {len(gov_files)} CPU governors set to 'performance'.")

def main():
    check_governor()
    batch = 20000
    repeats = 10
    seed = 42

    ranks_to_add = [9, 11, 13]
    tasks = []
    for r in ranks_to_add:
        for rep in range(repeats):
            tasks.append({
                "r": r,
                "rep": rep
            })

    rng = random.Random(seed)
    rng.shuffle(tasks)

    tmp_csv = Path("/tmp/e2b_add_out.csv")
    fields = [
        "experiment", "model", "ranks", "threads", "p_eff", "batch", "rep",
        "time_seconds", "throughput", "valid_count", "gen_s", "verify_s", "reduce_s",
        "binding", "cpuset", "schedule", "oversubscribed"
    ]

    print(f"--- Running E2b missing ranks {ranks_to_add} ({len(tasks)} tasks) ---")
    t0 = time.perf_counter()
    for idx, t in enumerate(tasks, 1):
        if tmp_csv.exists():
            tmp_csv.unlink()

        cmd = [
            "mpirun",
            "--report-bindings",
            "--map-by", "core",
            "--bind-to", "core",
            "-np", str(t["r"]),
            str(BIN_MPI),
            str(batch),
            "1",
            str(tmp_csv)
        ]

        env = os.environ.copy()
        env["HWLOC_COMPONENTS"] = env.get("HWLOC_COMPONENTS", "-gl")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        if proc.returncode != 0:
            raise RuntimeError(f"MPI failed:\n{proc.stderr}")

        with open(tmp_csv, "r") as cf:
            row = next(csv.DictReader(cf))

        rec = {
            "experiment": "E2b",
            "model": "mpi_pure_map_core",
            "ranks": t["r"],
            "threads": 1,
            "p_eff": t["r"],
            "batch": batch,
            "rep": t["rep"],
            "time_seconds": float(row["time_seconds"]),
            "throughput": float(row["throughput"]),
            "valid_count": int(row.get("valid_count", row.get("batch_size", batch))),
            "gen_s": float(row.get("gen_time_seconds", 0.0)),
            "verify_s": float(row.get("verify_time_seconds", 0.0)),
            "reduce_s": float(row.get("reduce_time_seconds", 0.0)),
            "binding": "map_core_bind_core",
            "cpuset": "all",
            "schedule": "none",
            "oversubscribed": 0
        }

        with open(CSV_PATH, "a", newline="") as cf:
            writer = csv.DictWriter(cf, fieldnames=fields)
            writer.writerow(rec)

        if idx % 10 == 0 or idx == len(tasks):
            print(f"[{idx:2d}/{len(tasks):2d}] E2b R={t['r']:2d} rep={t['rep']} -> t={rec['time_seconds']:.4f}s tp={rec['throughput']:7.1f} sig/s")

    print(f"[+] Added {len(tasks)} runs to {CSV_PATH} in {time.perf_counter() - t0:.2f}s")

if __name__ == "__main__":
    main()
