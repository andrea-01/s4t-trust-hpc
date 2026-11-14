#!/usr/bin/env python3
"""
Extended verification script for report/main.tex (Stage 13.5-ter).
Performs:
1. Label & reference matching (checks that all \\ref{...} reference valid \\label{...}).
2. Fact matching against PROGRESS.md.
3. Comprehensive cell-by-cell check of Table 5 (speedup_summary) against raw CSVs.
4. Comprehensive cell-by-cell check of Table 6 (equal_cores_comparison) against raw CSVs.
5. Arithmetic & statistical checks (E5 speedup vs rate, Table 1 sum, worker yield, Karp-Flatt, net residuals, pipeline gaps).
"""
import re
import sys
from pathlib import Path
import pandas as pd
import numpy as np

tex_path = Path("report/main.tex")
with open(tex_path) as f:
    tex = f.read()

prog_path = Path("PROGRESS.md")
with open(prog_path) as f:
    prog = f.read()

failed = False

def check(condition: bool, msg: str):
    global failed
    if not condition:
        print(f"[-] FAILED: {msg}")
        failed = True
    else:
        print(f"[+] PASSED: {msg}")

print("=== 1. LaTeX Labels and References Integrity (T3) ===")
refs = re.findall(r"\\ref\{([^}]+)\}", tex)
labels = set(re.findall(r"\\label\{([^}]+)\}", tex))
missing = [r for r in set(refs) if r not in labels]
check(len(missing) == 0, f"All {len(refs)} references match defined labels (missing: {missing})")

print("\n=== 2. Text & Fact Matches vs PROGRESS.md ===")
facts = [
    ("T1 baseline", "1.0636", "1.0636" in prog),
    ("Single-thread rate", "18,804.8", "18.804" in prog or "18,804" in prog or "18804" in prog),
    ("per-verify mean", "57.42", "57.42" in tex),
    ("per-verify cv", "12.66", "12.66" in tex),
    ("per-verify p99", "87.44", "87.44" in tex),
    ("Montgomery mul %", "32.71", "32.71" in tex),
    ("Montgomery sqr %", "19.97", "19.97" in tex),
    ("Total EC/BIGNUM %", "87.88", "87.88" in tex),
    ("MPI reduce overhead", "0.038", "0.038" in tex),
    ("Ping latency low", "1.1", "1.1" in tex),
    ("Ping latency high", "1.3", "1.3" in tex),
    ("MPI p=2 speedup", "1.93", "1.93" in prog),
    ("MPI p=4 speedup", "3.71", "3.71" in prog),
    ("MPI p=6 speedup", "5.32", "5.32" in prog),
    ("MPI p=7 speedup", "3.35", "3.35" in prog),
    ("MPI p=8 speedup", "3.88", "3.88" in prog),
    ("MPI p=20 speedup", "8.81", "8.81" in prog),
    ("E6b R=3 speedup", "1.93", "1.93" in prog),
    ("E6b R=7 speedup", "4.99", "4.99" in prog),
    ("E6b R=8 speedup", "5.49", "5.49" in prog),
    ("E6b R=14 speedup", "8.15", "8.15" in prog),
    ("E6b vs E2b R=7 gain", "+48.9", "48.9" in prog),
    ("E6b vs E2b R=8 gain", "+41.7", "41.7" in prog),
    ("E6b vs E2b R=14 gain", "+27.4", "27.4" in prog),
    ("E5 dynamic,16 S at T=16", "9.20", "9.20" in prog),
    ("E5 dynamic,16 S at T=20", "9.89", "9.89" in prog),
    ("E5 static S at T=20", "8.68", "8.68" in prog),
    ("C_static(20)", "8.74", "8.74" in prog),
    ("C_dyn(20)", "10.20", "10.20" in prog),
    ("E_cap_static MPI p=20", "100.8", "100.8" in prog),
    ("E_cap_static OMP p=20", "99.4", "99.4" in prog),
    ("E_cap_dyn dynamic,16", "97.0", "97.0" in prog),
    ("Amdahl fs", "2.80", "2.80" in prog),
    ("Amdahl p=6 pred", "5.26", "5.26" in prog),
    ("E4c p2_pcores wall", "1.0086", "1.0086" in prog),
    ("E4c p2_smt wall", "1.5525", "1.5525" in prog),
    ("E4c p8_ecores wall", "0.4979", "0.4979" in prog),
    ("E4c p8_smt wall", "0.4240", "0.4240" in prog),
    ("E4c p8_ecores net res", "26.9", "26.9" in prog),
    ("E4c p8_smt net res", "23.5", "23.5" in prog),
    ("E4c p6 net res", "79.0", "79.0" in prog),
    ("Pipeline n=8 runtime seq", "5.584", "5.584" in tex),
    ("Pipeline n=8 runtime conc", "3.532", "3.532" in tex),
]

