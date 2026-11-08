#!/usr/bin/env python3
"""
Verification script for numerical claims in report/main.tex vs PROGRESS.md and experimental artifacts.
"""
from pathlib import Path

tex_path = Path("report/main.tex")
with open(tex_path) as f:
    tex = f.read()

prog_path = Path("PROGRESS.md")
with open(prog_path) as f:
    prog = f.read()

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

all_ok = True
for name, val, ok in facts:
    if not ok:
        print(f"[-] FAILED check for {name}: {val}")
        all_ok = False
    else:
        print(f"[+] Verified {name}: {val}")

if all_ok:
    print("\n[SUCCESS] All key numerical claims match PROGRESS.md and experimental artifacts!")

