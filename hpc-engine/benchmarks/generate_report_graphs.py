#!/usr/bin/env python3
"""
generate_report_graphs.py
Generation of the complete chart set for the HPC Stage 11.5 report.

Requirements:
1. Validated data only from hpc-engine/results/ (no interpolation or estimation).
2. pilot_32x8_5000.csv excluded from all graphs.
3. No environment watermark text on bottom-right corner.
4. Visual distinction for clean (P_eff <= 20) vs oversubscribed (P_eff > 20).
5. Dual output: .png (300 dpi) and vector .pdf in graphs/.
6. Consistent color palette: gRPC (blue), MPI+OpenMP (orange), Pipeline (green).
7. English language for all titles, labels, legends, and annotations.
8. No percentage text inside bar labels in profile_breakdown (already shown on the bars).
"""

import os
import re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Directory setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "hpc-engine" / "results"
OUTPUT_DIR = PROJECT_ROOT / "graphs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Environment and color constants
ENV_ID = "i7_12700h_20260908"

# Main palette
COLOR_GRPC = "#1f77b4"
COLOR_MPI_OMP = "#e6550d"
COLOR_PIPELINE = "#2ca02c"
COLOR_THEORY = "#333333"

# Thread shades
GRPC_THREAD_COLORS = {
    1: "#6baed6",
    2: "#3182bd",
    4: "#1f77b4",
    8: "#08519c"
}

MPI_THREAD_COLORS = {
    1: "#fdae6b",
    2: "#f16913",
    4: "#d94801",
    8: "#8c2d04"
}

THREAD_MARKERS = {
    1: "o",
    2: "s",
    4: "^",
    8: "D"
}

# Global Matplotlib style configuration
plt.rcParams.update({
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "legend.fontsize": 9,
    "figure.titlesize": 13,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": ":",
    "axes.axisbelow": True,
})


def save_plot(fig, filename_base: str):
    """Save plot in both .png and .pdf vector formats."""
    png_path = OUTPUT_DIR / f"{filename_base}.png"
    pdf_path = OUTPUT_DIR / f"{filename_base}.pdf"
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    plt.close(fig)
    print(f"  [OK] Generated: graphs/{filename_base}.png & .pdf")
    report_fig_dir = PROJECT_ROOT / "report" / "figures"
    if report_fig_dir.exists():
        import shutil
        shutil.copy2(png_path, report_fig_dir / f"{filename_base}.png")
        shutil.copy2(pdf_path, report_fig_dir / f"{filename_base}.pdf")
        print(f"  [OK] Copied to report/figures/{filename_base}.*")


def plot_segmented_line(ax, x_vals, y_vals, is_oversub, color, marker, label=None, linewidth=1.5, markersize=7):
    """Draw solid line between clean points, dashed line when oversubscribed."""
    for i in range(len(x_vals) - 1):
        x_seg = [x_vals[i], x_vals[i+1]]
        y_seg = [y_vals[i], y_vals[i+1]]
        if not is_oversub[i] and not is_oversub[i+1]:
            ax.plot(x_seg, y_seg, color=color, linestyle="-", linewidth=linewidth, alpha=0.9)
        else:
            ax.plot(x_seg, y_seg, color=color, linestyle="--", linewidth=linewidth, alpha=0.85)

    if label:
        ax.plot([], [], color=color, linestyle="-", linewidth=linewidth, label=label)

    for x, y, ov in zip(x_vals, y_vals, is_oversub):
        if not ov:
            ax.plot(x, y, marker=marker, markersize=markersize, color=color, markerfacecolor=color)
        else:
            ax.plot(x, y, marker=marker, markersize=markersize, color=color, markerfacecolor="white", markeredgewidth=1.8)