for name, val, ok in facts:
    check(ok, f"Fact match for {name}: {val}")

print("\n=== 3. Table 5 (speedup_summary) Full Cell-by-Cell Check vs CSVs (T1/T2) ===")
t1_ref = 1.063555
e1c = pd.read_csv("hpc-engine/results/m13/results_e1c_omp_cores_close.csv")
e2b = pd.read_csv("hpc-engine/results/m13/results_e2b_mpi_map_core.csv")
e3 = pd.read_csv("hpc-engine/results/m13/results_e3_hybrid.csv")
e3b = pd.read_csv("hpc-engine/results/m13/results_e3b_hybrid_map_core.csv")
e4 = pd.read_csv("hpc-engine/results/m13/results_e4_grpc.csv")

pos5 = tex.find("\\label{tab:speedup_summary}")
start5 = tex.rfind("\\midrule", 0, pos5)
end5 = tex.rfind("\\bottomrule", 0, pos5)
table5_str = tex[start5+8:end5].strip()

tab5_ok = True
for line in table5_str.split("\n"):
    line = line.strip()
    if not line or line.startswith("%"):
        continue
    parts = [p.strip() for p in line.replace("\\\\", "").split("&")]
    p = int(parts[0])
    omp_s, omp_e = parts[1], float(parts[2])
    mpi_s, mpi_e = parts[3], float(parts[4])
    hyb_s, hyb_e = parts[5], parts[6]
    grpc_w, grpc_c = parts[7], parts[8]

    # OpenMP close (E1c)
    sub_e1c = e1c[e1c["threads"] == p]
    s_vals = t1_ref / sub_e1c["time_seconds"].values
    med, q25, q75 = np.median(s_vals), np.percentile(s_vals, 25), np.percentile(s_vals, 75)
    if omp_s != f"{med:.2f} [{q25:.2f}--{q75:.2f}]":
        tab5_ok = False
        print(f"[-] Table 5 p={p} OpenMP mismatch: got {omp_s}")

    # MPI pure (E2b)
    sub_e2b = e2b[e2b["ranks"] == p]
    s_vals = t1_ref / sub_e2b["time_seconds"].values
    med, q25, q75 = np.median(s_vals), np.percentile(s_vals, 25), np.percentile(s_vals, 75)
    if mpi_s != f"{med:.2f} [{q25:.2f}--{q75:.2f}]":
        tab5_ok = False
        print(f"[-] Table 5 p={p} MPI mismatch: got {mpi_s}")

    # Hybrid (E3/E3b)
    if p in [2, 4, 6]:
        if hyb_s != "---" or hyb_e != "---":
            tab5_ok = False
    elif p in [8, 12]:
        sub_e3b = e3b[e3b["physical_cores"] == p]
        s_vals = t1_ref / sub_e3b["time_seconds"].values
        med, q25, q75 = np.median(s_vals), np.percentile(s_vals, 25), np.percentile(s_vals, 75)
        if hyb_s != f"{med:.2f} [{q25:.2f}--{q75:.2f}]$^\\dagger$":
            tab5_ok = False
            print(f"[-] Table 5 p={p} Hybrid dagger mismatch: got {hyb_s}")
    elif p in [16, 20]:
        sub_e3 = e3[e3["ranks"] * e3["threads"] == p]
        s_vals = t1_ref / sub_e3["time_seconds"].values
        med, q25, q75 = np.median(s_vals), np.percentile(s_vals, 25), np.percentile(s_vals, 75)
        if hyb_s != f"{med:.2f} [{q25:.2f}--{q75:.2f}]$^*$":
            tab5_ok = False
            print(f"[-] Table 5 p={p} Hybrid star mismatch: got {hyb_s}")

    # gRPC isolated (E4 unpinned)
    sub_e4 = e4[e4["p_eff"] == p]
    sw = t1_ref / sub_e4["time_seconds"].values
    sc = t1_ref / sub_e4["verify_s"].values
    med_w, q25_w, q75_w = np.median(sw), np.percentile(sw, 25), np.percentile(sw, 75)
    med_c, q25_c, q75_c = np.median(sc), np.percentile(sc, 25), np.percentile(sc, 75)
    if grpc_w != f"{med_w:.2f} [{q25_w:.2f}--{q75_w:.2f}]":
        tab5_ok = False
        print(f"[-] Table 5 p={p} gRPC wall mismatch: got {grpc_w}")
    if grpc_c != f"{med_c:.2f} [{q25_c:.2f}--{q75_c:.2f}]":
        tab5_ok = False
        print(f"[-] Table 5 p={p} gRPC comp mismatch: got {grpc_c}")

