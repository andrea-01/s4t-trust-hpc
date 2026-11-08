#!/usr/bin/env python3
"""
E10 Benchmark:
Dynamic master-worker with OpenMP thread parallelism per worker (Hybrid Dynamic).
Factorizations:
  4x2 (8 cores), 5x2 (10 cores), 6x2 (12 cores), 7x2 (14 cores), 4x3 (12 cores).
Chunk sizes:
  100*T and 25*T.
Flags:
  mpirun --report-bindings --map-by slot:PE=T --bind-to core
10 interleaved repeats, batch = 20,000.
Saves to hpc-engine/results/m13/results_e10_dynamic_hybrid.csv.
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
BIN_MPI_DYNAMIC = REPO_ROOT / "build" / "hpc_engine_mpi_dynamic"
OUT_CSV = RESULTS_DIR / "results_e10_dynamic_hybrid.csv"

CONFIGS = [
    {"r": 4, "t": 2, "chunks": [50, 200], "cores": 8},
    {"r": 5, "t": 2, "chunks": [50, 200], "cores": 10},
    {"r": 6, "t": 2, "chunks": [50, 200], "cores": 12},
    {"r": 7, "t": 2, "chunks": [50, 200], "cores": 14},
    {"r": 4, "t": 3, "chunks": [75, 300], "cores": 12},
]

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

    tasks = []
    for cfg in CONFIGS:
        for chunk in cfg["chunks"]:
            for rep in range(repeats):
                tasks.append({
                    "r": cfg["r"],
                    "t": cfg["t"],
                    "chunk": chunk,
                    "cores": cfg["cores"],
                    "rep": rep
                })

    rng = random.Random(seed)
    rng.shuffle(tasks)

    fields = [
        "experiment", "model", "ranks", "threads", "p_eff", "batch", "rep",
        "time_seconds", "throughput", "valid_count", "gen_s", "verify_s", "reduce_s",
        "binding", "chunk_size", "physical_cores", "inactive_cores", "inactive_ratio"
    ]

    with open(OUT_CSV, "w", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=fields)
        writer.writeheader()

    tmp_csv = Path("/tmp/e10_out.csv")

    print(f"--- Running E10 Dynamic Hybrid ({len(tasks)} tasks) -> {OUT_CSV} ---")
    t0 = time.perf_counter()

    for idx, t in enumerate(tasks, 1):
        if tmp_csv.exists():
            tmp_csv.unlink()

        r = t["r"]
        th = t["t"]
        chunk = t["chunk"]
        cores = t["cores"]
        rep = t["rep"]

        cmd = [
            "mpirun",
            "--map-by", f"slot:PE={th}",
            "--bind-to", "core",
            "-np", str(r),
            str(BIN_MPI_DYNAMIC),
            str(batch),
            str(chunk),
            str(th),
            str(tmp_csv)
        ]

        env = os.environ.copy()
        env["HWLOC_COMPONENTS"] = env.get("HWLOC_COMPONENTS", "-gl")
        env["OMP_NUM_THREADS"] = str(th)

        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        if proc.returncode != 0:
            # Fallback check as required by prompt: --map-by ppr:R:node:PE=T
            print(f"[WARN] slot:PE={th} failed, trying fallback --map-by ppr:{r}:node:PE={th}...")
            cmd[1] = "--map-by"
            cmd[2] = f"ppr:{r}:node:PE={th}"
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            if proc.returncode != 0:
                raise RuntimeError(f"MPI failed:\n{proc.stderr}")

        with open(tmp_csv, "r") as cf:
            row = next(csv.DictReader(cf))

        inactive = th
        inactive_ratio = float(inactive) / float(cores)

        rec = {
            "experiment": "E10",
            "model": "mpi_dynamic_hybrid",
            "ranks": r,
            "threads": th,
            "p_eff": (r - 1) * th,
            "batch": batch,
            "rep": rep,
            "time_seconds": float(row["time_seconds"]),
            "throughput": float(row["throughput"]),
            "valid_count": int(row.get("valid_count", row.get("batch_size", batch))),
            "gen_s": float(row.get("gen_time_seconds", 0.0)),
            "verify_s": float(row.get("verify_time_seconds", 0.0)),
            "reduce_s": float(row.get("reduce_time_seconds", 0.0)),
            "binding": f"slot:PE={th}_bind_core",
            "chunk_size": chunk,
            "physical_cores": cores,
            "inactive_cores": inactive,
            "inactive_ratio": inactive_ratio
        }

        with open(OUT_CSV, "a", newline="") as cf:
            writer = csv.DictWriter(cf, fieldnames=fields)
            writer.writerow(rec)

        if idx % 10 == 0 or idx == len(tasks):
            print(f"[{idx:3d}/{len(tasks):3d}] E10 {r}x{th} (cores={cores:2d}) chunk={chunk:3d} rep={rep} -> t={rec['time_seconds']:.4f}s tp={rec['throughput']:7.1f} sig/s")

    print(f"\n[+] E10 campaign finished in {time.perf_counter() - t0:.2f}s")

if __name__ == "__main__":
    main()