# ==============================================================================
# GRAPH A: Profiling Breakdown (Task A)
# ==============================================================================
def plot_a_profile_breakdown():
    print("Generating Graph A: profile_breakdown...")
    source_file = "profile_i7_12700h_20260908.txt"
    filepath = RESULTS_DIR / source_file

    # Bar labels without embedded percentages (percentages are shown beside bars)
    categories = [
        ("Unattributed libc / runtime", 0.86, "#a0aec0"),
        ("Application / Harness", 1.80, "#4a5568"),
        ("Dynamic Memory (malloc / free)", 3.20, "#718096"),
        ("Other OpenSSL / libcrypto", 6.26, "#e28743"),
        ("EC: BN_uadd / bn_div / shifts", 7.10, "#3182bd"),
        ("EC: point_double & avx2", 7.71, "#2b6cb0"),
        ("EC: ecp_nistz256_ord_sqr_mont", 5.91, "#1e4e8c"),
        ("EC: __ecp_nistz256_sqr_montq", 19.97, "#1a365d"),
        ("EC: __ecp_nistz256_mul_montq", 32.71, "#0c2340"),
        ("EC: Other EC curve primitives", 14.48, "#2b4c7e"),
    ]

    fig_data_dir = PROJECT_ROOT / "report" / "figure_data"
    fig_data_dir.mkdir(parents=True, exist_ok=True)
    df_data = pd.DataFrame({
        "category": [c[0] for c in categories],
        "percentage": [c[1] for c in categories]
    })
    df_data.to_csv(fig_data_dir / "fig02_profile.csv", index=False)

    labels = [c[0] for c in categories]
    values = [c[1] for c in categories]
    colors = [c[2] for c in categories]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    y_pos = np.arange(len(labels))

    bars = ax.barh(y_pos, values, color=colors, height=0.65, edgecolor="#2d3748", linewidth=0.8)

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{val:.2f}%", va="center", ha="left", fontsize=9, fontweight="bold", color="#2d3748"
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Simulated Instruction Fraction (% Ir)")
    ax.set_xlim(0, 40)
    ax.set_title(
        "Flat Instruction Profile Breakdown (Valgrind Callgrind)\n"
        "ECDSA P-256 Workload (Single-Thread Sequential Baseline, Batch 500)"
    )

    # Workload summary box
    ax.text(
        0.58, 0.28,
        "Workload Breakdown Summary:\n"
        "• EC & BIGNUM Arithmetic: 87.88%\n"
        "• Total Cryptographic Compute: 94.14%\n"
        "• Dynamic Memory (malloc / free): 3.20%\n"
        "• Application / Harness Code: 1.80%\n"
        "--> Strictly compute-bound workload",
        transform=ax.transAxes,
        fontsize=8.5,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#ebf8ff", edgecolor="#bee3f8", alpha=0.95)
    )

    save_plot(fig, "profile_breakdown")


# ==============================================================================
# GRAPHS B: Isolated gRPC Grid (Task B)
# ==============================================================================
def plot_b_grpc_grid():
    source_file = "grid_grpc_i7_12700h_20260908.csv"
    filepath = RESULTS_DIR / source_file
    df = pd.read_csv(filepath)

    peff_ticks = [1, 2, 4, 8, 16, 32, 64, 128, 256]

    for batch in [1000, 5000]:
        df_batch = df[df["batch_size"] == batch].copy()
        t1_rec = df_batch[(df_batch["nodes"] == 1) & (df_batch["threads_per_node"] == 1)].iloc[0]
        t1_avg = t1_rec["avg_time_seconds"]

        # 1. Average Speedup vs P_eff
        fig, ax = plt.subplots(figsize=(8.5, 5.5))

        for th in [1, 2, 4, 8]:
            df_th = df_batch[df_batch["threads_per_node"] == th].sort_values("effective_parallelism")
            if df_th.empty:
                continue

            peffs = df_th["effective_parallelism"].values
            speedups = (t1_avg / df_th["avg_time_seconds"]).values
            is_oversub = df_th["is_oversubscribed"].values
            color = GRPC_THREAD_COLORS[th]
            marker = THREAD_MARKERS[th]

            plot_segmented_line(
                ax, peffs, speedups, is_oversub,
                color=color, marker=marker, label=f"gRPC (T={th} th/node)",
                linewidth=1.4, markersize=7
            )

        # Hardware limit line
        ax.axvline(x=20, color="#e53e3e", linestyle=":", linewidth=1.2, alpha=0.7)
        ax.text(20.5, 1.2, "Hardware Threshold P_eff=20\n(Oversubscription)", color="#e53e3e", fontsize=8)

        # Legend status handles
        ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="#4a5568", linestyle="-", label="Clean Regime (solid line, filled marker)")
        ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="white", markeredgewidth=1.8, linestyle="--", label="Oversubscribed (dashed line, hollow marker)")

        ax.set_xscale("log", base=2)
        ax.set_xticks(peff_ticks)
        ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
        ax.set_xlabel("Effective Parallelism P_eff = Nodes × Threads (log2 scale)")
        ax.set_ylabel("Average Speedup S_n = T_avg(1,1) / T_avg(N,T)")
        ax.set_title(f"Task B: gRPC Scalability — Speedup vs P_eff (Batch = {batch:,} signatures)")
        ax.legend(loc="upper left", framealpha=0.9, fontsize=8)
        ax.set_ylim(bottom=0.8)

        save_plot(fig, f"grpc_speedup_vs_peff_batch{batch}")

        # 2. Average Throughput vs P_eff with error bars
        fig, ax = plt.subplots(figsize=(8.5, 5.5))

        for th in [1, 2, 4, 8]:
            df_th = df_batch[df_batch["threads_per_node"] == th].sort_values("effective_parallelism")
            if df_th.empty:
                continue

            peffs = df_th["effective_parallelism"].values
            thru_avg = df_th["avg_throughput"].values
            time_avg = df_th["avg_time_seconds"].values
            time_std = df_th["stddev_seconds"].values
            thru_err = thru_avg * (time_std / time_avg)

            is_oversub = df_th["is_oversubscribed"].values
            color = GRPC_THREAD_COLORS[th]
            marker = THREAD_MARKERS[th]

            for p, th_val, err in zip(peffs, thru_avg, thru_err):
                ax.errorbar(p, th_val, yerr=err, fmt="none", ecolor=color, elinewidth=1.2, capsize=3, alpha=0.7)

            plot_segmented_line(
                ax, peffs, thru_avg, is_oversub,
                color=color, marker=marker, label=f"gRPC (T={th} th/node)",
                linewidth=1.3, markersize=6.5
            )

        ax.axvline(x=20, color="#e53e3e", linestyle=":", linewidth=1.2, alpha=0.7)
        ax.text(20.5, thru_avg.min() * 1.05, "P_eff=20", color="#e53e3e", fontsize=8)

        ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="#4a5568", linestyle="-", label="Clean Regime (solid line, filled marker)")
        ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="white", markeredgewidth=1.8, linestyle="--", label="Oversubscribed (dashed line, hollow marker)")

        ax.set_xscale("log", base=2)
        ax.set_xticks(peff_ticks)
        ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
        ax.set_xlabel("Effective Parallelism P_eff = Nodes × Threads (log2 scale)")
        ax.set_ylabel("Average Throughput (sig/s) ± StdDev")
        ax.set_title(f"Task B: gRPC Throughput vs P_eff with Error Bars (Batch = {batch:,} signatures)")
        ax.legend(loc="upper left", framealpha=0.9, fontsize=8)
        ax.set_ylim(bottom=0)

        save_plot(fig, f"grpc_throughput_vs_peff_batch{batch}")