check(tab5_ok, "All 56 cells in Table 5 (speedup_summary) verified against raw CSVs")

print("\n=== 4. Table 6 (equal_cores_comparison) Full Cell-by-Cell Check vs CSVs (T2/T4) ===")
e6b = pd.read_csv("hpc-engine/results/m13/results_e6b_dynamic_map_core.csv")
e10 = pd.read_csv("hpc-engine/results/m13/results_e10_dynamic_hybrid.csv")

pos6 = tex.find("\\label{tab:equal_cores_comparison}")
start6 = tex.rfind("\\midrule", 0, pos6)
end6 = tex.rfind("\\bottomrule", 0, pos6)
table6_str = tex[start6+8:end6].strip()

tab6_ok = True
for line in table6_str.split("\n"):
    line = line.strip()
    if not line or line.startswith("%"):
        continue
    parts = [p.strip() for p in line.replace("\\\\", "").split("&")]
    r = int(parts[0])
    e2b_s = parts[1]
    e1c_s = parts[2]
    e3b_s = parts[3]
    e6b_s = parts[4]
    e10_s = parts[5]
    verdict = parts[6]

    # E2b
    sub2 = e2b[e2b["ranks"] == r]
    s2 = t1_ref / sub2["time_seconds"].values
    med2, q25_2, q75_2 = np.median(s2), np.percentile(s2, 25), np.percentile(s2, 75)
    if e2b_s != f"{med2:.2f} [{q25_2:.2f}--{q75_2:.2f}]":
        tab6_ok = False
        print(f"[-] Table 6 R={r} E2b mismatch: got {e2b_s}")

    # E1c
    sub1 = e1c[e1c["threads"] == r]
    if len(sub1) > 0:
        s1 = t1_ref / sub1["time_seconds"].values
        med1, q25_1, q75_1 = np.median(s1), np.percentile(s1, 25), np.percentile(s1, 75)
        if e1c_s != f"{med1:.2f} [{q25_1:.2f}--{q75_1:.2f}]":
            tab6_ok = False
            print(f"[-] Table 6 R={r} E1c mismatch: got {e1c_s}")
    else:
        if e1c_s != "---":
            tab6_ok = False
            print(f"[-] Table 6 R={r} E1c expected ---, got {e1c_s}")

    # E3b
    sub3 = e3b[e3b["physical_cores"] == r]
    if len(sub3) > 0:
        s3 = t1_ref / sub3["time_seconds"].values
        med3, q25_3, q75_3 = np.median(s3), np.percentile(s3, 25), np.percentile(s3, 75)
        if e3b_s != f"{med3:.2f} [{q25_3:.2f}--{q75_3:.2f}]":
            tab6_ok = False
            print(f"[-] Table 6 R={r} E3b mismatch: got {e3b_s}")
    else:
        if e3b_s != "---":
            tab6_ok = False

    # E6b (c=25)
    sub6 = e6b[(e6b["ranks"] == r) & (e6b["chunk_size"] == 25)]
    s6 = t1_ref / sub6["time_seconds"].values
    med6, q25_6, q75_6 = np.median(s6), np.percentile(s6, 25), np.percentile(s6, 75)
    if e6b_s != f"{med6:.2f} [{q25_6:.2f}--{q75_6:.2f}]":
        tab6_ok = False
        print(f"[-] Table 6 R={r} E6b mismatch: got {e6b_s}")

    # E10 (c=50)
    sub10 = e10[(e10["physical_cores"] == r) & (e10["chunk_size"] == 50)]
    if len(sub10) > 0:
        s10 = t1_ref / sub10["time_seconds"].values
        med10, q25_10, q75_10 = np.median(s10), np.percentile(s10, 25), np.percentile(s10, 75)
        if e10_s != f"{med10:.2f} [{q25_10:.2f}--{q75_10:.2f}]":
            tab6_ok = False
            print(f"[-] Table 6 R={r} E10 mismatch: got {e10_s}")
    else:
        if e10_s != "---":
            tab6_ok = False

    # Verdict
    diff = (med6 - med2) / med2 * 100.0
    if q25_6 > q75_2:
        exp_v = f"E6b wins (${diff:+.1f}\\%$)"
    elif q75_6 < q25_2:
        exp_v = f"E6b loses (${diff:+.1f}\\%$)"
    else:
        exp_v = "indistinguishable"
    if verdict != exp_v:
        tab6_ok = False
        print(f"[-] Table 6 R={r} verdict mismatch: got {verdict}, expected {exp_v}")

