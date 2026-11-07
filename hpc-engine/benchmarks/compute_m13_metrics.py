#!/usr/bin/env python3
"""
M13 Campaign Metrics Computation Engine (Stage 13.4).

Computes derived scaling and efficiency metrics from raw campaign CSVs:
- T1 baseline from E0 (median, IQR)
- Tp median, IQR, p25, p75
- Speedup S(p) = T1 / Tp with 95% bootstrap CI (10,000 resamples)
- Parallel efficiency E(p) = S(p) / p with 95% bootstrap CI
- Karp-Flatt metric e(p) with 95% bootstrap CI
- Amdahl fraction fs non-linear fit on p <= 4, predicting p > 4 with 95% bootstrap CI
- Dual speedups for E4 gRPC (S_wall and S_compute)
- Dual p definitions for E6 dynamic MPI (nominal p=R and worker pool p=R-1)
- Real binding mapping (binding_real) per U3
- Oversubscribed flag consistency

Outputs:
- results/m13/derived_speedup.csv
- results/m13/derived_karp_flatt.csv
- results/m13/derived_amdahl.csv
- results/m13/derived_schedule.csv
- results/m13/derived_taskbased.csv
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "hpc-engine" / "results" / "m13"

def load_csv(filename: str) -> pd.DataFrame:
    p = RESULTS_DIR / filename
    if not p.exists():
        raise FileNotFoundError(f"Missing required CSV: {p}")
    return pd.read_csv(p)

def map_binding_real(row: pd.Series) -> str:
    exp = row["experiment"]
    model = row["model"]
    binding = row.get("binding", "")
    threads = int(row.get("threads", 1))

    if exp == "E0":
        return "none"
    elif exp == "E1":
        return "omp_unbound"
    elif exp == "E1b":
        return "threads_close"
    elif exp == "E2":
        return "core"
    elif exp == "E3":
        if binding == "none" or "unbound" in model:
            return "unbound"
        elif threads in [2, 4]:
            return "hwthread_distinct_core"
        elif threads in [3, 5]:
            return "hwthread_smt_shared_core"
        else:
            return "hwthread"
    elif exp == "E4":
        return "docker_container"
    elif exp == "E5":
        return "omp_unbound"
    elif exp == "E6":
        if model == "mpi_dynamic":
            return "hwthread"
        return "omp_unbound"
    elif exp == "E8":
        if model == "omp_pure_pcores":
            return "omp_pcores_taskset"
        return "core_pcores"
    return binding

def bootstrap_ratio(
    t1_samples: np.ndarray,
    tp_samples: np.ndarray,
    n_resamples: int = 10000,
    seed: int = 42
) -> Tuple[float, float, float, np.ndarray]:
    rng = np.random.default_rng(seed)
    n1 = len(t1_samples)
    np_len = len(tp_samples)

    t1_boot = rng.choice(t1_samples, size=(n_resamples, n1), replace=True)
    tp_boot = rng.choice(tp_samples, size=(n_resamples, np_len), replace=True)

    t1_med = np.median(t1_boot, axis=1)
    tp_med = np.median(tp_boot, axis=1)
    s_boot = t1_med / tp_med

    s_med = float(np.median(t1_samples) / np.median(tp_samples))
    ci_low = float(np.percentile(s_boot, 2.5))
    ci_high = float(np.percentile(s_boot, 97.5))

    return s_med, ci_low, ci_high, s_boot

def amdahl_func(p: np.ndarray, fs: float) -> np.ndarray:
    return 1.0 / (fs + (1.0 - fs) / p)

def fit_amdahl_model(
    p_vals: np.ndarray,
    s_vals: np.ndarray,
    s_boot_dict: Dict[int, np.ndarray],
    eval_p_vals: np.ndarray,
    n_resamples: int = 10000
) -> Dict[str, Any]:
    # Fit fs on observed medians for p <= 4
    mask = p_vals <= 4
    fit_p = p_vals[mask]
    fit_s = s_vals[mask]

    if len(fit_p) < 2:
        return {}

    popt, _ = curve_fit(amdahl_func, fit_p, fit_s, p0=[0.05], bounds=(0.0, 1.0))
    fs_fitted = float(popt[0])

    # Bootstrap fs and predicted speedups
    fs_boot = np.zeros(n_resamples)
    for b in range(n_resamples):
        b_s = np.array([s_boot_dict[int(p)][b] for p in fit_p])
        try:
            b_popt, _ = curve_fit(amdahl_func, fit_p, b_s, p0=[fs_fitted], bounds=(0.0, 1.0))
            fs_boot[b] = b_popt[0]
        except Exception:
            fs_boot[b] = fs_fitted

    fs_ci_low = float(np.percentile(fs_boot, 2.5))
    fs_ci_high = float(np.percentile(fs_boot, 97.5))

    # Evaluate predictions for all eval_p_vals
    preds = {}
    for p in eval_p_vals:
        s_pred_boot = amdahl_func(p, fs_boot)
        preds[p] = {
            "pred": float(amdahl_func(p, fs_fitted)),
            "ci_low": float(np.percentile(s_pred_boot, 2.5)),
            "ci_high": float(np.percentile(s_pred_boot, 97.5)),
        }

    return {
        "fs_fitted": fs_fitted,
        "fs_ci_low": fs_ci_low,
        "fs_ci_high": fs_ci_high,
        "predictions": preds
    }

def compute_all_metrics(n_bootstrap: int = 10000, seed: int = 42) -> None:
    print(f"Loading raw CSVs from {RESULTS_DIR}...")
    df_e0 = load_csv("results_e0_sequential.csv")
    df_e1 = load_csv("results_e1_omp_pure.csv")
    df_e1b = load_csv("results_e1b_omp_bound.csv")
    df_e2 = load_csv("results_e2_mpi_pure.csv")
    df_e3 = load_csv("results_e3_hybrid.csv")
    df_e4 = load_csv("results_e4_grpc.csv")
    df_e5 = load_csv("results_e5_schedule.csv")
    df_e6 = load_csv("results_e6_taskbased.csv")
    df_e8 = load_csv("results_e8_pcores.csv")

    # Baseline T1 from E0
    t1_samples = df_e0["time_seconds"].values
    t1_median = float(np.median(t1_samples))
    t1_p25 = float(np.percentile(t1_samples, 25))
    t1_p75 = float(np.percentile(t1_samples, 75))
    t1_iqr = t1_p75 - t1_p25
    print(f"T1 Baseline: median={t1_median:.6f}s (IQR={t1_iqr:.6f}s, p25={t1_p25:.6f}s, p75={t1_p75:.6f}s)")

    # 1. Compute Derived Speedup & Efficiency
    speedup_rows = []
    karp_flatt_rows = []
    model_boot_dict: Dict[str, Dict[int, np.ndarray]] = {}
    model_p_s: Dict[str, Tuple[List[int], List[float]]] = {}

    scaling_dfs = [
        ("E0", df_e0),
        ("E1", df_e1),
        ("E1b", df_e1b),
        ("E2", df_e2),
        ("E3", df_e3),
        ("E4", df_e4),
        ("E6", df_e6[df_e6["model"] == "mpi_dynamic"]),
        ("E8", df_e8),
    ]

    for exp_id, df in scaling_dfs:
        # Group by configuration
        group_cols = ["model", "ranks", "threads", "p_eff", "batch", "binding", "cpuset", "schedule"]
        if exp_id == "E6":
            group_cols.append("reduce_s") # to distinguish dynamic chunks or grain sizes if needed

        # Ensure correct types
        df_work = df.copy()
        df_work["binding_real"] = df_work.apply(map_binding_real, axis=1)

        groups = df_work.groupby(
            ["model", "ranks", "threads", "p_eff", "batch", "binding", "binding_real", "cpuset", "schedule"],
            sort=False
        )

        for (model, r, t, p_eff, batch, binding, binding_real, cpuset, sched), grp in groups:
            r = int(r)
            t = int(t)
            p_eff = int(p_eff)
            batch = int(batch)

            # Determine oversubscription
            max_cores = 12 if "pcores" in cpuset else 20
            oversubscribed = 1 if p_eff > max_cores else 0

            # Metric types: default 'wall', for E4 we compute both 'wall' and 'compute'
            metric_types = ["wall"]
            if exp_id == "E4":
                metric_types = ["wall", "compute"]

            for m_type in metric_types:
                if m_type == "compute" and exp_id == "E4":
                    tp_samples = grp["verify_s"].values
                else:
                    tp_samples = grp["time_seconds"].values

                tp_median = float(np.median(tp_samples))
                tp_p25 = float(np.percentile(tp_samples, 25))
                tp_p75 = float(np.percentile(tp_samples, 75))
                tp_iqr = tp_p75 - tp_p25
                tp_throughput = float(np.median(grp["throughput"].values))

                # Strong scaling speedup vs T1
                s_med, s_low, s_high, s_boot = bootstrap_ratio(t1_samples, tp_samples, n_bootstrap, seed)
                eff = s_med / p_eff
                eff_low = s_low / p_eff
                eff_high = s_high / p_eff

                # Save bootstrap samples for Amdahl fit
                model_key = f"{model}_{m_type}" if exp_id == "E4" else model
                if model_key not in model_boot_dict:
                    model_boot_dict[model_key] = {}
                    model_p_s[model_key] = ([], [])
                model_boot_dict[model_key][p_eff] = s_boot
                model_p_s[model_key][0].append(p_eff)
                model_p_s[model_key][1].append(s_med)

                # Store speedup row
                row_dict = {
                    "experiment": exp_id,
                    "model": model,
                    "ranks": r,
                    "threads": t,
                    "p_eff": p_eff,
                    "p_workers": (r - 1) * t if model == "mpi_dynamic" else p_eff,
                    "batch": batch,
                    "time_median": tp_median,
                    "time_iqr": tp_iqr,
                    "time_p25": tp_p25,
                    "time_p75": tp_p75,
                    "throughput_median": tp_throughput,
                    "metric_type": m_type,
                    "speedup": s_med,
                    "speedup_ci_low": s_low,
                    "speedup_ci_high": s_high,
                    "efficiency": eff,
                    "efficiency_ci_low": eff_low,
                    "efficiency_ci_high": eff_high,
                    "binding": binding,
                    "binding_real": binding_real,
                    "cpuset": cpuset,
                    "schedule": sched,
                    "oversubscribed": oversubscribed
                }
                speedup_rows.append(row_dict)

                # For E6 dynamic MPI: also record row with worker pool efficiency (p = R - 1)
                if model == "mpi_dynamic":
                    p_workers = r - 1
                    if p_workers > 0:
                        eff_w = s_med / p_workers
                        eff_w_low = s_low / p_workers
                        eff_w_high = s_high / p_workers
                        row_w = row_dict.copy()
                        row_w["model"] = "mpi_dynamic_workers_only"
                        row_w["p_eff"] = p_workers
                        row_w["efficiency"] = eff_w
                        row_w["efficiency_ci_low"] = eff_w_low
                        row_w["efficiency_ci_high"] = eff_w_high
                        speedup_rows.append(row_w)

                # Karp-Flatt metric e(p) = (1/S(p) - 1/p) / (1 - 1/p)
                if p_eff > 1 and m_type == "wall":
                    kf_med = ((1.0 / s_med) - (1.0 / p_eff)) / (1.0 - (1.0 / p_eff))
                    kf_boot = ((1.0 / s_boot) - (1.0 / p_eff)) / (1.0 - (1.0 / p_eff))
                    kf_low = float(np.percentile(kf_boot, 2.5))
                    kf_high = float(np.percentile(kf_boot, 97.5))
                else:
                    kf_med = np.nan
                    kf_low = np.nan
                    kf_high = np.nan

                karp_flatt_rows.append({
                    "experiment": exp_id,
                    "model": model,
                    "ranks": r,
                    "threads": t,
                    "p_eff": p_eff,
                    "speedup": s_med,
                    "efficiency": eff,
                    "karp_flatt": kf_med,
                    "kf_ci_low": kf_low,
                    "kf_ci_high": kf_high,
                    "metric_type": m_type,
                    "binding_real": binding_real,
                    "oversubscribed": oversubscribed
                })

    df_derived_speedup = pd.DataFrame(speedup_rows)
    df_derived_kf = pd.DataFrame(karp_flatt_rows)

    df_derived_speedup.to_csv(RESULTS_DIR / "derived_speedup.csv", index=False)
    df_derived_kf.to_csv(RESULTS_DIR / "derived_karp_flatt.csv", index=False)
    print(f"[+] Written {RESULTS_DIR / 'derived_speedup.csv'} ({len(df_derived_speedup)} rows)")
    print(f"[+] Written {RESULTS_DIR / 'derived_karp_flatt.csv'} ({len(df_derived_kf)} rows)")

    # 2. Amdahl Fit on p <= 4
    amdahl_rows = []
    models_to_fit = ["omp_pure", "omp_pure_bound", "mpi_pure", "omp_pure_pcores", "mpi_pure_pcores"]
    eval_p = np.array([1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20])

    for m in models_to_fit:
        if m not in model_p_s:
            continue
        p_list, s_list = model_p_s[m]
        p_arr = np.array(p_list)
        s_arr = np.array(s_list)
        # Sort by p
        order = np.argsort(p_arr)
        p_arr = p_arr[order]
        s_arr = s_arr[order]

        fit_res = fit_amdahl_model(p_arr, s_arr, model_boot_dict[m], eval_p, n_bootstrap)
        if not fit_res:
            continue

        fs_val = fit_res["fs_fitted"]
        fs_low = fit_res["fs_ci_low"]
        fs_high = fit_res["fs_ci_high"]
        preds = fit_res["predictions"]

        # Map observed speedups
        obs_map = {p: s for p, s in zip(p_arr, s_arr)}

        for p in eval_p:
            pred_item = preds[p]
            amdahl_rows.append({
                "model": m,
                "fs_fitted": fs_val,
                "fs_ci_low": fs_low,
                "fs_ci_high": fs_high,
                "p": p,
                "speedup_observed": obs_map.get(p, np.nan),
                "speedup_predicted": pred_item["pred"],
                "pred_ci_low": pred_item["ci_low"],
                "pred_ci_high": pred_item["ci_high"]
            })

    df_amdahl = pd.DataFrame(amdahl_rows)
    df_amdahl.to_csv(RESULTS_DIR / "derived_amdahl.csv", index=False)
    print(f"[+] Written {RESULTS_DIR / 'derived_amdahl.csv'} ({len(df_amdahl)} rows)")

    # 3. Derived Schedule (E5)
    e5_rows = []
    groups_e5 = df_e5.groupby(["model", "threads", "schedule"], sort=False)
    for (m, th, sched), grp in groups_e5:
        th = int(th)
        t_samples = grp["time_seconds"].values
        t_med = float(np.median(t_samples))
        t_p25 = float(np.percentile(t_samples, 25))
        t_p75 = float(np.percentile(t_samples, 75))
        tp_throughput = float(np.median(grp["throughput"].values))
        s_med, s_low, s_high, _ = bootstrap_ratio(t1_samples, t_samples, n_bootstrap, seed)
        eff = s_med / th

        # parse schedule and chunk size
        sched_type = sched
        chunk_val = 0
        if "," in sched:
            parts = sched.split(",")
            sched_type = parts[0]
            try:
                chunk_val = int(parts[1])
            except ValueError:
                chunk_val = 0

        e5_rows.append({
            "model": m,
            "threads": th,
            "schedule": sched,
            "sched_type": sched_type,
            "chunk_size": chunk_val,
            "time_median": t_med,
            "time_iqr": t_p75 - t_p25,
            "throughput_median": tp_throughput,
            "speedup": s_med,
            "speedup_ci_low": s_low,
            "speedup_ci_high": s_high,
            "efficiency": eff,
            "efficiency_ci_low": s_low / th,
            "efficiency_ci_high": s_high / th
        })

    df_derived_e5 = pd.DataFrame(e5_rows)
    df_derived_e5.to_csv(RESULTS_DIR / "derived_schedule.csv", index=False)
    print(f"[+] Written {RESULTS_DIR / 'derived_schedule.csv'} ({len(df_derived_e5)} rows)")

    # 4. Derived Task-based (E6: OpenMP Taskloop vs Dynamic MPI)
    e6_rows = []
    groups_e6 = df_e6.groupby(["model", "ranks", "threads", "p_eff", "schedule"], sort=False)
    for (m, r, th, p_eff, sched), grp in groups_e6:
        r = int(r)
        th = int(th)
        p_eff = int(p_eff)
        t_samples = grp["time_seconds"].values
        t_med = float(np.median(t_samples))
        t_p25 = float(np.percentile(t_samples, 25))
        t_p75 = float(np.percentile(t_samples, 75))
        tp_throughput = float(np.median(grp["throughput"].values))
        s_med, s_low, s_high, _ = bootstrap_ratio(t1_samples, t_samples, n_bootstrap, seed)

        verify_med = float(np.median(grp["verify_s"].values))
        reduce_med = float(np.median(grp["reduce_s"].values))

        p_workers = (r - 1) * th if m == "mpi_dynamic" else p_eff
        eff = s_med / p_eff

        # Parse chunk or grain size from schedule string
        chunk_val = 0
        for token in sched.split("_"):
            if token.isdigit():
                chunk_val = int(token)
                break

        e6_rows.append({
            "model": m,
            "ranks": r,
            "threads": th,
            "p_eff": p_eff,
            "p_workers": p_workers,
            "schedule": sched,
            "chunk_or_grain": chunk_val,
            "time_median": t_med,
            "time_iqr": t_p75 - t_p25,
            "throughput_median": tp_throughput,
            "verify_median": verify_med,
            "reduce_median": reduce_med,
            "speedup": s_med,
            "speedup_ci_low": s_low,
            "speedup_ci_high": s_high,
            "efficiency": eff,
            "efficiency_ci_low": s_low / p_eff,
            "efficiency_ci_high": s_high / p_eff
        })

    df_derived_e6 = pd.DataFrame(e6_rows)
    df_derived_e6.to_csv(RESULTS_DIR / "derived_taskbased.csv", index=False)
    print(f"[+] Written {RESULTS_DIR / 'derived_taskbased.csv'} ({len(df_derived_e6)} rows)")

def main():
    parser = argparse.ArgumentParser(description="M13 Metrics Computation Engine")
    parser.add_argument("--all", action="store_true", default=True, help="Compute all derived metrics")
    parser.add_argument("--bootstrap", type=int, default=10000, help="Number of bootstrap resamples (default: 10000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for bootstrap (default: 42)")

    args = parser.parse_args()
    compute_all_metrics(n_bootstrap=args.bootstrap, seed=args.seed)

if __name__ == "__main__":
    main()