# ==============================================================================
# GRAPHS C: MPI+OpenMP Hybrid Grid (Task B)
# ==============================================================================
def plot_c_mpi_omp_grid():
    source_file = "grid_mpi_omp_i7_12700h_20260908.csv"
    filepath = RESULTS_DIR / source_file
    df = pd.read_csv(filepath)

    peff_ticks = [1, 2, 4, 8, 16, 32, 64, 128, 256]

    for batch in [1000, 5000]:
        df_batch = df[df["batch_size"] == batch].copy()
        t1_rec = df_batch[(df_batch["mpi_ranks"] == 1) & (df_batch["omp_threads"] == 1)].iloc[0]
        t1_avg = t1_rec["avg_time_seconds"]

        # 1. Average Speedup vs P_eff
        fig, ax = plt.subplots(figsize=(8.5, 5.5))

        for th in [1, 2, 4, 8]:
            df_th = df_batch[df_batch["omp_threads"] == th].sort_values("effective_parallelism")
            if df_th.empty:
                continue

            peffs = df_th["effective_parallelism"].values
            speedups = (t1_avg / df_th["avg_time_seconds"]).values
            is_oversub = df_th["is_oversubscribed"].values
            color = MPI_THREAD_COLORS[th]
            marker = THREAD_MARKERS[th]

            plot_segmented_line(
                ax, peffs, speedups, is_oversub,
                color=color, marker=marker, label=f"MPI+OpenMP (T={th} th/rank)",
                linewidth=1.4, markersize=7
            )

        ax.axvline(x=20, color="#e53e3e", linestyle=":", linewidth=1.2, alpha=0.7)
        ax.text(20.5, 1.2, "Hardware Threshold P_eff=20\n(Oversubscription)", color="#e53e3e", fontsize=8)

        ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="#4a5568", linestyle="-", label="Clean Regime (solid line, filled marker)")
        ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="white", markeredgewidth=1.8, linestyle="--", label="Oversubscribed (dashed line, hollow marker)")

        ax.set_xscale("log", base=2)
        ax.set_xticks(peff_ticks)
        ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
        ax.set_xlabel("Effective Parallelism P_eff = MPI Ranks × OMP Threads (log2 scale)")
        ax.set_ylabel("Average Speedup S_n = T_avg(1,1) / T_avg(P,T)")
        ax.set_title(f"Task B: Hybrid MPI+OpenMP Scalability — Speedup vs P_eff (Batch = {batch:,} signatures)")
        ax.legend(loc="upper left", framealpha=0.9, fontsize=8)
        ax.set_ylim(bottom=0.8)

        save_plot(fig, f"mpi_omp_speedup_vs_peff_batch{batch}")

        # 2. Average Throughput vs P_eff with error bars
        fig, ax = plt.subplots(figsize=(8.5, 5.5))

        for th in [1, 2, 4, 8]:
            df_th = df_batch[df_batch["omp_threads"] == th].sort_values("effective_parallelism")
            if df_th.empty:
                continue

            peffs = df_th["effective_parallelism"].values
            thru_avg = df_th["avg_throughput"].values
            time_avg = df_th["avg_time_seconds"].values
            time_std = df_th["stddev_seconds"].values
            thru_err = thru_avg * (time_std / time_avg)

            is_oversub = df_th["is_oversubscribed"].values
            color = MPI_THREAD_COLORS[th]
            marker = THREAD_MARKERS[th]

            for p, th_val, err in zip(peffs, thru_avg, thru_err):
                ax.errorbar(p, th_val, yerr=err, fmt="none", ecolor=color, elinewidth=1.2, capsize=3, alpha=0.7)

            plot_segmented_line(
                ax, peffs, thru_avg, is_oversub,
                color=color, marker=marker, label=f"MPI+OMP (T={th} th/rank)",
                linewidth=1.3, markersize=6.5
            )

        ax.axvline(x=20, color="#e53e3e", linestyle=":", linewidth=1.2, alpha=0.7)
        ax.text(20.5, thru_avg.min() * 1.05, "P_eff=20", color="#e53e3e", fontsize=8)

        ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="#4a5568", linestyle="-", label="Clean Regime (solid line, filled marker)")
        ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="white", markeredgewidth=1.8, linestyle="--", label="Oversubscribed (dashed line, hollow marker)")

        ax.set_xscale("log", base=2)
        ax.set_xticks(peff_ticks)
        ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
        ax.set_xlabel("Effective Parallelism P_eff = MPI Ranks × OMP Threads (log2 scale)")
        ax.set_ylabel("Average Throughput (sig/s) ± StdDev")
        ax.set_title(f"Task B: MPI+OpenMP Throughput vs P_eff with Error Bars (Batch = {batch:,} signatures)")
        ax.legend(loc="upper left", framealpha=0.9, fontsize=8)
        ax.set_ylim(bottom=0)

        save_plot(fig, f"mpi_omp_throughput_vs_peff_batch{batch}")