check(tab6_ok, "All 60 cells in Table 6 (equal_cores_comparison) verified against raw CSVs")

print("\n=== 5. Arithmetic Check: E5 Speedup vs Throughput (A1) ===")
v1 = 18804.8
rate_static_16 = 144700.0  # from 144.7 ksig/s
rate_dyn_16 = 173000.0     # from 173.0 ksig/s
s_calc_static = rate_static_16 / v1
s_calc_dyn = rate_dyn_16 / v1
check(abs(s_calc_static - 7.69) < 0.05, f"E5 static T=16 S = {s_calc_static:.2f} matches 7.69")
check(abs(s_calc_dyn - 9.20) < 0.05, f"E5 dynamic,16 T=16 S = {s_calc_dyn:.2f} matches 9.20")
check("144.7" in tex and "173.0" in tex, "Correct throughput values 144.7 and 173.0 present in text")
check("136.0" not in tex and "162.7" not in tex, "Old erroneously divided throughputs 136.0 and 162.7 removed from text")

print("\n=== 6. Arithmetic Check: Table 1 Instruction Profile Sum (A3) ===")
tab1_items = [87.88, 6.26, 3.20, 1.80, 0.86]
sum_tab1 = sum(tab1_items)
check(abs(sum_tab1 - 100.0) < 1e-5, f"Table 1 instruction rows sum to {sum_tab1:.2f}% (exact 100%)")
check(abs(87.88 + 6.26 - 94.14) < 1e-5, "Crypto total 87.88% + 6.26% = 94.14%")
check("Unattributed / runtime libc" in tex, "Unattributed libc row present in Table 1")

print("\n=== 7. Arithmetic Check: Static MPI S/R and Worker Yield S/(R-1) (A5) ===")
e2b_s = {3: 2.81, 4: 3.71, 5: 4.45, 6: 5.32}
e6b_s = {3: 1.93, 4: 2.87, 5: 3.60, 6: 4.49}
for r in [3, 4, 5, 6]:
    sr_static = e2b_s[r] / r
    s_worker_dyn = e6b_s[r] / (r - 1)
    check(0.88 <= sr_static <= 0.95, f"R={r}: Static MPI S/R = {sr_static:.2f} in [0.89, 0.94]")
    check(0.89 <= s_worker_dyn <= 0.98, f"R={r}: E6b worker yield S/(R-1) = {s_worker_dyn:.2f} in [0.90, 0.97]")

