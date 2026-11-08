# TRACEABILITY.md — M13 Report Artifact Traceability

This document records the exact data provenance, raw and derived CSV sources, analysis scripts, and plotting routines for every table and figure presented in the final HPC report (`report/main.tex`).

---

## 1. Baseline Measurements

- **Reference Single-Thread Time ($T_1$):**
  - Value: $T_1 = 1.063555$\,s (reported as $1.0636$\,s, IQR $0.0031$\,s, throughput $18{,}804.8$\,signatures/s).
  - Raw Data: `hpc-engine/results/m13/results_e0b_sequential.csv` (10 repetitions, $N = 20{,}000$, CPU 0).
  - Derivation Script: `hpc-engine/benchmarks/calculate_x4_efficiencies.py`.
- **Per-Verification Micro-benchmark:**
  - Metrics: Mean $57.42\,\mu$s, SD $7.27\,\mu$s, $CV = 12.66\%$, p50 $55.71\,\mu$s, p90 $59.73\,\mu$s, p99 $87.44\,\mu$s, timer overhead $12.80$\,ns.
  - Raw Data: `hpc-engine/results/m13/per_verify_cost.csv` ($N = 20{,}000$ calls).
  - Summary: `hpc-engine/results/m13/per_verify_summary.csv`.
  - Binary Source: `hpc-engine/src/onboarding/bench_device_gen.cpp`.

---

## 2. Figures Traceability

| Figure in Report | Label | Description | Generating Script | Primary Data Source (CSV / Logs) |
|---|---|---|---|---|
| Figure 1 | `fig:verify_flow` | Verification control flow | Direct TikZ vector code in `main.tex` | Algorithm 1 specification |
| Figure 2 | `fig:profile_breakdown` | Instruction profile breakdown | Valgrind / Callgrind script | `graphs/profile_breakdown.pdf` |
| Figure 3 | `fig:dep_graph` | Task dependency graph | Direct TikZ vector code in `main.tex` | Section 3 PCAM partitioning |
| Figure 4 | `fig:pipeline_graph` | Pipeline functional graph | Direct TikZ vector code in `main.tex` | Section 3 PCAM pipeline decomposition |
| Figure 5 | `fig:hybrid_architecture` | Two-tier hybrid architecture | Direct TikZ vector code in `main.tex` | Section 6 PCAM agglomeration |
| Figure 6 | `fig:strong_scaling` | Strong scaling speedup $S(p)$ | `hpc-engine/benchmarks/generate_m13_graphs.py` | `derived_speedup.csv`, `v3_machine_capacity_curve.csv`, `results_e2b_mpi_map_core.csv` |
| Figure 7 | `fig:karp_flatt` | Karp-Flatt serialization $e(p)$ | `hpc-engine/benchmarks/generate_m13_graphs.py` | `derived_karp_flatt.csv` |
| Figure 8 | `fig:openmp_schedules` | 15 OpenMP schedules at $T=16$ | `hpc-engine/benchmarks/generate_m13_graphs.py` | `derived_schedule.csv`, `results_e5_schedule.csv` |
| Figure 9 | `fig:taskbased_scaling` | Taskloop vs.\ dynamic MPI | `hpc-engine/benchmarks/generate_m13_graphs.py` | `derived_taskbased.csv`, `results_e6_taskbased.csv` |
| Figure 10 | `fig:parallel_efficiency` | Parallel efficiency $E(p)$ & capacity bounds | `hpc-engine/benchmarks/generate_m13_graphs.py` | `derived_speedup.csv`, `v3_machine_capacity_curve.csv` |
| Figure 11 | `fig:amdahl_fit` | Amdahl fit on $p \le 4$ with 95% CI | `hpc-engine/benchmarks/generate_m13_graphs.py` | `derived_amdahl.csv`, `results_e2b_mpi_map_core.csv` |
| Figure 12 | `fig:grpc_vs_mpi` | gRPC wall & compute vs.\ MPI | `hpc-engine/benchmarks/generate_m13_graphs.py` | `results_e2b_mpi_map_core.csv`, `results_e4_grpc.csv` |
| Figure 13 | `fig:pipeline_speedup` | Pipeline speedup vs.\ model | M11.5 plotting script | `graphs/pipeline_speedup_predicted_vs_measured.pdf` |

---

## 3. Tables Traceability

| Table in Report | Label | Description | Generating / Analysis Script | Primary Data Source (CSV / Logs) |
|---|---|---|---|---|
| Table 1 | `tab:callgrind_profile` | Callgrind flat instruction profile | Callgrind analysis script | OpenSSL 3.0 debug symbols profile, batch 500 |
| Table 2 | `tab:comm_overhead` | Communication substrate overhead | Statistical summarization | `results_e2b_mpi_map_core.csv` (`reduce_s`), `v1_ping_dispatch.csv`, M11.5 telemetry |
| Table 3 | `tab:mapping_policies` | Mapping policy matrix | Conceptual PCAM design | `report/sezioni_13_5_bozza.tex` Section 5 |
| Table 4 | `tab:binding_hardware` | Hardware binding flags & cores | Audit of launch scripts & logs | `hpc-engine/benchmarks/launch_*.sh`, `logs/e2.log`, `logs/e6.log`, `OMP_DISPLAY_AFFINITY` |
| Table 5 | `tab:speedup_summary` | Speedup & efficiency ($p \in [2, 20]$) | `calculate_x4_efficiencies.py` | `results_e1c_omp_cores_close.csv`, `results_e2b_mpi_map_core.csv`, `results_e3_hybrid.csv`, `results_e4_grpc.csv` |
| Table 6 | `tab:equal_cores_comparison` | Equal physical cores ($R \in [3, 14]$) | `analyze_x1.py`, `analyze_x3.py` | `results_e2b_mpi_map_core.csv`, `results_e6b_dynamic_map_core.csv`, `results_e3b_hybrid_map_core.csv`, `results_e10_dynamic_hybrid.csv` |
| Table 7 | `tab:e4c_discriminant` | Discriminant gRPC pinning test | `analyze_x2.py` | `results_e4c_smt_ecore_discrim.csv` |
| Table 8 | `tab:pipeline_perf` | Pipeline concurrent speedup ($k=3$) | M11.5 benchmark script | Historical pipeline campaign telemetry |

---

## 4. Derived Metric Formulas & Baselines

- **Machine Capacity Limits (E9b, `results_e9b_capacity_fill.csv`):**
  - Normalized against $T_1(\text{E0b}) = 1.063555$\,s ($v_1 = 18{,}804.8$\,signatures/s).
  - Recomputed via `hpc-engine/benchmarks/update_x4_capacity.py` saving into `hpc-engine/results/m13/v3_machine_capacity_curve.csv`.
- **Amdahl Parameter Estimation:**
  - $f_s = 2.802\%$ [Bootstrap 95% CI: $2.330\%,\; 4.006\%$] fitted on $p \in \{1, 2, 3, 4\}$ of `results_e2b_mpi_map_core.csv`.
  - Stored in `hpc-engine/results/m13/derived_amdahl.csv`.
- **Net Residual Formula (E4c):**
  - $\text{Net Residual} = T_{\mathrm{wall}} - T_{\mathrm{verify}} - Gen(chunk) - Ping$.
  - Reported in Table 7 and documented in `PROGRESS.md` Section 13.4-quater.