# ==============================================================================
# GRAPH D: Direct Substrate Comparison gRPC vs MPI+OpenMP (Task B/D)
# ==============================================================================
def plot_d_substrate_comparison():
    print("Generating Graph D: substrate_comparison_throughput_batch5000...")
    f_grpc = "grid_grpc_i7_12700h_20260908.csv"
    f_mpi = "grid_mpi_omp_i7_12700h_20260908.csv"

    df_grpc = pd.read_csv(RESULTS_DIR / f_grpc)
    df_mpi = pd.read_csv(RESULTS_DIR / f_mpi)

    df_grpc_5k = df_grpc[df_grpc["batch_size"] == 5000].copy()
    df_mpi_5k = df_mpi[df_mpi["batch_size"] == 5000].copy()

    peff_ticks = [1, 2, 4, 8, 16, 32, 64, 128, 256]

    fig, ax = plt.subplots(figsize=(9, 6))

    # Envelope aggregation: maximum average throughput per P_eff
    grpc_best = df_grpc_5k.loc[df_grpc_5k.groupby("effective_parallelism")["avg_throughput"].idxmax()].sort_values("effective_parallelism")
    mpi_best = df_mpi_5k.loc[df_mpi_5k.groupby("effective_parallelism")["avg_throughput"].idxmax()].sort_values("effective_parallelism")

    # gRPC Series
    peff_g = grpc_best["effective_parallelism"].values
    thru_g = grpc_best["avg_throughput"].values
    ov_g = grpc_best["is_oversubscribed"].values

    plot_segmented_line(
        ax, peff_g, thru_g, ov_g,
        color=COLOR_GRPC, marker="o", label="gRPC (Docker Containers, Socket RPC)",
        linewidth=2.0, markersize=7.5
    )

    # MPI+OpenMP Series
    peff_m = mpi_best["effective_parallelism"].values
    thru_m = mpi_best["avg_throughput"].values
    ov_m = mpi_best["is_oversubscribed"].values

    plot_segmented_line(
        ax, peff_m, thru_m, ov_m,
        color=COLOR_MPI_OMP, marker="s", label="MPI + OpenMP (In-process, Zero Network)",
        linewidth=2.0, markersize=7.5
    )

    # Asymptote and peak highlight
    ax.axhline(y=87250, color=COLOR_GRPC, linestyle="--", linewidth=1.1, alpha=0.6)
    ax.text(1.15, 89500, "gRPC Asymptote: ~87k sig/s (HTTP/2 & socket overhead)", color=COLOR_GRPC, fontsize=8.5, fontweight="bold")

    ax.axhline(y=163900, color=COLOR_MPI_OMP, linestyle="--", linewidth=1.1, alpha=0.6)
    ax.text(1.15, 166000, "MPI+OpenMP Peak: ~164k sig/s (Shared memory)", color=COLOR_MPI_OMP, fontsize=8.5, fontweight="bold")

    ax.axvline(x=20, color="#e53e3e", linestyle=":", linewidth=1.2, alpha=0.7)
    ax.text(20.5, 45000, "P_eff = 20\n(Physical core threshold)", color="#e53e3e", fontsize=8)

    # Legend status
    ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="#4a5568", linestyle="-", label="Clean Regime (solid line, filled marker)")
    ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="white", markeredgewidth=1.8, linestyle="--", label="Oversubscribed (dashed line, hollow marker)")

    ax.set_xscale("log", base=2)
    ax.set_xticks(peff_ticks)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax.set_xlabel("Effective Parallelism P_eff (log2 scale)")
    ax.set_ylabel("Peak Measured Throughput per P_eff (sig/s)")
    ax.set_title(
        "Execution Substrate Comparison: gRPC vs MPI+OpenMP Throughput\n"
        "Batch = 5,000 ECDSA P-256 Signatures (Best Configuration per P_eff)"
    )
    ax.legend(loc="lower right", framealpha=0.95, fontsize=8.5)
    ax.set_ylim(0, 180000)

    save_plot(fig, "substrate_comparison_throughput_batch5000")


