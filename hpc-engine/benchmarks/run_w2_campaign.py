#!/usr/bin/env python3
"""
W2 Campaign:
1. E6b: Dynamic Master-Worker with --map-by core --bind-to core (no --use-hwthread-cpus)
   - R = 3, 4, 5, 6, 7, 8, 9, 10, 12, 14
   - chunk = 25, 100
   - T = 1
   - Extra variant for R = 4, 8, 9 with --mca mpi_yield_when_idle 1
   - Saves in results_e6b_dynamic_map_core.csv with column binding_real
2. E8b: Pure MPI on P-cores with taskset -c 0-11, --map-by core --bind-to core
   - R = 1..12
   - T = 1
   - Saves in results_e8b_mpi_pcores_map_core.csv
3. E3b: Hybrid with physical core binding: --map-by slot:PE=T --bind-to core
   - (R, T): (4,2), (5,2), (6,2), (7,2), (4,3)
   - Saves in results_e3b_hybrid_map_core.csv
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
LOGS_DIR = RESULTS_DIR / "logs"
BIN_MPI_DYNAMIC = REPO_ROOT / "build" / "hpc_engine_mpi_dynamic"
BIN_MPI = REPO_ROOT / "build" / "hpc_engine_mpi"

def check_governor():
    gov_files = list(Path("/sys/devices/system/cpu").glob("cpu*/cpufreq/scaling_governor"))
    for gf in gov_files:
        gov = gf.read_text().strip()
        if gov != "performance":
            raise RuntimeError(f"CPU governor is '{gov}' on {gf}, must be 'performance'!")
    print(f"[OK] All {len(gov_files)} CPU governors set to 'performance'.")

def describe_worker_binding(r: int) -> str:
    # Master is on Core 0 (P-core).
    # Workers are on Cores 1 .. (R - 1).
    # Cores 1..5 are 5 P-cores.
    # Cores 6..13 are 8 E-cores.
    num_workers = r - 1
    if num_workers <= 5:
        return f"{num_workers}_pcores"
    else:
        ecores = num_workers - 5
        return f"5_pcores_{ecores}_ecores"

def run_w2():
    check_governor()
    batch = 20000
    repeats = 10
    seed = 42

    tmp_csv = Path("/tmp/w2_bench_out.csv")
    log_file = LOGS_DIR / "w2_campaign.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    # -------------------------------------------------------------
    # 1. E6b Tasks
    # -------------------------------------------------------------
    e6b_csv = RESULTS_DIR / "results_e6b_dynamic_map_core.csv"
    e6b_fields = [
        "experiment", "model", "ranks", "threads", "p_eff", "chunk_size",
        "batch", "rep", "time_seconds", "throughput", "valid_count",
        "gen_s", "verify_s", "reduce_s", "binding", "binding_real", "yield_idle"
    ]
    if e6b_csv.exists() and sum(1 for _ in open(e6b_csv)) >= 261:
        print(f"[SKIP] E6b already completed ({e6b_csv} has 260 results).")
    else:
        with open(e6b_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=e6b_fields)
            writer.writeheader()

        e6b_tasks = []
        r_list_e6b = [3, 4, 5, 6, 7, 8, 9, 10, 12, 14]
        chunk_list = [25, 100]

        for r in r_list_e6b:
            for c in chunk_list:
                for rep in range(repeats):
                    e6b_tasks.append({
                        "r": r,
                        "c": c,
                        "rep": rep,
                        "yield_idle": 0
                    })

        # Additional variant with yield_idle=1 for R=4, 8, 9
        for r in [4, 8, 9]:
            for c in chunk_list:
                for rep in range(repeats):
                    e6b_tasks.append({
                        "r": r,
                        "c": c,
                        "rep": rep,
                        "yield_idle": 1
                    })

        rng = random.Random(seed)
        rng.shuffle(e6b_tasks)

        print(f"\n--- Running E6b Dynamic Master-Worker ({len(e6b_tasks)} tasks) -> {e6b_csv} ---")
        t0 = time.perf_counter()
        for idx, t in enumerate(e6b_tasks, 1):
            if tmp_csv.exists():
                tmp_csv.unlink()

            cmd = [
                "mpirun",
                "--report-bindings",
                "--map-by", "core",
                "--bind-to", "core"
            ]
            if t["yield_idle"] == 1:
                cmd.extend(["--mca", "mpi_yield_when_idle", "1"])
            cmd.extend([
                "-np", str(t["r"]),
                str(BIN_MPI_DYNAMIC),
                str(batch),
                str(t["c"]),
                "1",
                str(tmp_csv)
            ])

            env = os.environ.copy()
            env["HWLOC_COMPONENTS"] = env.get("HWLOC_COMPONENTS", "-gl")
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            with open(log_file, "a") as lf:
                lf.write(f"\n[E6b R={t['r']} chunk={t['c']} yield={t['yield_idle']} Rep {t['rep']}] CMD: {' '.join(cmd)}\n")
                lf.write(proc.stdout + "\n" + proc.stderr + "\n")
            if proc.returncode != 0:
                raise RuntimeError(f"E6b failed:\n{proc.stderr}")

            with open(tmp_csv, "r") as cf:
                row = next(csv.DictReader(cf))

            b_real = describe_worker_binding(t["r"])
            rec = {
                "experiment": "E6b",
                "model": "mpi_dynamic_map_core",
                "ranks": t["r"],
                "threads": 1,
                "p_eff": t["r"] - 1,
                "chunk_size": t["c"],
                "batch": batch,
                "rep": t["rep"],
                "time_seconds": float(row["time_seconds"]),
                "throughput": float(row["throughput"]),
                "valid_count": int(row.get("valid_count", row.get("batch_size", batch))),
                "gen_s": float(row.get("gen_time_seconds", 0.0)),
                "verify_s": float(row.get("verify_time_seconds", 0.0)),
                "reduce_s": float(row.get("reduce_time_seconds", 0.0)),
                "binding": "map_core_bind_core",
                "binding_real": b_real,
                "yield_idle": t["yield_idle"]
            }
            with open(e6b_csv, "a", newline="") as cf:
                writer = csv.DictWriter(cf, fieldnames=e6b_fields)
                writer.writerow(rec)

            if idx % 20 == 0 or idx == len(e6b_tasks):
                print(f"[{idx:3d}/{len(e6b_tasks):3d}] E6b R={t['r']:2d} c={t['c']:3d} yield={t['yield_idle']} -> t={rec['time_seconds']:.4f}s tp={rec['throughput']:7.1f} sig/s ({b_real})")
        print(f"[+] E6b completed in {time.perf_counter() - t0:.2f}s")

    # -------------------------------------------------------------
    # 2. E8b Tasks (Pure MPI on P-cores: taskset -c 0-11, --map-by core --bind-to core)
    # -------------------------------------------------------------
    e8b_csv = RESULTS_DIR / "results_e8b_mpi_pcores_map_core.csv"
    e8b_fields = [
        "experiment", "model", "ranks", "threads", "p_eff", "batch", "rep",
        "time_seconds", "throughput", "valid_count", "gen_s", "verify_s", "reduce_s", "binding"
    ]
    with open(e8b_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=e8b_fields)
        writer.writeheader()

    e8b_tasks = []
    for r in range(1, 13):
        for rep in range(repeats):
            e8b_tasks.append({
                "r": r,
                "rep": rep
            })

    rng.shuffle(e8b_tasks)
    print(f"\n--- Running E8b Pure MPI on P-cores ({len(e8b_tasks)} tasks) -> {e8b_csv} ---")
    t0 = time.perf_counter()
    for idx, t in enumerate(e8b_tasks, 1):
        if tmp_csv.exists():
            tmp_csv.unlink()

        cmd = [
            "taskset", "-c", "0-11",
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
        with open(log_file, "a") as lf:
            lf.write(f"\n[E8b R={t['r']} Rep {t['rep']}] CMD: {' '.join(cmd)}\n")
            lf.write(proc.stdout + "\n" + proc.stderr + "\n")
        if proc.returncode != 0:
            raise RuntimeError(f"E8b failed:\n{proc.stderr}")

        with open(tmp_csv, "r") as cf:
            row = next(csv.DictReader(cf))

        rec = {
            "experiment": "E8b",
            "model": "mpi_pcores_map_core",
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
            "binding": "taskset_0-11_map_core_bind_core"
        }
        with open(e8b_csv, "a", newline="") as cf:
            writer = csv.DictWriter(cf, fieldnames=e8b_fields)
            writer.writerow(rec)

        if idx % 20 == 0 or idx == len(e8b_tasks):
            print(f"[{idx:3d}/{len(e8b_tasks):3d}] E8b R={t['r']:2d} -> t={rec['time_seconds']:.4f}s tp={rec['throughput']:7.1f} sig/s")
    print(f"[+] E8b completed in {time.perf_counter() - t0:.2f}s")

    # -------------------------------------------------------------
    # 3. E3b Tasks (Hybrid MPI+OpenMP with physical core binding: --map-by slot:PE=T --bind-to core)
    # -------------------------------------------------------------
    e3b_csv = RESULTS_DIR / "results_e3b_hybrid_map_core.csv"
    e3b_fields = [
        "experiment", "model", "ranks", "threads", "p_eff", "physical_cores", "batch", "rep",
        "time_seconds", "throughput", "valid_count", "gen_s", "verify_s", "reduce_s", "binding"
    ]
    with open(e3b_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=e3b_fields)
        writer.writeheader()

    e3b_configs = [
        {"r": 4, "t": 2, "cores": 8},
        {"r": 5, "t": 2, "cores": 10},
        {"r": 6, "t": 2, "cores": 12},
        {"r": 7, "t": 2, "cores": 14},
        {"r": 4, "t": 3, "cores": 12},
    ]
    e3b_tasks = []
    for cfg in e3b_configs:
        for rep in range(repeats):
            e3b_tasks.append({
                "r": cfg["r"],
                "t": cfg["t"],
                "cores": cfg["cores"],
                "rep": rep
            })

    rng.shuffle(e3b_tasks)
    print(f"\n--- Running E3b Hybrid on Physical Cores ({len(e3b_tasks)} tasks) -> {e3b_csv} ---")
    t0 = time.perf_counter()
    for idx, t in enumerate(e3b_tasks, 1):
        if tmp_csv.exists():
            tmp_csv.unlink()

        cmd = [
            "mpirun",
            "--report-bindings",
            "--map-by", f"slot:PE={t['t']}",
            "--bind-to", "core",
            "-np", str(t["r"]),
            str(BIN_MPI),
            str(batch),
            str(t["t"]),
            str(tmp_csv)
        ]

        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = str(t["t"])
        env["HWLOC_COMPONENTS"] = env.get("HWLOC_COMPONENTS", "-gl")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        with open(log_file, "a") as lf:
            lf.write(f"\n[E3b R={t['r']} T={t['t']} cores={t['cores']} Rep {t['rep']}] CMD: {' '.join(cmd)}\n")
            lf.write(proc.stdout + "\n" + proc.stderr + "\n")
        if proc.returncode != 0:
            raise RuntimeError(f"E3b failed:\n{proc.stderr}")

        with open(tmp_csv, "r") as cf:
            row = next(csv.DictReader(cf))

        rec = {
            "experiment": "E3b",
            "model": "hybrid_map_core_pe",
            "ranks": t["r"],
            "threads": t["t"],
            "p_eff": t["r"] * t["t"],
            "physical_cores": t["cores"],
            "batch": batch,
            "rep": t["rep"],
            "time_seconds": float(row["time_seconds"]),
            "throughput": float(row["throughput"]),
            "valid_count": int(row.get("valid_count", row.get("batch_size", batch))),
            "gen_s": float(row.get("gen_time_seconds", 0.0)),
            "verify_s": float(row.get("verify_time_seconds", 0.0)),
            "reduce_s": float(row.get("reduce_time_seconds", 0.0)),
            "binding": f"slot:PE={t['t']}_bind_core"
        }
        with open(e3b_csv, "a", newline="") as cf:
            writer = csv.DictWriter(cf, fieldnames=e3b_fields)
            writer.writerow(rec)

        if idx % 10 == 0 or idx == len(e3b_tasks):
            print(f"[{idx:2d}/{len(e3b_tasks):2d}] E3b {t['r']}x{t['t']} (cores={t['cores']}) -> t={rec['time_seconds']:.4f}s tp={rec['throughput']:7.1f} sig/s")
    print(f"[+] E3b completed in {time.perf_counter() - t0:.2f}s")

if __name__ == "__main__":
    run_w2()

