#!/usr/bin/env python3
"""
M13 Campaign Graph Generator (Stage 13.5-sexies).

Generates publication-quality benchmark plots in both vector PDF and 300 dpi PNG,
and exports plotted coordinates to report/figure_data/ for automated anti-regression checking.

Figures generated:
- Fig. A (Fig. 6 in report): Comparative Strong Scaling (S vs p up to p=20, with core regions)
- Fig. B (Fig. 10 in report): Parallel Efficiency (E vs p with 0.8 and 0.5 thresholds)
- Fig. C (Fig. 7 in report): Karp-Flatt Metric (e(p) vs p)
- Fig. D (Fig. 11 in report): Amdahl's Law Fit (p <= 4 fit for E2b and E1c, projection p > 4)
- Fig. E: Hybrid MPI+OpenMP Heatmap (R x T grid)
- Fig. F (Fig. 12 in report): gRPC vs MPI Pure (Swall vs Scompute up to p=32)
- Fig. G (Fig. 8 in report): OpenMP Scheduling Comparison at T=16 (static, guided, dynamic,16)
- Fig. H (Fig. 9 in report): Dynamic Task-based Scaling (OpenMP taskloop vs MPI dynamic)
- Fig. I: Alder Lake Heterogeneity: P-cores vs All Cores

Outputs saved to:
  graphs/m13/
  report/figures/
  report/figure_data/
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import Patch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "hpc-engine" / "results" / "m13"
GRAPHS_DIR = REPO_ROOT / "graphs" / "m13"
REPORT_FIGS_DIR = REPO_ROOT / "report" / "figures"
REPORT_FIG_DATA_DIR = REPO_ROOT / "report" / "figure_data"

T1_BASELINE = 1.063555  # median of results_e0b_sequential.csv (18,804.8 sig/s)
V1_RATE = 20000.0 / T1_BASELINE  # 18,804.819... sig/s

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

def save_fig_and_data(fig: plt.Figure, name: str, data_rows: List[Dict[str, Any]], data_filename: str) -> None:
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FIGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FIG_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Save to graphs/m13/
    pdf_path = GRAPHS_DIR / f"{name}.pdf"
    png_path = GRAPHS_DIR / f"{name}.png"
    fig.savefig(pdf_path)
    fig.savefig(png_path)

    # Save directly to report/figures/
    rep_pdf = REPORT_FIGS_DIR / f"{name}.pdf"
    rep_png = REPORT_FIGS_DIR / f"{name}.png"
    fig.savefig(rep_pdf)
    fig.savefig(rep_png)

    plt.close(fig)

    # Export figure data CSV
    df_data = pd.DataFrame(data_rows)
    csv_path = REPORT_FIG_DATA_DIR / f"{data_filename}.csv"
    df_data.to_csv(csv_path, index=False)
    print(f"[+] Saved: {name}.pdf (.png) -> graphs/ & report/figures/ | Data -> {csv_path.name} ({len(df_data)} rows)")

def add_alder_lake_regions(ax: plt.Axes, text_y: float) -> None:
    """Add background shading and labels for Alder Lake heterogeneous core zones."""
    ax.axvspan(0.8, 6.2, color="#e6f2ff", alpha=0.5, zorder=0)
    ax.axvspan(6.2, 14.2, color="#fff2e6", alpha=0.5, zorder=0)
    ax.axvspan(14.2, 20.5, color="#f2e6ff", alpha=0.5, zorder=0)

    ax.text(3.5, text_y, "P-cores\n(no SMT)", ha="center", va="center", fontsize=8, color="#004080", fontweight="bold", alpha=0.85)
    ax.text(10.2, text_y, "P-cores +\nE-cores", ha="center", va="center", fontsize=8, color="#804000", fontweight="bold", alpha=0.85)
    ax.text(17.3, text_y, "SMT\n(P-cores)", ha="center", va="center", fontsize=8, color="#600080", fontweight="bold", alpha=0.85)

# ==============================================================================
# FIG A (Fig. 6 in Report): Strong Scaling
# ==============================================================================
def plot_fig_a() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    data_rows = []

    # 1. Ideal Linear
    p_ideal = np.arange(1, 21)
    ax.plot(p_ideal, p_ideal, "k--", alpha=0.6, label="Linear ideal ($S = p$)", zorder=1)
    for p in p_ideal:
        data_rows.append({"series": "Linear ideal", "x": p, "y": float(p)})

    # 2. Machine Capacity Limits (E9b)
    cap_csv = RESULTS_DIR / "v3_machine_capacity_curve.csv"
    if cap_csv.exists():
        df_cap = pd.read_csv(cap_csv)
        ax.plot(df_cap["p"], df_cap["c_dyn"], "m-.", lw=2.2, alpha=0.85, label=r"Ideal dynamic capacity $C_{\mathrm{dyn}}(p)$ (E9b)", zorder=2)
        ax.plot(df_cap["p"], df_cap["c_static"], ":", color="#d62728", lw=2.0, alpha=0.80, label=r"Static partition capacity $C_{\mathrm{static}}(p)$ (E9b)", zorder=2)
        for _, r in df_cap.iterrows():
            data_rows.append({"series": "Capacity dynamic (E9b)", "x": int(r["p"]), "y": float(r["c_dyn"])})
            data_rows.append({"series": "Capacity static (E9b)", "x": int(r["p"]), "y": float(r["c_static"])})

    # 3. OpenMP Pure Unbound (E1)
    e1 = pd.read_csv(RESULTS_DIR / "results_e1_omp_pure.csv")
    e1_p, e1_s = [], []
    for p in sorted(e1["threads"].unique()):
        if p > 20: continue
        sub = e1[e1["threads"] == p]
        med = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        e1_p.append(p)
        e1_s.append(med)
        data_rows.append({"series": "OpenMP unbound (E1)", "x": p, "y": med})
    ax.plot(e1_p, e1_s, "o--", color="#6baed6", lw=1.5, markersize=4, label="OpenMP unbound (E1)")

    # 4. OpenMP Close (E1c)
    e1c = pd.read_csv(RESULTS_DIR / "results_e1c_omp_cores_close.csv")
    e1c_p, e1c_s = [], []
    for p in sorted(e1c["threads"].unique()):
        if p > 20: continue
        sub = e1c[e1c["threads"] == p]
        med = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        e1c_p.append(p)
        e1c_s.append(med)
        data_rows.append({"series": "OpenMP close (E1c)", "x": p, "y": med})
    ax.plot(e1c_p, e1c_s, "s-", color="#1f77b4", lw=2.0, markersize=5, label="OpenMP close (E1c, cores close)")

    # 5. MPI Pure (E2b)
    e2b = pd.read_csv(RESULTS_DIR / "results_e2b_mpi_map_core.csv")
    e2b_p, e2b_s = [], []
    for p in sorted(e2b["ranks"].unique()):
        if p > 20: continue
        sub = e2b[e2b["ranks"] == p]
        med = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        e2b_p.append(p)
        e2b_s.append(med)
        data_rows.append({"series": "MPI pure (E2b)", "x": p, "y": med})
    ax.plot(e2b_p, e2b_s, "^-", color="#2ca02c", lw=2.0, markersize=6, label="MPI pure (E2b, core binding)")

    # 6. Hybrid Dedicated Physical Cores (E3b)
    e3b = pd.read_csv(RESULTS_DIR / "results_e3b_hybrid_map_core.csv")
    e3b_p, e3b_s = [], []
    for p in sorted(e3b["physical_cores"].unique()):
        if p > 20: continue
        sub = e3b[e3b["physical_cores"] == p]
        med = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        e3b_p.append(p)
        e3b_s.append(med)
        data_rows.append({"series": "Hybrid (E3b)", "x": p, "y": med})
    ax.plot(e3b_p, e3b_s, "d-", color="#ff7f0e", lw=2.0, markersize=6, label=r"Hybrid (E3b, dedicated cores $T=2$)")

    # 7. Hybrid Hardware-Thread Mapping (E3)
    e3 = pd.read_csv(RESULTS_DIR / "results_e3_hybrid.csv")
    e3_p, e3_s = [], []
    for p in [16, 20]:
        sub = e3[(e3["ranks"] * e3["threads"] == p) & (e3["binding"].str.contains("slot"))]
        med = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        e3_p.append(p)
        e3_s.append(med)
        data_rows.append({"series": "Hybrid (E3)", "x": p, "y": med})
    ax.plot(e3_p, e3_s, "*-", color="#d95f02", lw=1.8, markersize=8, label=r"Hybrid (E3, hwthread $p=16, 20$)")

    # 8. gRPC Isolated (E4) - Both Swall and Scompute
    e4 = pd.read_csv(RESULTS_DIR / "results_e4_grpc.csv")
    e4_p, e4_sw, e4_sc = [], [], []
    for p in [2, 4, 6, 8, 10, 12, 16, 20]:
        sub = e4[e4["p_eff"] == p]
        sw = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        sc = float(np.median(T1_BASELINE / sub["verify_s"].values))
        e4_p.append(p)
        e4_sw.append(sw)
        e4_sc.append(sc)
        data_rows.append({"series": "gRPC wall (E4)", "x": p, "y": sw})
        data_rows.append({"series": "gRPC compute (E4)", "x": p, "y": sc})
    ax.plot(e4_p, e4_sc, "P:", color="#9467bd", lw=1.8, markersize=6, label=r"gRPC ($S_{\mathrm{compute}}$, E4)")
    ax.plot(e4_p, e4_sw, "v--", color="#d62728", lw=1.8, markersize=6, label=r"gRPC ($S_{\mathrm{wall}}$, E4)")

    add_alder_lake_regions(ax, text_y=19.2)

    ax.set_xlim(0.5, 20.5)
    ax.set_ylim(0, 21)
    ax.set_xticks(range(1, 21))
    ax.set_xlabel("Effective parallelism $p$ (cores / hardware threads)")
    ax.set_ylabel("Strong Scaling Speedup $S(p) = T_1 / T_p$")
    ax.set_title("Comparative Strong Scaling (ECDSA P-256 Batch 20,000)")
    ax.legend(loc="upper left", framealpha=0.9, fontsize=8.5)

    save_fig_and_data(fig, "fig_a_strong_scaling", data_rows, "fig06_strong_scaling")

# ==============================================================================
# FIG B (Fig. 10 in Report): Parallel Efficiency
# ==============================================================================
def plot_fig_b() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 6.0))
    data_rows = []

    # Threshold lines
    ax.axhline(1.0, color="black", linestyle="--", alpha=0.5, label="Ideal ($E=1.0$)")
    ax.axhline(0.8, color="gray", linestyle=":", alpha=0.7, label="Threshold $E=0.8$")
    ax.axhline(0.5, color="red", linestyle=":", alpha=0.7, label="Threshold $E=0.5$")

    # Capacity Limits
    cap_csv = RESULTS_DIR / "v3_machine_capacity_curve.csv"
    if cap_csv.exists():
        df_cap = pd.read_csv(cap_csv)
        ax.plot(df_cap["p"], df_cap["c_dyn"] / df_cap["p"], "m-.", lw=2.2, alpha=0.85, label=r"Ideal dynamic limit $C_{\mathrm{dyn}}(p)/p$ (E9b)")
        ax.plot(df_cap["p"], df_cap["c_static"] / df_cap["p"], ":", color="#d62728", lw=2.0, alpha=0.80, label=r"Static partition limit $C_{\mathrm{static}}(p)/p$ (E9b)")
        for _, r in df_cap.iterrows():
            data_rows.append({"series": "Capacity dynamic limit", "x": int(r["p"]), "y": float(r["c_dyn"] / r["p"])})
            data_rows.append({"series": "Capacity static limit", "x": int(r["p"]), "y": float(r["c_static"] / r["p"])})

    # OpenMP Unbound (E1)
    e1 = pd.read_csv(RESULTS_DIR / "results_e1_omp_pure.csv")
    e1_p, e1_e = [], []
    for p in sorted(e1["threads"].unique()):
        if p > 20: continue
        sub = e1[e1["threads"] == p]
        eff = float(np.median(T1_BASELINE / sub["time_seconds"].values) / p)
        e1_p.append(p)
        e1_e.append(eff)
        data_rows.append({"series": "OpenMP unbound (E1)", "x": p, "y": eff})
    ax.plot(e1_p, e1_e, "o--", color="#6baed6", lw=1.5, markersize=4, label="OpenMP unbound (E1)")

    # OpenMP Close (E1c)
    e1c = pd.read_csv(RESULTS_DIR / "results_e1c_omp_cores_close.csv")
    e1c_p, e1c_e = [], []
    for p in sorted(e1c["threads"].unique()):
        if p > 20: continue
        sub = e1c[e1c["threads"] == p]
        eff = float(np.median(T1_BASELINE / sub["time_seconds"].values) / p)
        e1c_p.append(p)
        e1c_e.append(eff)
        data_rows.append({"series": "OpenMP close (E1c)", "x": p, "y": eff})
    ax.plot(e1c_p, e1c_e, "s-", color="#1f77b4", lw=2.0, markersize=5, label="OpenMP close (E1c)")

    # MPI Pure (E2b)
    e2b = pd.read_csv(RESULTS_DIR / "results_e2b_mpi_map_core.csv")
    e2b_p, e2b_e = [], []
    for p in sorted(e2b["ranks"].unique()):
        if p > 20: continue
        sub = e2b[e2b["ranks"] == p]
        eff = float(np.median(T1_BASELINE / sub["time_seconds"].values) / p)
        e2b_p.append(p)
        e2b_e.append(eff)
        data_rows.append({"series": "MPI pure (E2b)", "x": p, "y": eff})
    ax.plot(e2b_p, e2b_e, "^-", color="#2ca02c", lw=2.0, markersize=6, label="MPI pure (E2b)")

    # Hybrid E3b
    e3b = pd.read_csv(RESULTS_DIR / "results_e3b_hybrid_map_core.csv")
    e3b_p, e3b_e = [], []
    for p in sorted(e3b["physical_cores"].unique()):
        if p > 20: continue
        sub = e3b[e3b["physical_cores"] == p]
        eff = float(np.median(T1_BASELINE / sub["time_seconds"].values) / p)
        e3b_p.append(p)
        e3b_e.append(eff)
        data_rows.append({"series": "Hybrid (E3b)", "x": p, "y": eff})
    ax.plot(e3b_p, e3b_e, "d-", color="#ff7f0e", lw=2.0, markersize=6, label="Hybrid (E3b)")

    # Hybrid E3
    e3 = pd.read_csv(RESULTS_DIR / "results_e3_hybrid.csv")
    e3_p, e3_e = [], []
    for p in [16, 20]:
        sub = e3[(e3["ranks"] * e3["threads"] == p) & (e3["binding"].str.contains("slot"))]
        eff = float(np.median(T1_BASELINE / sub["time_seconds"].values) / p)
        e3_p.append(p)
        e3_e.append(eff)
        data_rows.append({"series": "Hybrid (E3)", "x": p, "y": eff})
    ax.plot(e3_p, e3_e, "*-", color="#d95f02", lw=1.8, markersize=8, label="Hybrid (E3)")

    # gRPC Wall and Compute (E4)
    e4 = pd.read_csv(RESULTS_DIR / "results_e4_grpc.csv")
    e4_p, e4_ew, e4_ec = [], [], []
    for p in [2, 4, 6, 8, 10, 12, 16, 20]:
        sub = e4[e4["p_eff"] == p]
        ew = float(np.median(T1_BASELINE / sub["time_seconds"].values) / p)
        ec = float(np.median(T1_BASELINE / sub["verify_s"].values) / p)
        e4_p.append(p)
        e4_ew.append(ew)
        e4_ec.append(ec)
        data_rows.append({"series": "gRPC wall (E4)", "x": p, "y": ew})
        data_rows.append({"series": "gRPC compute (E4)", "x": p, "y": ec})
    ax.plot(e4_p, e4_ec, "P:", color="#9467bd", lw=1.8, markersize=6, label=r"gRPC ($E_{\mathrm{compute}}$, E4)")
    ax.plot(e4_p, e4_ew, "v--", color="#d62728", lw=1.8, markersize=6, label=r"gRPC ($E_{\mathrm{wall}}$, E4)")

    add_alder_lake_regions(ax, text_y=1.04)

    ax.set_xlim(0.5, 20.5)
    ax.set_ylim(0.0, 1.1)
    ax.set_xticks(range(1, 21))
    ax.set_xlabel("Effective parallelism $p$")
    ax.set_ylabel("Parallel Efficiency $E(p) = S(p) / p$")
    ax.set_title("Parallel Efficiency $E(p)$ vs Number of Workers")
    # H3: Move legend outside data area below the x-axis in 3 columns
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=3,
        framealpha=0.92,
        fontsize=8.2,
        columnspacing=1.0,
        handletextpad=0.4
    )

    save_fig_and_data(fig, "fig_b_parallel_efficiency", data_rows, "fig10_parallel_efficiency")

# ==============================================================================
# FIG C (Fig. 7 in Report): Karp-Flatt Metric
# ==============================================================================
def plot_fig_c() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    data_rows = []

    def calc_kf(s_val: float, p_val: int) -> float:
        return float((1.0 / s_val - 1.0 / p_val) / (1.0 - 1.0 / p_val))

    # 1. MPI Pure (E2b)
    e2b = pd.read_csv(RESULTS_DIR / "results_e2b_mpi_map_core.csv")
    e2b_p, e2b_kf = [], []
    for p in sorted(e2b["ranks"].unique()):
        if p < 2 or p > 20: continue
        sub = e2b[e2b["ranks"] == p]
        s = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        kf = calc_kf(s, p)
        e2b_p.append(p)
        e2b_kf.append(kf)
        data_rows.append({"series": "MPI pure (E2b)", "x": p, "y": kf})
    ax.plot(e2b_p, e2b_kf, "^-", color="#2ca02c", lw=2.0, markersize=6, label="MPI pure (E2b)")

    # 2. OpenMP Close (E1c)
    e1c = pd.read_csv(RESULTS_DIR / "results_e1c_omp_cores_close.csv")
    e1c_p, e1c_kf = [], []
    for p in sorted(e1c["threads"].unique()):
        if p < 2 or p > 20: continue
        sub = e1c[e1c["threads"] == p]
        s = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        kf = calc_kf(s, p)
        e1c_p.append(p)
        e1c_kf.append(kf)
        data_rows.append({"series": "OpenMP close (E1c)", "x": p, "y": kf})
    ax.plot(e1c_p, e1c_kf, "s-", color="#1f77b4", lw=2.0, markersize=5, label="OpenMP close (E1c)")

    # 3. OpenMP Unbound (E1)
    e1 = pd.read_csv(RESULTS_DIR / "results_e1_omp_pure.csv")
    e1_p, e1_kf = [], []
    for p in sorted(e1["threads"].unique()):
        if p < 2 or p > 20: continue
        sub = e1[e1["threads"] == p]
        s = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        kf = calc_kf(s, p)
        e1_p.append(p)
        e1_kf.append(kf)
        data_rows.append({"series": "OpenMP unbound (E1)", "x": p, "y": kf})
    ax.plot(e1_p, e1_kf, "o--", color="#6baed6", lw=1.5, markersize=4, label="OpenMP unbound (E1)")

    # 4. Hybrid E3b
    e3b = pd.read_csv(RESULTS_DIR / "results_e3b_hybrid_map_core.csv")
    e3b_p, e3b_kf = [], []
    for p in sorted(e3b["physical_cores"].unique()):
        if p < 2 or p > 20: continue
        sub = e3b[e3b["physical_cores"] == p]
        s = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        kf = calc_kf(s, p)
        e3b_p.append(p)
        e3b_kf.append(kf)
        data_rows.append({"series": "Hybrid (E3b)", "x": p, "y": kf})
    ax.plot(e3b_p, e3b_kf, "d-", color="#ff7f0e", lw=2.0, markersize=6, label="Hybrid (E3b)")

    # 5. Hybrid E3
    e3 = pd.read_csv(RESULTS_DIR / "results_e3_hybrid.csv")
    e3_p, e3_kf = [], []
    for p in [16, 20]:
        sub = e3[(e3["ranks"] * e3["threads"] == p) & (e3["binding"].str.contains("slot"))]
        s = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        kf = calc_kf(s, p)
        e3_p.append(p)
        e3_kf.append(kf)
        data_rows.append({"series": "Hybrid (E3)", "x": p, "y": kf})
    ax.plot(e3_p, e3_kf, "*-", color="#d95f02", lw=1.8, markersize=8, label="Hybrid (E3)")

    # 6. gRPC Wall (E4)
    e4 = pd.read_csv(RESULTS_DIR / "results_e4_grpc.csv")
    e4_p, e4_kf = [], []
    for p in [2, 4, 6, 8, 10, 12, 16, 20]:
        sub = e4[e4["p_eff"] == p]
        s = float(np.median(T1_BASELINE / sub["time_seconds"].values))
        kf = calc_kf(s, p)
        e4_p.append(p)
        e4_kf.append(kf)
        data_rows.append({"series": "gRPC wall (E4)", "x": p, "y": kf})
    ax.plot(e4_p, e4_kf, "v--", color="#d62728", lw=1.6, markersize=5, label="gRPC wall (E4)")

    ax.set_xlim(1.5, 20.5)
    # G5: y-axis set to (-0.01, 0.25) so all points (max 0.1814) fit comfortably
    ax.set_ylim(-0.01, 0.25)
    ax.set_xticks(range(2, 21))
    ax.set_xlabel("Effective parallelism $p$")
    ax.set_ylabel(r"Karp-Flatt Metric $e(p) = \frac{1/S(p) - 1/p}{1 - 1/p}$")
    ax.set_title("Karp-Flatt Metric $e(p)$ (Algorithmic Overhead vs Contention)")
    ax.legend(loc="upper left", framealpha=0.9, fontsize=8.5)

    save_fig_and_data(fig, "fig_c_karp_flatt", data_rows, "fig07_karp_flatt")

# ==============================================================================
# FIG D (Fig. 11 in Report): Amdahl's Law Fit
# ==============================================================================
def plot_fig_d() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    data_rows = []

    p_dense = np.linspace(1, 20, 200)

    def amdahl(p: Any, fs: float) -> Any:
        return 1.0 / (fs + (1.0 - fs) / p)

    # 1. MPI Pure (E2b)
    e2b = pd.read_csv(RESULTS_DIR / "results_e2b_mpi_map_core.csv")
    e2b_fit_p = [1, 2, 3, 4]
    e2b_fit_s = [1.0]
    for p in [2, 3, 4]:
        sub = e2b[e2b["ranks"] == p]
        e2b_fit_s.append(float(np.median(T1_BASELINE / sub["time_seconds"].values)))
    popt_m, _ = curve_fit(amdahl, e2b_fit_p, e2b_fit_s, p0=[0.02], bounds=(0, 1))
    fs_mpi = popt_m[0]  # 0.028018

    # Bootstrap CI for MPI
    rng = np.random.default_rng(42)
    m_boot = []
    for _ in range(1000):
        s_b = [1.0]
        for p in [2, 3, 4]:
            t_samp = rng.choice(e2b[e2b["ranks"] == p]["time_seconds"].values, size=10, replace=True)
            s_b.append(T1_BASELINE / np.median(t_samp))
        popt_b, _ = curve_fit(amdahl, e2b_fit_p, s_b, p0=[0.02], bounds=(0, 1))
        m_boot.append(popt_b[0])
    fs_m_low, fs_m_high = float(np.percentile(m_boot, 2.5)), float(np.percentile(m_boot, 97.5))

    # All observed points for E2b
    e2b_all_p = sorted(e2b["ranks"].unique())
    e2b_obs_p, e2b_obs_s = [], []
    for p in e2b_all_p:
        if p > 20: continue
        med = float(np.median(T1_BASELINE / e2b[e2b["ranks"] == p]["time_seconds"].values))
        e2b_obs_p.append(p)
        e2b_obs_s.append(med)
        data_rows.append({"series": "MPI observed (E2b)", "x": p, "y": med})

    # Plot MPI fit points and observed
    ax.plot([p for p in e2b_obs_p if p <= 4], [s for p, s in zip(e2b_obs_p, e2b_obs_s) if p <= 4],
            "^", color="#2ca02c", markersize=7, label=r"MPI fit points ($p \leq 4$)")
    ax.plot([p for p in e2b_obs_p if p > 4], [s for p, s in zip(e2b_obs_p, e2b_obs_s) if p > 4],
            "d", color="#2ca02c", fillstyle="none", markersize=6, label=r"MPI observed ($p > 4$)")

    pred_mpi = amdahl(p_dense, fs_mpi)
    pred_m_low = amdahl(p_dense, fs_m_high)
    pred_m_high = amdahl(p_dense, fs_m_low)
    ax.plot(p_dense, pred_mpi, "-", color="#2ca02c", lw=2, label=f"MPI pure fit (E2b, $f_s={fs_mpi*100:.2f}\\%$)")
    ax.fill_between(p_dense, pred_m_low, pred_m_high, color="#2ca02c", alpha=0.15, label="MPI 95% bootstrap CI")

    # 2. OpenMP Close (E1c)
    e1c = pd.read_csv(RESULTS_DIR / "results_e1c_omp_cores_close.csv")
    e1c_fit_p = [1, 2, 3, 4]
    e1c_fit_s = [1.0]
    for p in [2, 3, 4]:
        sub = e1c[e1c["threads"] == p]
        e1c_fit_s.append(float(np.median(T1_BASELINE / sub["time_seconds"].values)))
    popt_o, _ = curve_fit(amdahl, e1c_fit_p, e1c_fit_s, p0=[0.02], bounds=(0, 1))
    fs_omp = popt_o[0]  # 0.044816

    o_boot = []
    for _ in range(1000):
        s_b = [1.0]
        for p in [2, 3, 4]:
            t_samp = rng.choice(e1c[e1c["threads"] == p]["time_seconds"].values, size=10, replace=True)
            s_b.append(T1_BASELINE / np.median(t_samp))
        popt_b, _ = curve_fit(amdahl, e1c_fit_p, s_b, p0=[0.02], bounds=(0, 1))
        o_boot.append(popt_b[0])
    fs_o_low, fs_o_high = float(np.percentile(o_boot, 2.5)), float(np.percentile(o_boot, 97.5))

    e1c_all_p = sorted(e1c["threads"].unique())
    e1c_obs_p, e1c_obs_s = [], []
    for p in e1c_all_p:
        if p > 20: continue
        med = float(np.median(T1_BASELINE / e1c[e1c["threads"] == p]["time_seconds"].values))
        e1c_obs_p.append(p)
        e1c_obs_s.append(med)
        data_rows.append({"series": "OpenMP observed (E1c)", "x": p, "y": med})

    ax.plot([p for p in e1c_obs_p if p <= 4], [s for p, s in zip(e1c_obs_p, e1c_obs_s) if p <= 4],
            "o", color="#1f77b4", markersize=7, label=r"OpenMP fit points ($p \leq 4$)")
    ax.plot([p for p in e1c_obs_p if p > 4], [s for p, s in zip(e1c_obs_p, e1c_obs_s) if p > 4],
            "s", color="#1f77b4", fillstyle="none", markersize=6, label=r"OpenMP observed ($p > 4$)")

    pred_omp = amdahl(p_dense, fs_omp)
    pred_o_low = amdahl(p_dense, fs_o_high)
    pred_o_high = amdahl(p_dense, fs_o_low)
    ax.plot(p_dense, pred_omp, "-", color="#1f77b4", lw=2, label=f"OpenMP close fit (E1c, $f_s={fs_omp*100:.2f}\\%$)")
    ax.fill_between(p_dense, pred_o_low, pred_o_high, color="#1f77b4", alpha=0.15, label="OpenMP 95% bootstrap CI")

    # Linear ideal
    ax.plot(p_dense, p_dense, "k--", alpha=0.4, label="Ideal linear")

    ax.set_xlim(0.5, 20.5)
    ax.set_ylim(0, 21)
    ax.set_xticks(range(1, 21))
    ax.set_xlabel("Effective parallelism $p$")
    ax.set_ylabel("Speedup $S(p)$")
    ax.set_title(r"Amdahl's Law Fit on $p \leq 4$ and Projection for $p > 4$ (E2b and E1c)")
    ax.legend(loc="upper left", framealpha=0.9, fontsize=8.0)

    save_fig_and_data(fig, "fig_d_amdahl_fit", data_rows, "fig11_amdahl_fit")

# ==============================================================================
# FIG E: Hybrid Heatmap
# ==============================================================================
def plot_fig_e() -> None:
    e3 = pd.read_csv(RESULTS_DIR / "results_e3_hybrid.csv")
    d3 = e3[e3["model"] == "hybrid_mpi_omp"].copy()

    pivot = d3.groupby(["ranks", "threads"])["throughput"].median().unstack()

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    cax = ax.imshow(pivot.values, cmap="YlGnBu", aspect="auto", origin="lower")

    ranks_list = list(pivot.index)
    threads_list = list(pivot.columns)

    ax.set_xticks(range(len(threads_list)))
    ax.set_xticklabels([f"T={t}" for t in threads_list])
    ax.set_yticks(range(len(ranks_list)))
    ax.set_yticklabels([f"R={r}" for r in ranks_list])

    data_rows = []
    for i, r in enumerate(ranks_list):
        for j, t in enumerate(threads_list):
            val = pivot.iloc[i, j]
            if np.isnan(val):
                continue
            p_eff = r * t
            cell_text = f"{val/1000:.1f}k\n(p={p_eff})"
            if t in [3, 5]:
                cell_text += "\n★ SMT"
            color = "white" if val > pivot.values[~np.isnan(pivot.values)].mean() else "black"
            ax.text(j, i, cell_text, ha="center", va="center", color=color, fontsize=8.5, fontweight="bold")
            data_rows.append({"ranks": r, "threads": t, "p_eff": p_eff, "throughput_ksig": float(val / 1000.0)})

    cbar = fig.colorbar(cax, ax=ax)
    cbar.set_label("Throughput (signatures/sec)")

    ax.set_xlabel("Threads per rank ($T$)")
    ax.set_ylabel("MPI Ranks ($R$)")
    ax.set_title("Hybrid MPI+OpenMP Performance Grid ($R \\times T$)\n(★ denotes odd $T=3,5$ sharing core via SMT)")

    save_fig_and_data(fig, "fig_e_hybrid_heatmap", data_rows, "fig_e_hybrid_heatmap")

# ==============================================================================
# FIG F (Fig. 12 in Report): gRPC vs Native MPI Pure
# ==============================================================================
def plot_fig_f() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    data_rows = []

    # 1. MPI pure (E2b)
    e2b = pd.read_csv(RESULTS_DIR / "results_e2b_mpi_map_core.csv")
    e2b_p, e2b_th = [], []
    for p in sorted(e2b["ranks"].unique()):
        sub = e2b[e2b["ranks"] == p]
        th = float(np.median(sub["throughput"].values) / 1000.0)
        e2b_p.append(p)
        e2b_th.append(th)
        data_rows.append({"series": "MPI pure (E2b)", "x": p, "y": th})
    ax.plot(e2b_p, e2b_th, "^-", color="#2ca02c", lw=2.2, markersize=6, label="MPI pure native (E2b, core binding)")

    # 2. gRPC Isolated (E4) - Worker compute only and End-to-end wall clock
    e4 = pd.read_csv(RESULTS_DIR / "results_e4_grpc.csv")
    e4_p, e4_comp, e4_wall = [], [], []
    for p in sorted(e4["p_eff"].unique()):
        sub = e4[e4["p_eff"] == p]
        # compute throughput = 20,000 / verify_s
        th_c = float(np.median(20000.0 / sub["verify_s"].values) / 1000.0)
        # wall throughput = 20,000 / time_seconds (or median of throughput)
        th_w = float(np.median(20000.0 / sub["time_seconds"].values) / 1000.0)
        e4_p.append(p)
        e4_comp.append(th_c)
        e4_wall.append(th_w)
        data_rows.append({"series": "gRPC compute (E4)", "x": p, "y": th_c})
        data_rows.append({"series": "gRPC wall (E4)", "x": p, "y": th_w})

    ax.plot(e4_p, e4_comp, "s--", color="#ff7f0e", lw=2.0, markersize=5, label=r"gRPC worker compute only (E4, $S_{\mathrm{compute}}$)")
    ax.plot(e4_p, e4_wall, "v-", color="#d62728", lw=2.0, markersize=6, label=r"gRPC end-to-end wall-clock (E4, $S_{\mathrm{wall}}$)")

    # Oversubscription line at p=20
    ax.axvline(20, color="gray", linestyle=":", alpha=0.7)
    ax.text(20.5, 120, "Host core limit (20)\nOversubscription ->", fontsize=8.5, color="gray", va="center")

    ax.set_xlim(0, 33)
    ax.set_ylim(0, 200)
    ax.set_xlabel("Number of logical workers / nodes ($p$)")
    ax.set_ylabel("Throughput (k sig/s)")
    ax.set_title("Containerized gRPC (E4) vs Native MPI Pure (E2b)")
    ax.legend(loc="upper left", framealpha=0.9)

    save_fig_and_data(fig, "fig_f_grpc_vs_mpi", data_rows, "fig12_grpc_vs_mpi")

# ==============================================================================
# FIG G (Fig. 8 in Report): OpenMP Schedules at T=16
# ==============================================================================
def plot_fig_g() -> None:
    e5 = pd.read_csv(RESULTS_DIR / "results_e5_schedule.csv")
    d16 = e5[e5["threads"] == 16].copy()

    # Aggregate median throughput per schedule clause
    sched_order = ["static", "guided", "dynamic,16"]
    th_vals = []
    data_rows = []
    for s in sched_order:
        sub = d16[d16["schedule"] == s]
        th = float(np.median(sub["throughput"].values) / 1000.0)
        th_vals.append(th)
        data_rows.append({"series": "OpenMP schedule (E5)", "schedule": s, "throughput_ksig": th})

    fig, ax = plt.subplots(figsize=(8.0, 4.0))

    y_pos = np.arange(len(sched_order))
    colors = ["#1f77b4", "#2ca02c", "#ff7f0e"]

    bars = ax.barh(y_pos, th_vals, color=colors, height=0.55, alpha=0.85, edgecolor="black", lw=0.6)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sched_order, fontsize=10, fontweight="bold")

    # Annotate bar values in ksig/s as in §7.3
    for i, val in enumerate(th_vals):
        ax.text(val + 2.0, i, f"{val:.1f} ksig/s", va="center", fontsize=9, fontweight="bold")

    ax.set_xlim(0, 205)
    ax.set_xlabel("Throughput (k sig/s)")
    ax.set_ylabel("OpenMP Schedule Clause")
    ax.set_title("OpenMP Scheduling Overhead Comparison ($T=16$, E5)")

    # H3: Redundant legend removed as y-axis tick labels identify each bar and values are directly annotated without occlusion

    save_fig_and_data(fig, "fig_g_openmp_schedules", data_rows, "fig08_openmp_schedules")

# ==============================================================================
# FIG H (Fig. 9 in Report): Dynamic Task-based Scaling
# ==============================================================================
def plot_fig_h() -> None:
    e6 = pd.read_csv(RESULTS_DIR / "results_e6_taskbased.csv")

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    data_rows = []

    # 1. OpenMP taskloop across grain sizes
    d_omp = e6[e6["model"] == "omp_taskloop"].copy()
    # Map schedules to grain size
    d_omp["grain"] = d_omp["schedule"].str.extract(r"taskloop_grain_(\d+)").astype(int)

    omp_colors = {10: "#9467bd", 50: "#1f77b4", 100: "#2ca02c", 500: "#d62728"}
    for grain in [10, 50, 100, 500]:
        sub_g = d_omp[d_omp["grain"] == grain]
        if sub_g.empty: continue
        t_vals, th_vals = [], []
        for t in sorted(sub_g["threads"].unique()):
            th = float(np.median(sub_g[sub_g["threads"] == t]["throughput"].values) / 1000.0)
            t_vals.append(t)
            th_vals.append(th)
            data_rows.append({"series": f"OpenMP taskloop (grain={grain})", "x": t, "y": th})
        ax.plot(t_vals, th_vals, "o-", color=omp_colors.get(grain, "#333333"),
                lw=1.8, markersize=5, label=f"OpenMP taskloop (grain={grain})")

    # 2. MPI dynamic (master-worker)
    d_dyn = e6[e6["model"] == "mpi_dynamic"].copy()
    d_dyn["chunk"] = d_dyn["schedule"].str.extract(r"dynamic_chunk_(\d+)_workers").astype(int)

    # Chunk 100 across ranks 4..12
    sub_100 = d_dyn[d_dyn["chunk"] == 100]
    r_vals, th_vals = [], []
    for r in sorted(sub_100["ranks"].unique()):
        th = float(np.median(sub_100[sub_100["ranks"] == r]["throughput"].values) / 1000.0)
        r_vals.append(r)
        th_vals.append(th)
        data_rows.append({"series": "MPI dynamic (chunk=100)", "x": r, "y": th})
    ax.plot(r_vals, th_vals, "s--", color="#ff7f0e", lw=2.0, markersize=6, label=r"MPI dynamic (chunk=100, $p=R$)")

    # Chunks 25 and 500 at rank 8
    for chunk, col in [(25, "#8c564b"), (500, "#e377c2")]:
        sub_c = d_dyn[d_dyn["chunk"] == chunk]
        if not sub_c.empty:
            th = float(np.median(sub_c["throughput"].values) / 1000.0)
            data_rows.append({"series": f"MPI dynamic (chunk={chunk})", "x": 8, "y": th})
            ax.plot([8], [th], "s", color=col, markersize=8, label=f"MPI dynamic (chunk={chunk}, R=8)")

    # G4: Ensure entire range p=1..21 is comfortably framed and not cut off!
    ax.set_xlim(0.5, 21.5)
    ax.set_ylim(0, 205)
    ax.set_xticks([1, 4, 8, 12, 16, 20])
    ax.set_xlabel("Workers / Ranks ($p$)")
    ax.set_ylabel("Throughput (k sig/s)")
    ax.set_title("Dynamic Task-based Scaling: OpenMP Taskloop vs MPI Dynamic")
    ax.legend(loc="upper left", framealpha=0.9, fontsize=8.5)

    save_fig_and_data(fig, "fig_h_taskbased_scaling", data_rows, "fig09_taskbased_scaling")

# ==============================================================================
# FIG I: P-cores vs ALL Cores
# ==============================================================================
def plot_fig_i() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    data_rows = []

    # P-cores OpenMP (E8)
    e8 = pd.read_csv(RESULTS_DIR / "results_e8_pcores.csv")
    e8_omp = e8[e8["model"] == "omp_pure_pcores"]
    t_vals, s_vals = [], []
    for t in sorted(e8_omp["threads"].unique()):
        s = float(np.median(T1_BASELINE / e8_omp[e8_omp["threads"] == t]["time_seconds"].values))
        t_vals.append(t)
        s_vals.append(s)
        data_rows.append({"series": "OpenMP (P-cores only, taskset 0-11)", "x": t, "y": s})
    ax.plot(t_vals, s_vals, "o-", color="#1f77b4", lw=2, markersize=6, label="OpenMP (P-cores only, taskset 0-11)")

    # All cores OpenMP (E1c)
    e1c = pd.read_csv(RESULTS_DIR / "results_e1c_omp_cores_close.csv")
    t_vals, s_vals = [], []
    for t in sorted(e1c["threads"].unique()):
        if t > 12: continue
        s = float(np.median(T1_BASELINE / e1c[e1c["threads"] == t]["time_seconds"].values))
        t_vals.append(t)
        s_vals.append(s)
        data_rows.append({"series": "OpenMP (All cores, close)", "x": t, "y": s})
    ax.plot(t_vals, s_vals, "o--", color="#6baed6", lw=1.8, markersize=5, label="OpenMP (All cores, close)")

    # P-cores MPI (E8b)
    e8b = pd.read_csv(RESULTS_DIR / "results_e8b_mpi_pcores_map_core.csv")
    r_vals, s_vals = [], []
    for r in sorted(e8b["ranks"].unique()):
        s = float(np.median(T1_BASELINE / e8b[e8b["ranks"] == r]["time_seconds"].values))
        r_vals.append(r)
        s_vals.append(s)
        data_rows.append({"series": "MPI pure (P-cores only, core binding)", "x": r, "y": s})
    ax.plot(r_vals, s_vals, "^-", color="#2ca02c", lw=2, markersize=6, label="MPI pure (P-cores only, core binding)")

    # All cores MPI (E2b)
    e2b = pd.read_csv(RESULTS_DIR / "results_e2b_mpi_map_core.csv")
    r_vals, s_vals = [], []
    for r in sorted(e2b["ranks"].unique()):
        if r > 12: continue
        s = float(np.median(T1_BASELINE / e2b[e2b["ranks"] == r]["time_seconds"].values))
        r_vals.append(r)
        s_vals.append(s)
        data_rows.append({"series": "MPI pure (All cores, core binding)", "x": r, "y": s})
    ax.plot(r_vals, s_vals, "^--", color="#74c476", lw=1.8, markersize=5, label="MPI pure (All cores, core binding)")

    p_arr = np.arange(1, 13)
    ax.plot(p_arr, p_arr, "k--", alpha=0.4, label="Ideal linear")

    ax.axvline(6, color="purple", linestyle=":", alpha=0.7)
    ax.text(6.1, 2.5, "P-core physical limit (6)\n-> SMT kicks in", fontsize=8.5, color="purple")

    ax.set_xlim(0.5, 12.5)
    ax.set_ylim(0, 13)
    ax.set_xticks(range(1, 13))
    ax.set_xlabel("Effective parallelism $p$")
    ax.set_ylabel("Speedup $S(p)$")
    ax.set_title("Heterogeneity Impact: P-cores (0-11) vs All Cores (E8 vs E1c/E2b)")
    ax.legend(loc="upper left", framealpha=0.9)

    save_fig_and_data(fig, "fig_i_pcores_vs_all", data_rows, "fig_i_pcores_vs_all")

def main():
    parser = argparse.ArgumentParser(description="M13 Publication Graph Generator")
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