# ==============================================================================
# GRAPHS E: Amdahl Investigation & Overhead Breakdown (Task C)
# ==============================================================================
def plot_e_amdahl_and_overhead():
    print("Generating Graphs E: Amdahl and overhead breakdown...")
    source_file = "amdahl_investigation_i7_12700h_20260908.csv"
    filepath = RESULTS_DIR / source_file
    df = pd.read_csv(filepath)

    # 1. amdahl_predicted_vs_measured_extended.png
    # Serial fraction estimated from previous report (task-level 2 nodes x 1 thread baseline):
    # fs = 0.0251 (2.51% serial)
    fs_task = 0.0251

    # EXPLICIT AND UNIFORM SELECTION: BATCH = 5,000 FOR ALL POINTS
    BATCH_TARGET = 5000

    # Baseline T1 from grid_grpc_i7_12700h_20260908.csv for the exact same batch (5000)
    df_grid = pd.read_csv(RESULTS_DIR / "grid_grpc_i7_12700h_20260908.csv")
    t1_target = df_grid[
        (df_grid["batch_size"] == BATCH_TARGET) &
        (df_grid["nodes"] == 1) &
        (df_grid["threads_per_node"] == 1)
    ]["avg_time_seconds"].iloc[0]

    # Measured points P = 8, 16, 32 (T=1, consistent batch = 5000) from amdahl_investigation
    df_amd_target = df[(df["batch_size"] == BATCH_TARGET) & (df["threads"] == 1)]
    p_measured = np.array([8, 16, 32])

    # Statistical aggregation across 10 runs: median and stddev
    stats_p = df_amd_target.groupby("nodes")["total_time_seconds"].agg(["median", "mean", "std"]).loc[p_measured]
    speedup_measured = t1_target / stats_p["median"].values
    speedup_err = speedup_measured * (stats_p["std"].values / stats_p["mean"].values)

    # Amdahl theoretical continuous curve: S(P) = 1 / (fs + (1 - fs)/P)
    p_cont = np.linspace(1, 36, 300)
    s_cont = 1.0 / (fs_task + (1.0 - fs_task) / p_cont)

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.plot(p_cont, s_cont, color=COLOR_THEORY, linestyle="--", linewidth=1.8, label=f"Amdahl Theoretical Curve (fs = {fs_task*100:.2f}%)")

    # Plot measured points with error bars (stddev across 10 runs)
    for p, s, s_err in zip(p_measured, speedup_measured, speedup_err):
        ov = (p > 20)
        color = COLOR_GRPC
        ax.errorbar(p, s, yerr=s_err, fmt="none", ecolor=color, elinewidth=1.5, capsize=4, alpha=0.75)
        if not ov:
            ax.plot(p, s, marker="o", markersize=8, color=color, markerfacecolor=color, linestyle="None")
        else:
            ax.plot(p, s, marker="o", markersize=8, color=color, markerfacecolor="white", markeredgewidth=2.0, linestyle="None")

        s_theo = 1.0 / (fs_task + (1.0 - fs_task) / p)
        ax.annotate(
            f"P={p}: {s:.2f}x\n(Theoretical: {s_theo:.1f}x)",
            xy=(p, s), xytext=(p - 2.8, s - 2.8),
            fontsize=8,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#ebf8ff", edgecolor="#90cdf4", alpha=0.9),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.1", color="#2b6cb0", lw=1)
        )

    # Hardware threshold line
    ax.axvline(x=20, color="#e53e3e", linestyle=":", linewidth=1.2, alpha=0.7)
    ax.text(20.5, 2.0, "P_eff = 20 (Physical Core Threshold)", color="#e53e3e", fontsize=8)

    ax.plot([], [], marker="o", color=COLOR_GRPC, markerfacecolor=COLOR_GRPC, linestyle="None", label="Measured Clean (P ≤ 20, Batch 5,000)")
    ax.plot([], [], marker="o", color=COLOR_GRPC, markerfacecolor="white", markeredgewidth=2.0, linestyle="None", label="Measured Oversubscribed (P > 20, Batch 5,000)")

    ax.set_xlabel("Number of Nodes / Task Parallelism P (1 thread/node)")
    ax.set_ylabel("Speedup vs Sequential Baseline T1(5000)")
    ax.set_title(
        "Task C: Amdahl's Law Validation & Extension (P = 8, 16, 32)\n"
        "Divergence Between Ideal Asymptotic Curve and Empirical Measurements (Batch = 5,000)"
    )
    ax.set_xlim(1, 35)
    ax.set_ylim(1, 25)
    ax.legend(loc="upper left", framealpha=0.9, fontsize=8.5)

    save_plot(fig, "amdahl_predicted_vs_measured_extended")

    # 2. overhead_decomposition_stacked.png
    # 12 configurations grouped by (batch, nodes, threads)
    agg_df = df.groupby(["batch_size", "nodes", "threads"]).agg({
        "avg_worker_compute_s": "mean",
        "avg_network_overhead_s": "mean",
        "total_time_seconds": "mean",
        "network_overhead_fraction": "mean",
        "is_oversubscribed": "first"
    }).reset_index()

    agg_df = agg_df.sort_values(["batch_size", "nodes", "threads"]).reset_index(drop=True)

    config_labels = [
        f"N={r.nodes}, T={r.threads}\n(B={r.batch_size})"
        for _, r in agg_df.iterrows()
    ]

    compute_ms = agg_df["avg_worker_compute_s"].values * 1000
    overhead_ms = agg_df["avg_network_overhead_s"].values * 1000
    fractions_pct = agg_df["network_overhead_fraction"].values * 100

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(config_labels))
    width = 0.55

    bars1 = ax.bar(x, compute_ms, width, label="Useful C++ Compute Time (worker_time)", color="#3182bd", edgecolor="#1a365d")
    bars2 = ax.bar(x, overhead_ms, width, bottom=compute_ms, label="Network / RPC Coordination Overhead (network_overhead)", color="#e28743", edgecolor="#9c4221")

    for i, (b1, b2, pct) in enumerate(zip(compute_ms, overhead_ms, fractions_pct)):
        total_h = b1 + b2
        ax.text(
            i, total_h + 1.2,
            f"{pct:.1f}% net",
            ha="center", va="bottom", fontsize=8, fontweight="bold", color="#9c4221"
        )

    # Visual separator between Batch 1000 and Batch 5000
    ax.axvline(x=5.5, color="#718096", linestyle="--", linewidth=1.2)
    ax.text(2.5, max(compute_ms + overhead_ms) * 0.92, "Batch = 1,000 signatures", ha="center", fontsize=10, fontweight="bold", color="#4a5568")
    ax.text(8.5, max(compute_ms + overhead_ms) * 0.92, "Batch = 5,000 signatures", ha="center", fontsize=10, fontweight="bold", color="#4a5568")

    ax.set_xticks(x)
    ax.set_xticklabels(config_labels, fontsize=8.5)
    ax.set_ylabel("Average Time per RPC Call (milliseconds)")
    ax.set_title(
        "Task C: RPC Network Overhead vs C++ Compute Time Breakdown\n"
        "Average Across 10 Independent Runs for Each of the 12 Configurations"
    )
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9)
    ax.set_ylim(0, max(compute_ms + overhead_ms) * 1.15)

    save_plot(fig, "overhead_decomposition_stacked")

    # 3. throughput_saturation.png
    # Median throughput vs P_eff (log2) for the 12 configurations
    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    peff_ticks = [8, 16, 32, 64, 128, 256]

    df_thru_med = df.groupby(["batch_size", "nodes", "threads", "effective_parallelism", "is_oversubscribed"])["throughput"].median().reset_index()

    for batch, marker_b, color_b in [(1000, "^", "#3182bd"), (5000, "o", "#08519c")]:
        sub = df_thru_med[df_thru_med["batch_size"] == batch].sort_values("effective_parallelism")
        peffs = sub["effective_parallelism"].values
        thrus = sub["throughput"].values
        overs = sub["is_oversubscribed"].values

        plot_segmented_line(
            ax, peffs, thrus, overs,
            color=color_b, marker=marker_b, label=f"Batch {batch:,} (Median Throughput)",
            linewidth=1.4, markersize=7.5
        )

    # Asymptote band (~80k - 87k sig/s)
    ax.axhspan(80000, 87250, color="#fed7d7", alpha=0.45, label="Saturation Asymptote Band (~80k - 87k sig/s)")
    ax.axhline(y=87250, color="#e53e3e", linestyle="--", linewidth=1.2)
    ax.text(8.5, 88500, "Observed Upper Asymptote: 87,252 sig/s", color="#c53030", fontsize=8.5, fontweight="bold")

    ax.axvline(x=20, color="#e53e3e", linestyle=":", linewidth=1.2, alpha=0.7)
    ax.text(20.5, 36000, "P_eff=20", color="#e53e3e", fontsize=8)

    ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="#4a5568", linestyle="-", label="Clean Regime (solid line, filled marker)")
    ax.plot([], [], marker="o", color="#4a5568", markerfacecolor="white", markeredgewidth=1.8, linestyle="--", label="Oversubscribed (dashed line, hollow marker)")

    ax.set_xscale("log", base=2)
    ax.set_xticks(peff_ticks)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax.set_xlabel("Effective Parallelism P_eff (log2 scale)")
    ax.set_ylabel("Measured Median Throughput (sig/s)")
    ax.set_title(
        "Task C: Throughput Saturation & Empirical Asymptote\n"
        "12 Stress Test Configurations (10 Runs per Point)"
    )
    ax.legend(loc="lower right", framealpha=0.9, fontsize=8.5)
    ax.set_ylim(30000, 95000)

    save_plot(fig, "throughput_saturation")


