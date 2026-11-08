#!/usr/bin/env python3
"""
M13 Campaign Graph Generator (Stage 13.4).

Generates publication-quality benchmark plots in both vector PDF and 300 dpi PNG:
- Fig. A: Comparative Strong Scaling (S vs p up to p=20, with core regions)
- Fig. B: Parallel Efficiency (E vs p with 0.8 and 0.5 thresholds)
- Fig. C: Karp-Flatt Metric (e(p) vs p)
- Fig. D: Amdahl's Law Fit (p <= 4 fit, projection p > 4 with 95% bootstrap band)
- Fig. E: Hybrid MPI+OpenMP Heatmap (R x T grid with SMT markers for odd T)
- Fig. F: gRPC vs MPI Pure (containerized deployment cost, Swall vs Scompute, p up to 32)
- Fig. G: OpenMP Scheduling Comparison (E5: static, dynamic, guided across chunks)
- Fig. H: Task-based vs Dynamic Master-Worker (E6: OpenMP taskloop vs MPI dynamic)
- Fig. I: Alder Lake Heterogeneity: P-cores (0-11) vs All Cores (E8 vs ALL)

Outputs saved to:
  graphs/m13/fig_a_strong_scaling.{pdf,png}
  graphs/m13/fig_b_parallel_efficiency.{pdf,png}
  graphs/m13/fig_c_karp_flatt.{pdf,png}
  graphs/m13/fig_d_amdahl_fit.{pdf,png}
  graphs/m13/fig_e_hybrid_heatmap.{pdf,png}
  graphs/m13/fig_f_grpc_vs_mpi.{pdf,png}
  graphs/m13/fig_g_openmp_schedules.{pdf,png}
  graphs/m13/fig_h_taskbased_scaling.{pdf,png}
  graphs/m13/fig_i_pcores_vs_all.{pdf,png}
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "hpc-engine" / "results" / "m13"
GRAPHS_DIR = REPO_ROOT / "graphs" / "m13"

# Styling configuration for publication quality
plt.rcParams.update({
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 13,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "--"
})

def save_fig(fig: plt.Figure, name: str) -> None:
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = GRAPHS_DIR / f"{name}.pdf"
    png_path = GRAPHS_DIR / f"{name}.png"
    fig.savefig(pdf_path)
    fig.savefig(png_path)
    plt.close(fig)
    print(f"[+] Saved: {pdf_path.name} and {png_path.name}")

def add_alder_lake_regions(ax: plt.Axes, y_min: float, y_max: float, text_y: float) -> None:
    """Add background shading and labels for Alder Lake heterogeneous core zones (U4)."""
    # Region 1: P-cores only (1-6)
    ax.axvspan(0.8, 6.2, color="#e6f2ff", alpha=0.5, zorder=0)
    # Region 2: Mix P-cores + E-cores (6.8 - 14.2)
    ax.axvspan(6.2, 14.2, color="#fff2e6", alpha=0.5, zorder=0)
    # Region 3: P-cores SMT (14.2 - 20.5)
    ax.axvspan(14.2, 20.5, color="#f2e6ff", alpha=0.5, zorder=0)

    ax.text(3.5, text_y, "P-cores\n(no SMT)", ha="center", va="center", fontsize=8, color="#004080", fontweight="bold", alpha=0.85)
    ax.text(10.2, text_y, "P-cores +\nE-cores", ha="center", va="center", fontsize=8, color="#804000", fontweight="bold", alpha=0.85)
    ax.text(17.3, text_y, "SMT\n(P-cores)", ha="center", va="center", fontsize=8, color="#600080", fontweight="bold", alpha=0.85)

# --- FIG A: Strong Scaling ---
def plot_fig_a() -> None:
    df = pd.read_csv(RESULTS_DIR / "derived_speedup.csv")

    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    # Ideal Linear
    p_ideal = np.linspace(1, 20, 100)
    ax.plot(p_ideal, p_ideal, "k--", alpha=0.6, label="Linear ideal ($S = p$)", zorder=1)

    # Machine Capacity Curves (E9b)
    cap_csv = RESULTS_DIR / "v3_machine_capacity_curve.csv"
    if cap_csv.exists():
        df_cap = pd.read_csv(cap_csv)
        if "c_dyn" in df_cap.columns:
            ax.plot(df_cap["p"], df_cap["c_dyn"], "m-.", lw=2.2, alpha=0.85, label=r"Ideal dynamic capacity $C_{\mathrm{dyn}}(p)$ (E9b)", zorder=2)
            ax.plot(df_cap["p"], df_cap["c_static"], ":", color="#d62728", lw=2.0, alpha=0.80, label=r"Static partition capacity $C_{\mathrm{static}}(p)$ (E9b)", zorder=2)
        elif "c_cap" in df_cap.columns:
            ax.plot(df_cap["p"], df_cap["c_cap"], "m-.", lw=2.2, alpha=0.85, label="Machine capacity limit $C(p)/C(1)$ (E9)", zorder=2)

    # 1. OpenMP Pure Unbound (E1)
    d1 = df[(df["experiment"] == "E1") & (df["model"] == "omp_pure")].sort_values("p_eff")
    ax.errorbar(d1["p_eff"], d1["speedup"],
                 yerr=[d1["speedup"] - d1["speedup_ci_low"], d1["speedup_ci_high"] - d1["speedup"]],
                 fmt="o-", color="#1f77b4", label="OpenMP unbound (E1, default)", capsize=3, lw=1.8, markersize=5)

    # 2. OpenMP Pure Bound (E1b)
    d1b = df[(df["experiment"] == "E1b") & (df["model"] == "omp_pure_bound")].sort_values("p_eff")
    ax.errorbar(d1b["p_eff"], d1b["speedup"],
                 yerr=[d1b["speedup"] - d1b["speedup_ci_low"], d1b["speedup_ci_high"] - d1b["speedup"]],
                 fmt="s-", color="#004d99", label="OpenMP bound (E1b, threads close)", capsize=3, lw=1.8, markersize=5)

    # 3. MPI Pure (E2)
    d2 = df[(df["experiment"] == "E2") & (df["model"] == "mpi_pure")].sort_values("p_eff")
    ax.errorbar(d2["p_eff"], d2["speedup"],
                 yerr=[d2["speedup"] - d2["speedup_ci_low"], d2["speedup_ci_high"] - d2["speedup"]],
                 fmt="^-", color="#2ca02c", label="MPI pure (E2, bind-to core)", capsize=3, lw=1.8, markersize=5)

    # 4. Hybrid MPI+OpenMP (E3) - filter bound configurations
    d3 = df[(df["experiment"] == "E3") & (df["model"] == "hybrid_mpi_omp")].sort_values("p_eff")
    ax.errorbar(d3["p_eff"], d3["speedup"],
                 yerr=[d3["speedup"] - d3["speedup_ci_low"], d3["speedup_ci_high"] - d3["speedup"]],
                 fmt="d-", color="#ff7f0e", label="Hybrid MPI+OpenMP (E3, T≥2)", capsize=3, lw=1.8, markersize=5)

    # 5. gRPC Swall (E4)
    d4 = df[(df["experiment"] == "E4") & (df["metric_type"] == "wall") & (df["threads"] == 1) & (df["p_eff"] <= 20)].sort_values("p_eff")
    ax.errorbar(d4["p_eff"], d4["speedup"],
                 yerr=[d4["speedup"] - d4["speedup_ci_low"], d4["speedup_ci_high"] - d4["speedup"]],
                 fmt="v--", color="#d62728", label="gRPC distributed ($S_{wall}$, E4)", capsize=3, lw=1.6, markersize=5)

    add_alder_lake_regions(ax, y_min=0, y_max=21, text_y=19.2)

    ax.set_xlim(0.5, 20.5)
    ax.set_ylim(0, 21)
    ax.set_xticks(range(1, 21))
    ax.set_xlabel("Effective parallelism $p$ (cores / hardware threads)")
    ax.set_ylabel("Strong Scaling Speedup $S(p) = T_1 / T_p$")
    ax.set_title("Fig. A — Comparative Strong Scaling (ECDSA P-256 Batch 20,000)")
    ax.legend(loc="upper left", framealpha=0.9)

    save_fig(fig, "fig_a_strong_scaling")

# --- FIG B: Parallel Efficiency ---
def plot_fig_b() -> None:
    df = pd.read_csv(RESULTS_DIR / "derived_speedup.csv")

    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    # Threshold lines
    ax.axhline(1.0, color="black", linestyle="--", alpha=0.5, label="Ideal ($E=1.0$)")
    ax.axhline(0.8, color="gray", linestyle=":", alpha=0.7, label="Threshold $E=0.8$")
    ax.axhline(0.5, color="red", linestyle=":", alpha=0.7, label="Threshold $E=0.5$")

    # Machine Capacity Limit Efficiency: C(p)/p (E9b)
    cap_csv = RESULTS_DIR / "v3_machine_capacity_curve.csv"
    if cap_csv.exists():
        df_cap = pd.read_csv(cap_csv)
        if "c_dyn" in df_cap.columns:
            ax.plot(df_cap["p"], df_cap["c_dyn"] / df_cap["p"], "m-.", lw=2.2, alpha=0.85, label=r"Ideal dynamic limit $C_{\mathrm{dyn}}(p)/p$ (E9b)", zorder=2)
            ax.plot(df_cap["p"], df_cap["c_static"] / df_cap["p"], ":", color="#d62728", lw=2.0, alpha=0.80, label=r"Static partition limit $C_{\mathrm{static}}(p)/p$ (E9b)", zorder=2)
        elif "c_cap" in df_cap.columns:
            ax.plot(df_cap["p"], df_cap["c_cap"] / df_cap["p"], "m-.", lw=2.2, alpha=0.85, label="Capacity limit $C(p)/p$ (E9)", zorder=2)

    # 1. OpenMP Pure Unbound (E1)
    d1 = df[(df["experiment"] == "E1") & (df["model"] == "omp_pure")].sort_values("p_eff")
    ax.plot(d1["p_eff"], d1["efficiency"], "o-", color="#1f77b4", label="OpenMP unbound (E1)", lw=1.8, markersize=5)

    # 2. OpenMP Pure Bound (E1b)
    d1b = df[(df["experiment"] == "E1b") & (df["model"] == "omp_pure_bound")].sort_values("p_eff")
    ax.plot(d1b["p_eff"], d1b["efficiency"], "s-", color="#004d99", label="OpenMP bound (E1b)", lw=1.8, markersize=5)

    # 3. MPI Pure (E2)
    d2 = df[(df["experiment"] == "E2") & (df["model"] == "mpi_pure")].sort_values("p_eff")
    ax.plot(d2["p_eff"], d2["efficiency"], "^-", color="#2ca02c", label="MPI pure (E2)", lw=1.8, markersize=5)

    # 4. Hybrid MPI+OpenMP (E3)
    d3 = df[(df["experiment"] == "E3") & (df["model"] == "hybrid_mpi_omp")].sort_values("p_eff")
    ax.plot(d3["p_eff"], d3["efficiency"], "d-", color="#ff7f0e", label="Hybrid MPI+OpenMP (E3)", lw=1.8, markersize=5)

    # 5. gRPC Swall (E4)
    d4 = df[(df["experiment"] == "E4") & (df["metric_type"] == "wall") & (df["threads"] == 1) & (df["p_eff"] <= 20)].sort_values("p_eff")
    ax.plot(d4["p_eff"], d4["efficiency"], "v--", color="#d62728", label="gRPC distributed ($E_{wall}$, E4)", lw=1.6, markersize=5)

    add_alder_lake_regions(ax, y_min=0, y_max=1.1, text_y=1.04)

    ax.set_xlim(0.5, 20.5)
    ax.set_ylim(0.0, 1.1)
    ax.set_xticks(range(1, 21))
    ax.set_xlabel("Effective parallelism $p$")
    ax.set_ylabel("Parallel Efficiency $E(p) = S(p) / p$")
    ax.set_title("Fig. B — Parallel Efficiency $E(p)$ vs Number of Workers")
    ax.legend(loc="lower left", framealpha=0.9)

    save_fig(fig, "fig_b_parallel_efficiency")

# --- FIG C: Karp-Flatt Metric ---
def plot_fig_c() -> None:
    df = pd.read_csv(RESULTS_DIR / "derived_karp_flatt.csv")

    fig, ax = plt.subplots(figsize=(8.5, 5.2))

    # OpenMP Unbound (E1)
    d1 = df[(df["experiment"] == "E1") & (df["p_eff"] > 1)].sort_values("p_eff")
    ax.plot(d1["p_eff"], d1["karp_flatt"], "o-", color="#1f77b4", label="OpenMP unbound (E1)", lw=1.8, markersize=5)

    # OpenMP Bound (E1b)
    d1b = df[(df["experiment"] == "E1b") & (df["p_eff"] > 1)].sort_values("p_eff")
    ax.plot(d1b["p_eff"], d1b["karp_flatt"], "s-", color="#004d99", label="OpenMP bound (E1b)", lw=1.8, markersize=5)

    # MPI Pure (E2)
    d2 = df[(df["experiment"] == "E2") & (df["p_eff"] > 1)].sort_values("p_eff")
    ax.plot(d2["p_eff"], d2["karp_flatt"], "^-", color="#2ca02c", label="MPI pure (E2)", lw=1.8, markersize=5)

    # Hybrid (E3)
    d3 = df[(df["experiment"] == "E3") & (df["p_eff"] > 1) & (df["binding_real"] != "unbound")].sort_values("p_eff")
    ax.plot(d3["p_eff"], d3["karp_flatt"], "d-", color="#ff7f0e", label="Hybrid MPI+OpenMP (E3)", lw=1.8, markersize=5)

    # gRPC (E4)
    d4 = df[(df["experiment"] == "E4") & (df["p_eff"] > 1) & (df["p_eff"] <= 20)].sort_values("p_eff")
    ax.plot(d4["p_eff"], d4["karp_flatt"], "v--", color="#d62728", label="gRPC wall (E4)", lw=1.6, markersize=5)

    ax.set_xlim(1.5, 20.5)
    ax.set_ylim(-0.02, 0.45)
    ax.set_xticks(range(2, 21))
    ax.set_xlabel("Effective parallelism $p$")
    ax.set_ylabel("Karp-Flatt Metric $e(p) = \\frac{1/S(p) - 1/p}{1 - 1/p}$")
    ax.set_title("Fig. C — Karp-Flatt Metric $e(p)$ (Algorithmic Overhead vs Contention)")
    ax.legend(loc="upper left", framealpha=0.9)

    save_fig(fig, "fig_c_karp_flatt")

# --- FIG D: Amdahl Fit ---
def plot_fig_d() -> None:
    df_amdahl = pd.read_csv(RESULTS_DIR / "derived_amdahl.csv")
    df_speedup = pd.read_csv(RESULTS_DIR / "derived_speedup.csv")

    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    p_dense = np.linspace(1, 20, 200)

    # 1. OpenMP Pure
    d_omp = df_amdahl[df_amdahl["model"] == "omp_pure"].sort_values("p")
    if not d_omp.empty:
        fs_omp = d_omp["fs_fitted"].iloc[0]
        fs_low = d_omp["fs_ci_low"].iloc[0]
        fs_high = d_omp["fs_ci_high"].iloc[0]

        # Observed points
        obs_fit = d_omp[d_omp["p"] <= 4]
        obs_proj = d_omp[d_omp["p"] > 4]
        ax.plot(obs_fit["p"], obs_fit["speedup_observed"], "o", color="#1f77b4", markersize=7, label=r"OpenMP fit points ($p \leq 4$)")
        ax.plot(obs_proj["p"], obs_proj["speedup_observed"], "s", color="#1f77b4", fillstyle="none", markersize=6, label=r"OpenMP observed ($p > 4$)")

        # Predicted curve
        pred_omp = 1.0 / (fs_omp + (1.0 - fs_omp) / p_dense)
        pred_low = 1.0 / (fs_high + (1.0 - fs_high) / p_dense)
        pred_high = 1.0 / (fs_low + (1.0 - fs_low) / p_dense)
        ax.plot(p_dense, pred_omp, "-", color="#1f77b4", lw=2, label=f"OpenMP Amdahl fit ($f_s={fs_omp*100:.2f}\\%$)")
        ax.fill_between(p_dense, pred_low, pred_high, color="#1f77b4", alpha=0.15, label="OpenMP 95% bootstrap CI")

    # 2. MPI Pure
    d_mpi = df_amdahl[df_amdahl["model"] == "mpi_pure"].sort_values("p")
    if not d_mpi.empty:
        fs_mpi = d_mpi["fs_fitted"].iloc[0]
        fs_low_m = d_mpi["fs_ci_low"].iloc[0]
        fs_high_m = d_mpi["fs_ci_high"].iloc[0]

        obs_fit_m = d_mpi[d_mpi["p"] <= 4]
        obs_proj_m = d_mpi[d_mpi["p"] > 4]
        ax.plot(obs_fit_m["p"], obs_fit_m["speedup_observed"], "^", color="#2ca02c", markersize=7, label=r"MPI fit points ($p \leq 4$)")
        ax.plot(obs_proj_m["p"], obs_proj_m["speedup_observed"], "d", color="#2ca02c", fillstyle="none", markersize=6, label=r"MPI observed ($p > 4$)")

        pred_mpi = 1.0 / (fs_mpi + (1.0 - fs_mpi) / p_dense)
        pred_low_m = 1.0 / (fs_high_m + (1.0 - fs_high_m) / p_dense)
        pred_high_m = 1.0 / (fs_low_m + (1.0 - fs_low_m) / p_dense)
        ax.plot(p_dense, pred_mpi, "-", color="#2ca02c", lw=2, label=f"MPI Amdahl fit ($f_s={fs_mpi*100:.2f}\\%$)")
        ax.fill_between(p_dense, pred_low_m, pred_high_m, color="#2ca02c", alpha=0.15, label="MPI 95% bootstrap CI")

    # Linear ideal
    ax.plot(p_dense, p_dense, "k--", alpha=0.4, label="Ideal linear")

    ax.set_xlim(0.5, 20.5)
    ax.set_ylim(0, 21)
    ax.set_xticks(range(1, 21))
    ax.set_xlabel("Effective parallelism $p$")
    ax.set_ylabel("Speedup $S(p)$")
    ax.set_title(r"Fig. D — Amdahl's Law Fit on $p \leq 4$ and Projection for $p > 4$")
    ax.legend(loc="upper left", framealpha=0.9, fontsize=8.5)

    save_fig(fig, "fig_d_amdahl_fit")

# --- FIG E: Hybrid Heatmap ---
def plot_fig_e() -> None:
    df = pd.read_csv(RESULTS_DIR / "derived_speedup.csv")
    d3 = df[(df["experiment"] == "E3") & (df["model"] == "hybrid_mpi_omp")]

    # Pivot table: R (rows) x T (cols) -> throughput
    pivot = d3.pivot(index="ranks", columns="threads", values="throughput_median")

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    cax = ax.imshow(pivot.values, cmap="YlGnBu", aspect="auto", origin="lower")

    ranks_list = list(pivot.index)
    threads_list = list(pivot.columns)

    ax.set_xticks(range(len(threads_list)))
    ax.set_xticklabels([f"T={t}" for t in threads_list])
    ax.set_yticks(range(len(ranks_list)))
    ax.set_yticklabels([f"R={r}" for r in ranks_list])

    # Annotate cells with throughput and mark odd T (U3)
    for i, r in enumerate(ranks_list):
        for j, t in enumerate(threads_list):
            val = pivot.iloc[i, j]
            if np.isnan(val):
                continue
            p_eff = r * t
            cell_text = f"{val/1000:.1f}k\n(p={p_eff})"
            # Marker for odd threads where ranks share physical core via SMT
            if t in [3, 5]:
                cell_text += "\n★ SMT"
            color = "white" if val > pivot.values[~np.isnan(pivot.values)].mean() else "black"
            ax.text(j, i, cell_text, ha="center", va="center", color=color, fontsize=8.5, fontweight="bold")

    cbar = fig.colorbar(cax, ax=ax)
    cbar.set_label("Throughput (signatures/sec)")

    ax.set_xlabel("Threads per rank ($T$)")
    ax.set_ylabel("MPI Ranks ($R$)")
    ax.set_title("Fig. E — Hybrid MPI+OpenMP Performance Grid ($R \\times T$)\n(★ denotes odd $T=3,5$ sharing core via SMT per U3)")

    save_fig(fig, "fig_e_hybrid_heatmap")

# --- FIG F: gRPC vs MPI Pure ---
def plot_fig_f() -> None:
    df = pd.read_csv(RESULTS_DIR / "derived_speedup.csv")

    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    # MPI pure (E2)
    d_mpi = df[(df["experiment"] == "E2") & (df["model"] == "mpi_pure")].sort_values("ranks")
    ax.plot(d_mpi["ranks"], d_mpi["throughput_median"] / 1000.0, "^-", color="#2ca02c", lw=2, markersize=6, label="MPI pure native (E2, core binding)")

    # gRPC wall and compute (E4)
    d_grpc_wall = df[(df["experiment"] == "E4") & (df["metric_type"] == "wall") & (df["threads"] == 1)].sort_values("ranks")
    d_grpc_comp = df[(df["experiment"] == "E4") & (df["metric_type"] == "compute") & (df["threads"] == 1)].sort_values("ranks")

    ax.plot(d_grpc_comp["ranks"], d_grpc_comp["throughput_median"] / 1000.0, "s--", color="#ff7f0e", lw=1.8, markersize=5, label="gRPC worker compute only (E4, $S_{compute}$)")
    ax.plot(d_grpc_wall["ranks"], d_grpc_wall["throughput_median"] / 1000.0, "v-", color="#d62728", lw=2, markersize=6, label="gRPC end-to-end wall-clock (E4, $S_{wall}$)")

    # Draw vertical separator for p=20 (host core limit) -> p=32
    ax.axvline(20, color="gray", linestyle=":", alpha=0.7)
    ax.text(20.5, 120, "Host core limit (20)\nOversubscription ->", fontsize=8.5, color="gray", va="center")

    ax.set_xlim(0, 33)
    ax.set_ylim(0, 350)
    ax.set_xlabel("Number of logical workers / nodes")
    ax.set_ylabel("Throughput (k sig/s)")
    ax.set_title("Fig. F — Containerized gRPC (E4) vs Native MPI Pure (E2)")
    ax.legend(loc="upper left", framealpha=0.9)

    save_fig(fig, "fig_f_grpc_vs_mpi")

# --- FIG G: OpenMP Schedules ---
def plot_fig_g() -> None:
    df = pd.read_csv(RESULTS_DIR / "derived_schedule.csv")
    # Take T=16 (or largest thread count)
    d16 = df[df["threads"] == 16].copy()
    if d16.empty:
        d16 = df.copy()

    # Sort by throughput
    d16 = d16.sort_values("throughput_median", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 6))

    y_pos = np.arange(len(d16))
    colors = ["#1f77b4" if "static" in s else ("#ff7f0e" if "dynamic" in s else "#2ca02c") for s in d16["schedule"]]

    ax.barh(y_pos, d16["throughput_median"] / 1000.0, color=colors, alpha=0.85, edgecolor="black", lw=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(d16["schedule"])

    # Annotate values
    for i, val in enumerate(d16["throughput_median"] / 1000.0):
        ax.text(val + 1.0, i, f"{val:.1f}k", va="center", fontsize=8.5)

    ax.set_xlabel("Throughput (k sig/s)")
    ax.set_ylabel("OpenMP Schedule Clause")
    ax.set_title(f"Fig. G — OpenMP Scheduling Overhead Comparison (T={d16['threads'].iloc[0]})")

    # Custom legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#1f77b4", edgecolor="black", label="Static"),
        Patch(facecolor="#ff7f0e", edgecolor="black", label="Dynamic"),
        Patch(facecolor="#2ca02c", edgecolor="black", label="Guided"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", framealpha=0.9)

    save_fig(fig, "fig_g_openmp_schedules")

# --- FIG H: Task-based Scaling ---
def plot_fig_h() -> None:
    df = pd.read_csv(RESULTS_DIR / "derived_taskbased.csv")

    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    # 1. OpenMP taskloop
    d_omp = df[df["model"] == "omp_taskloop"].sort_values("threads")
    for grain, grp in d_omp.groupby("chunk_or_grain"):
        ax.plot(grp["threads"], grp["throughput_median"] / 1000.0, "o-", label=f"OpenMP taskloop (grain={grain})", lw=1.8, markersize=5)

    # 2. MPI dynamic (master-worker)
    d_dyn = df[df["model"] == "mpi_dynamic"].sort_values("ranks")
    for chunk, grp in d_dyn.groupby("chunk_or_grain"):
        # Plot vs total ranks R
        ax.plot(grp["ranks"], grp["throughput_median"] / 1000.0, "s--", label=f"MPI dynamic (chunk={chunk}, p=R)", lw=1.8, markersize=5)

    ax.set_xlim(0.5, 9.5)
    ax.set_xticks(range(1, 10))
    ax.set_xlabel("Workers / Ranks ($p$)")
    ax.set_ylabel("Throughput (k sig/s)")
    ax.set_title("Fig. H — Dynamic Task-based Scaling: OpenMP Taskloop vs MPI Dynamic")
    ax.legend(loc="upper left", framealpha=0.9, fontsize=8.5)

    save_fig(fig, "fig_h_taskbased_scaling")

# --- FIG I: P-cores vs ALL ---
def plot_fig_i() -> None:
    df = pd.read_csv(RESULTS_DIR / "derived_speedup.csv")

    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    # P-cores OpenMP (E8)
    d_omp_p = df[(df["experiment"] == "E8") & (df["model"] == "omp_pure_pcores")].sort_values("threads")
    ax.plot(d_omp_p["threads"], d_omp_p["speedup"], "o-", color="#1f77b4", lw=2, markersize=6, label="OpenMP (P-cores only, taskset 0-11)")

    # All cores OpenMP (E1)
    d_omp_all = df[(df["experiment"] == "E1") & (df["model"] == "omp_pure") & (df["threads"] <= 12)].sort_values("threads")
    ax.plot(d_omp_all["threads"], d_omp_all["speedup"], "o--", color="#6baed6", lw=1.8, markersize=5, label="OpenMP (All cores, unbound)")

    # P-cores MPI (E8)
    d_mpi_p = df[(df["experiment"] == "E8") & (df["model"] == "mpi_pure_pcores")].sort_values("ranks")
    ax.plot(d_mpi_p["ranks"], d_mpi_p["speedup"], "^-", color="#2ca02c", lw=2, markersize=6, label="MPI pure (P-cores only, core binding)")

    # All cores MPI (E2)
    d_mpi_all = df[(df["experiment"] == "E2") & (df["model"] == "mpi_pure") & (df["ranks"] <= 12)].sort_values("ranks")
    ax.plot(d_mpi_all["ranks"], d_mpi_all["speedup"], "^--", color="#74c476", lw=1.8, markersize=5, label="MPI pure (All cores, core binding)")

    # Ideal linear
    p_arr = np.arange(1, 13)
    ax.plot(p_arr, p_arr, "k--", alpha=0.4, label="Ideal linear")

    # Add vertical line at p=6 (where P-core physical cores end and SMT begins)
    ax.axvline(6, color="purple", linestyle=":", alpha=0.7)
    ax.text(6.1, 2.5, "P-core physical limit (6)\n-> SMT kicks in", fontsize=8.5, color="purple")

    ax.set_xlim(0.5, 12.5)
    ax.set_ylim(0, 13)
    ax.set_xticks(range(1, 13))
    ax.set_xlabel("Effective parallelism $p$")
    ax.set_ylabel("Speedup $S(p)$")
    ax.set_title("Fig. I — Heterogeneity Impact: P-cores (0-11) vs All Cores (E8 vs E1/E2)")
    ax.legend(loc="upper left", framealpha=0.9)

    save_fig(fig, "fig_i_pcores_vs_all")

def main():
    parser = argparse.ArgumentParser(description="M13 Graph Generator")
    parser.add_argument("--fig", choices=["A", "B", "C", "D", "E", "F", "G", "H", "I", "ALL"], default="ALL",
                        help="Figure to generate (default: ALL)")
    args = parser.parse_args()

    dispatch = {
        "A": plot_fig_a,
        "B": plot_fig_b,
        "C": plot_fig_c,
        "D": plot_fig_d,
        "E": plot_fig_e,
        "F": plot_fig_f,
        "G": plot_fig_g,
        "H": plot_fig_h,
        "I": plot_fig_i,
    }

    if args.fig == "ALL":
        for k, func in dispatch.items():
            func()
    else:
        dispatch[args.fig]()

if __name__ == "__main__":
    main()
