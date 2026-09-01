#!/usr/bin/env python3
"""
Compute Formal HPC Metrics for Task Parallelism (gRPC + OpenMP)
Stage 11.3 - Speedup, Efficiency, Amdahl's Law, Scalability L
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Any

def compute_metrics(csv_path: str):
    p = Path(csv_path)
    if not p.exists():
        print(f"[!] Error: CSV file {csv_path} does not exist.")
        sys.exit(1)
        
    records = []
    with open(p, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            records.append({
                "batch_size": int(r["batch_size"]),
                "nodes": int(r["nodes"]),
                "threads": int(r["threads_per_node"]),
                "peff": int(r["effective_parallelism"]),
                "is_oversubscribed": r["is_oversubscribed"].lower() == "true",
                "best_time": float(r["best_time_seconds"]),
                "avg_time": float(r["avg_time_seconds"]),
                "best_throughput": float(r["best_throughput"]),
                "avg_throughput": float(r["avg_throughput"])
            })
            
    # Group by batch_size
    by_batch = {}
    for r in records:
        by_batch.setdefault(r["batch_size"], []).append(r)
        
    batch_sizes = sorted(by_batch.keys())
    print("="*100)
    print("HPC METRICS EVALUATION: TASK PARALLELISM (gRPC + OpenMP)")
    print("="*100)
    
    efficiency_by_batch_peff = {}
    
    for b_size in batch_sizes:
        batch_recs = by_batch[b_size]
        
        # Baseline T1: 1 node, 1 thread
        t1_rec = next((r for r in batch_recs if r["nodes"] == 1 and r["threads"] == 1), None)
        if not t1_rec:
            print(f"[!] Error: Baseline (1 node, 1 thread) not found for batch_size={b_size}")
            continue
            
        t1 = t1_rec["best_time"]
        
        # 1. Task Parallelism (Node-level): 2 nodes x 1 thread
        t2_nodes_rec = next((r for r in batch_recs if r["nodes"] == 2 and r["threads"] == 1), None)
        fs_nodes = None
        if t2_nodes_rec:
            s2_nodes = t1 / t2_nodes_rec["best_time"]
            fs_nodes = max(0.0, (2.0 / s2_nodes) - 1.0)
            
        # 2. Data Parallelism (Thread-level OpenMP): 1 node x 2 threads
        t2_omp_rec = next((r for r in batch_recs if r["nodes"] == 1 and r["threads"] == 2), None)
        fs_omp = None
        if t2_omp_rec:
            s2_omp = t1 / t2_omp_rec["best_time"]
            fs_omp = max(0.0, (2.0 / s2_omp) - 1.0)
            
        print(f"\n--- Batch Size = {b_size} Firme ECDSA ---")
        print(f"Baseline T1 (1 node, 1 thread): {t1*1000:.2f} ms ({t1_rec['best_throughput']:.1f} sig/s)")
        if fs_nodes is not None:
            print(f" -> Amdahl Serial Fraction Task-Parallel (2 nodi x 1 th): fs_task = {fs_nodes:.4f} ({fs_nodes*100:.2f}% seriale)")
        if fs_omp is not None:
            print(f" -> Amdahl Serial Fraction OpenMP (1 nodo x 2 th):       fs_omp  = {fs_omp:.4f} ({fs_omp*100:.2f}% seriale)")
            
        print("\n" + "-"*120)
        print(f"{'Nodes':>5} | {'Th/Node':>7} | {'P_eff':>5} | {'Time (ms)':>10} | {'Throughput':>12} | {'Speedup':>8} | {'Eff(P_eff)':>10} | {'Eff(Nodes)':>10} | {'Amdahl Task':>11} | {'Amdahl OMP':>11} | {'Status'}")
        print("-"*120)
        
        for r in batch_recs:
            t = r["best_time"]
            speedup = t1 / t
            eff_peff = speedup / r["peff"]
            eff_nodes = speedup / r["nodes"]
            
            amdahl_task_pred = (1.0 / (fs_nodes + (1.0 - fs_nodes) / r["nodes"])) if (fs_nodes is not None and r["nodes"] > 0) else 0.0
            amdahl_omp_pred = (1.0 / (fs_omp + (1.0 - fs_omp) / r["threads"])) if (fs_omp is not None and r["threads"] > 0) else 0.0
            status_tag = "OVERSUBSCRIBED" if r["is_oversubscribed"] else "CLEAN"
            
            efficiency_by_batch_peff.setdefault(b_size, {})[r["peff"]] = eff_peff
            
            print(f"{r['nodes']:>5} | {r['threads']:>7} | {r['peff']:>5} | {t*1000:>10.2f} | {r['best_throughput']:>10.1f} s/s | {speedup:>8.2f}x | {eff_peff:>9.2f} | {eff_nodes:>9.2f} | {amdahl_task_pred:>10.2f}x | {amdahl_omp_pred:>10.2f}x | {status_tag}")
            
    # Scalability Metric L between smallest and largest batch size
    if len(batch_sizes) >= 2:
        b_small = batch_sizes[0]
        b_large = batch_sizes[-1]
        print("\n" + "="*80)
        print(f"SCALABILITY METRIC L = E(P, N={b_large}) / E(P, N={b_small})")
        print("="*80)
        print(f"{'P_eff':>5} | {'Eff (Small)':>12} | {'Eff (Large)':>12} | {'Scalability L':>15} | {'Interpretation'}")
        print("-"*80)
        
        common_peffs = sorted(set(efficiency_by_batch_peff[b_small].keys()) & set(efficiency_by_batch_peff[b_large].keys()))
        for peff in common_peffs:
            e_s = efficiency_by_batch_peff[b_small][peff]
            e_l = efficiency_by_batch_peff[b_large][peff]
            l_val = e_l / e_s if e_s > 0 else 0.0
            
            if peff == 1:
                interp = "Baseline (1.0)"
            elif l_val >= 1.05:
                interp = "Scalabilità positiva (ammortizza overhead)"
            elif l_val >= 0.95:
                interp = "Scalabilità ideale / invariante"
            else:
                interp = "Degrado relativo"
                
            print(f"{peff:>5} | {e_s:>12.2f} | {e_l:>12.2f} | {l_val:>15.2f} | {interp}")

def main():
    parser = argparse.ArgumentParser(description="Compute formal HPC metrics from benchmark CSV")
    parser.add_argument("--csv", default=str(Path(__file__).resolve().parent.parent / "results_grpc_task_parallel.csv"),
                        help="Path to results CSV")
    args = parser.parse_args()
    compute_metrics(args.csv)

if __name__ == "__main__":
    main()