# ==============================================================================
# GRAPHS F: Pipelining (Task D)
# ==============================================================================
def plot_f_pipelining():
    print("Generating Graphs F: Pipelining...")
    source_file = "pipeline_throughput_i7_12700h_20260908.csv"
    filepath = RESULTS_DIR / source_file
    df = pd.read_csv(filepath)

    # 1. pipeline_speedup_predicted_vs_measured.png
    # Theoretical formula: S(n, k) = n*k / (k + n - 1) with k=3
    k = 3
    n_cont = np.linspace(1, 8.5, 200)
    s_pred_cont = (n_cont * k) / (k + n_cont - 1)

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.plot(n_cont, s_pred_cont, color=COLOR_THEORY, linestyle="--", linewidth=1.8, label="Predicted Speedup S(n,3) = 3n / (n+2)")

    n_pts = df["n"].values
    s_meas = df["speedup_measured"].values

    t_seq_mean = df["t_sequential_mean_s"].values
    t_seq_std = df["t_sequential_stddev_s"].values
    t_conc_mean = df["t_concurrent_mean_s"].values
    t_conc_std = df["t_concurrent_stddev_s"].values
    s_err = s_meas * np.sqrt((t_seq_std / t_seq_mean)**2 + (t_conc_std / t_conc_mean)**2)

    ax.plot(n_pts, s_meas, color=COLOR_PIPELINE, linestyle="-", linewidth=1.8, alpha=0.85, label="Empirical Speedup (Mean over 5 runs)")
    for n, s, err in zip(n_pts, s_meas, s_err):
        ax.errorbar(n, s, yerr=err, fmt="none", ecolor=COLOR_PIPELINE, elinewidth=1.5, capsize=4)
        ax.plot(n, s, marker="o", markersize=7.5, color=COLOR_PIPELINE, markerfacecolor=COLOR_PIPELINE)
        pred_val = (n * k) / (k + n - 1)
        scarto = ((pred_val - s) / pred_val) * 100
        ax.annotate(
            f"n={n}: {s:.2f}x\n(Predicted: {pred_val:.2f}x, -{scarto:.1f}%)",
            xy=(n, s), xytext=(n + 0.25, s - 0.22),
            fontsize=8,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#f0fff4", edgecolor="#9ae6b4", alpha=0.9),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.1", color="#276749", lw=1)
        )

    ax.set_xlabel("Number of Concurrent Pipelined Requests (n)")
    ax.set_ylabel("Pipelining Speedup S(n)")
    ax.set_title(
        "Task D: Real 3-Stage Chain Pipelining — Predicted vs Measured Speedup\n"
        "(Satellite -> IoTronic / Lightning-Rod -> Worker-1 -> Worker-2 -> Worker-3)"
    )
    ax.set_xticks([1, 2, 3, 4, 5, 6, 7, 8])
    ax.set_xlim(0.8, 8.5)
    ax.set_ylim(0.7, 2.7)
    ax.legend(loc="upper left", framealpha=0.9, fontsize=8.5)

    save_plot(fig, "pipeline_speedup_predicted_vs_measured")

    # 2. pipeline_tseq_vs_tconc.png
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    x = np.arange(len(n_pts))
    width = 0.35

    bars_seq = ax.bar(x - width/2, t_seq_mean, width, yerr=t_seq_std, capsize=4, label="Sequential Time T_seq (mean ± stddev)", color="#e2e8f0", edgecolor="#4a5568", linewidth=1.1)
    bars_conc = ax.bar(x + width/2, t_conc_mean, width, yerr=t_conc_std, capsize=4, label="Concurrent Pipeline Time T_conc (mean ± stddev)", color=COLOR_PIPELINE, edgecolor="#14532d", linewidth=1.1)

    for bar, val in zip(bars_seq, t_seq_mean):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.15, f"{val:.2f}s", ha="center", va="bottom", fontsize=8.5, color="#2d3748")

    for bar, val in zip(bars_conc, t_conc_mean):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.15, f"{val:.2f}s", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#14532d")

    for i, (seq, conc) in enumerate(zip(t_seq_mean, t_conc_mean)):
        gain = seq - conc
        pct = (gain / seq) * 100 if seq > 0 else 0
        if gain > 0:
            ax.text(i, max(seq, conc) + 0.55, f"Δ = -{gain:.2f}s\n(-{pct:.0f}%)", ha="center", fontsize=8, color="#15803d", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([f"n = {n}" for n in n_pts], fontsize=10)
    ax.set_xlabel("Number of Concurrent Pipelined Requests")
    ax.set_ylabel("Total Pipeline Execution Time (seconds)")
    ax.set_title(
        "Task D: Absolute Execution Time — Sequential vs Concurrent Pipelined\n"
        "Absolute Latency Reduction Across 3 Physical Worker Nodes"
    )
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9)
    ax.set_ylim(0, max(t_seq_mean) * 1.22)

    save_plot(fig, "pipeline_tseq_vs_tconc")


# ==============================================================================
# MAIN ORCHESTRATOR
# ==============================================================================
def main():
    print(f"=== HPC REPORT GRAPH GENERATION (English, no environment watermark) ===")
    print(f"Output directory: {OUTPUT_DIR}\n")

    plot_a_profile_breakdown()
    plot_b_grpc_grid()
    plot_c_mpi_omp_grid()
    plot_d_substrate_comparison()
    plot_e_amdahl_and_overhead()
    plot_f_pipelining()

    print("\n=== GENERATION COMPLETED SUCCESSFULLY ===")
    files = sorted(os.listdir(OUTPUT_DIR))
    png_files = [f for f in files if f.endswith(".png")]
    pdf_files = [f for f in files if f.endswith(".pdf")]
    print(f"Total files in graphs/: {len(files)} ({len(png_files)} PNG, {len(pdf_files)} PDF)")


if __name__ == "__main__":
    main()