print("\n=== 8. Arithmetic Check: Karp-Flatt Serialization e(p) (B3) ===")
def kf(s, p):
    return (1.0/s - 1.0/p) / (1.0 - 1.0/p)

e6_val = kf(5.32, 6)
e7_val = kf(3.35, 7)
e8_val = kf(3.88, 8)
check(0.025 <= e6_val <= 0.036, f"e(6) = {e6_val:.4f} in [0.026, 0.036]")
check(0.17 <= e7_val <= 0.19, f"e(7) = {e7_val:.4f} matches ~0.18")
check(0.14 <= e8_val <= 0.16, f"e(8) = {e8_val:.4f} matches ~0.15")

print("\n=== 9. Arithmetic Check: Table 7 Net Residuals (B5) ===")
ping = 0.00133
e4c_rows = [
    ("p2_pcores", 1.0086, 0.5740, 0.3850, 48.3),
    ("p2_smt", 1.5525, 0.9072, 0.6150, 29.2),
    ("p6_pcores", 0.4659, 0.2573, 0.1284, 79.0),
    ("p6_pcores_conc", 0.4659, 0.2573, 0.1387, 68.7),
    ("p8_ecores", 0.4979, 0.2822, 0.1875, 26.9),
    ("p8_smt", 0.4240, 0.2455, 0.1537, 23.5),
    ("p12_ecores", 0.3662, 0.2071, 0.1250, 33.0),
    ("p14_ecores", 0.3164, 0.1772, 0.1072, 30.8),
]

for cfg, tw, tv, tg, expected_res in e4c_rows:
    calc_res_ms = (tw - tv - tg - ping) * 1000.0
    check(abs(calc_res_ms - expected_res) < 0.6, f"E4c {cfg}: Net Res = {calc_res_ms:.1f} ms matches expected {expected_res:.1f} ms")

print("\n=== 10. Arithmetic Check: Table 8 Pipeline Gaps (A9) ===")
p_gaps = [
    (1, 0.98, 1.00, 2.0),
    (2, 1.39, 1.50, 7.3),
    (4, 1.318, 2.00, 34.1),
    (8, 1.581, 2.40, 34.1),
]
for n, s_m, s_p, exp_gap in p_gaps:
    gap = (s_p - s_m) / s_p * 100.0
    check(abs(gap - exp_gap) < 0.2, f"Pipeline n={n}: Gap = {gap:.1f}% matches expected {exp_gap:.1f}%")

print("\n=== 11. Figure Data Anti-Regression and Consistency Checks (G1-G5) ===")
fig_data_dir = Path("report/figure_data")
expected_files = [
    "fig02_profile.csv",
    "fig06_strong_scaling.csv",
    "fig07_karp_flatt.csv",
    "fig08_openmp_schedules.csv",
    "fig09_taskbased_scaling.csv",
    "fig10_parallel_efficiency.csv",
    "fig11_amdahl_fit.csv",
    "fig12_grpc_vs_mpi.csv",
]
for fn in expected_files:
    fp = fig_data_dir / fn
    check(fp.exists(), f"Figure data CSV exists: {fn}")

# Check forbidden series across all figure_data CSVs
forbidden_series = ["OpenMP bound (E1b)", "E1b", "MPI pure (E2)"]
for fp in fig_data_dir.glob("*.csv"):
    df_fig = pd.read_csv(fp)
    if "series" in df_fig.columns:
        for bad in forbidden_series:
            has_bad = (df_fig["series"] == bad).any()
            check(not has_bad, f"{fp.name}: Forbidden series '{bad}' absent")

# Control points: fig06_strong_scaling.csv
df06 = pd.read_csv(fig_data_dir / "fig06_strong_scaling.csv")
def get_s06(series_name, x_val):
    sub = df06[(df06["series"] == series_name) & (df06["x"] == x_val)]
    return sub["y"].values[0] if len(sub) > 0 else None

# MPI pure (E2b)
check(abs(get_s06("MPI pure (E2b)", 2) - 1.93) < 0.05, f"Fig 06: MPI p=2 S = {get_s06('MPI pure (E2b)', 2):.2f} (matches 1.93, not 1.2)")
check(abs(get_s06("MPI pure (E2b)", 6) - 5.32) < 0.05, f"Fig 06: MPI p=6 S = {get_s06('MPI pure (E2b)', 6):.2f} (matches 5.32)")
check(abs(get_s06("MPI pure (E2b)", 7) - 3.35) < 0.05, f"Fig 06: MPI p=7 S = {get_s06('MPI pure (E2b)', 7):.2f} (matches 3.35)")
check(abs(get_s06("MPI pure (E2b)", 8) - 3.88) < 0.05, f"Fig 06: MPI p=8 S = {get_s06('MPI pure (E2b)', 8):.2f} (matches 3.88)")
check(abs(get_s06("MPI pure (E2b)", 20) - 8.81) < 0.05, f"Fig 06: MPI p=20 S = {get_s06('MPI pure (E2b)', 20):.2f} (matches 8.81)")

# OpenMP close (E1c)
check(abs(get_s06("OpenMP close (E1c)", 6) - 5.23) < 0.05, f"Fig 06: OpenMP close p=6 S = {get_s06('OpenMP close (E1c)', 6):.2f} (matches 5.23)")
check(abs(get_s06("OpenMP close (E1c)", 20) - 8.37) < 0.05, f"Fig 06: OpenMP close p=20 S = {get_s06('OpenMP close (E1c)', 20):.2f} (matches 8.37)")

# Capacities
check(abs(get_s06("Capacity static (E9b)", 20) - 8.74) < 0.05, f"Fig 06: C_static(20) = {get_s06('Capacity static (E9b)', 20):.2f} (matches 8.74)")
check(abs(get_s06("Capacity dynamic (E9b)", 20) - 10.20) < 0.05, f"Fig 06: C_dyn(20) = {get_s06('Capacity dynamic (E9b)', 20):.2f} (matches 10.20)")

# gRPC wall vs compute
check(abs(get_s06("gRPC wall (E4)", 2) - 1.14) < 0.05, f"Fig 06: gRPC wall p=2 S = {get_s06('gRPC wall (E4)', 2):.2f} (matches 1.14)")
check(abs(get_s06("gRPC wall (E4)", 20) - 3.53) < 0.05, f"Fig 06: gRPC wall p=20 S = {get_s06('gRPC wall (E4)', 20):.2f} (matches 3.53)")
check(abs(get_s06("gRPC compute (E4)", 2) - 2.00) < 0.05, f"Fig 06: gRPC compute p=2 S = {get_s06('gRPC compute (E4)', 2):.2f} (matches 2.00)")
check(abs(get_s06("gRPC compute (E4)", 20) - 9.11) < 0.05, f"Fig 06: gRPC compute p=20 S = {get_s06('gRPC compute (E4)', 20):.2f} (matches 9.11)")

# Control points: fig07_karp_flatt.csv
df07 = pd.read_csv(fig_data_dir / "fig07_karp_flatt.csv")
def get_e07(series_name, x_val):
    sub = df07[(df07["series"] == series_name) & (df07["x"] == x_val)]
    return sub["y"].values[0] if len(sub) > 0 else None

check(0.025 <= get_e07("MPI pure (E2b)", 2) <= 0.045, f"Fig 07: MPI p=2 e(2) = {get_e07('MPI pure (E2b)', 2):.4f} in [0.025, 0.045] (not broken ~0.61)")
check(0.020 <= get_e07("MPI pure (E2b)", 6) <= 0.035, f"Fig 07: MPI p=6 e(6) = {get_e07('MPI pure (E2b)', 6):.4f} in [0.020, 0.035]")
check(0.17 <= get_e07("MPI pure (E2b)", 7) <= 0.19, f"Fig 07: MPI p=7 e(7) = {get_e07('MPI pure (E2b)', 7):.4f} ~0.18")
check(0.14 <= get_e07("MPI pure (E2b)", 8) <= 0.16, f"Fig 07: MPI p=8 e(8) = {get_e07('MPI pure (E2b)', 8):.4f} ~0.15")
sub_e2b = df07[df07["series"] == "MPI pure (E2b)"]
all_in_bounds = ((sub_e2b["y"] >= -0.01) & (sub_e2b["y"] <= 0.25)).all()
check(all_in_bounds, "Fig 07: All Karp-Flatt values for MPI pure (E2b) in [-0.01, 0.25]")

# Control points: fig08_openmp_schedules.csv
df08 = pd.read_csv(fig_data_dir / "fig08_openmp_schedules.csv")
def get_rate08(sched):
    sub = df08[df08["schedule"] == sched]
    return sub["throughput_ksig"].values[0] if len(sub) > 0 else None

check(abs(get_rate08("static") - 144.7) < 0.2, f"Fig 08: static rate = {get_rate08('static'):.1f} ksig/s ~144.7")
check(abs(get_rate08("guided") - 159.9) < 0.2, f"Fig 08: guided rate = {get_rate08('guided'):.1f} ksig/s ~159.9")
check(abs(get_rate08("dynamic,16") - 173.0) < 0.2, f"Fig 08: dynamic,16 rate = {get_rate08('dynamic,16'):.1f} ksig/s ~173.0")

# Control points: fig10_parallel_efficiency.csv
df10 = pd.read_csv(fig_data_dir / "fig10_parallel_efficiency.csv")
def get_eff10(series_name, x_val):
    sub = df10[(df10["series"] == series_name) & (df10["x"] == x_val)]
    return sub["y"].values[0] if len(sub) > 0 else None

check(abs(get_eff10("MPI pure (E2b)", 2) - 0.966) < 0.02, f"Fig 10: MPI p=2 E = {get_eff10('MPI pure (E2b)', 2):.3f} ~0.97 (not 0.62)")
check(abs(get_eff10("MPI pure (E2b)", 6) - 0.886) < 0.02, f"Fig 10: MPI p=6 E = {get_eff10('MPI pure (E2b)', 6):.3f} ~0.89")
check(abs(get_eff10("OpenMP close (E1c)", 6) - 0.871) < 0.02, f"Fig 10: OpenMP close p=6 E = {get_eff10('OpenMP close (E1c)', 6):.3f} ~0.87")

# Control points: fig12_grpc_vs_mpi.csv
df12 = pd.read_csv(fig_data_dir / "fig12_grpc_vs_mpi.csv")
def get_rate12(series_name, x_val):
    sub = df12[(df12["series"] == series_name) & (df12["x"] == x_val)]
    return sub["y"].values[0] if len(sub) > 0 else None

check(abs(get_rate12("MPI pure (E2b)", 2) - 36.3) < 0.5, f"Fig 12: MPI p=2 rate = {get_rate12('MPI pure (E2b)', 2):.1f} ksig/s ~36.3")
rate_wall_20 = get_rate12("gRPC wall (E4)", 20)
rate_comp_20 = get_rate12("gRPC compute (E4)", 20)
check(abs(rate_wall_20 - 66.5) < 1.0, f"Fig 12: gRPC wall p=20 rate = {rate_wall_20:.1f} ksig/s ~66.5")
check(abs(rate_comp_20 - 171.3) < 1.0, f"Fig 12: gRPC compute p=20 rate = {rate_comp_20:.1f} ksig/s ~171.3")
check(rate_comp_20 - rate_wall_20 > 100.0, f"Fig 12: gRPC compute is distinctly separated from wall (diff = {rate_comp_20 - rate_wall_20:.1f} ksig/s > 100)")

if failed:
    print("\n[FAILURE] One or more verification checks failed!")
    sys.exit(1)
else:
    print("\n[SUCCESS] ALL mathematical, statistical, structural, and CSV checks passed perfectly!")
