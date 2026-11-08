import pandas as pd
import numpy as np

T1 = 1.063555

def get_stats(df, key_col, time_col="time_seconds"):
    res = {}
    for k, grp in df.groupby(key_col):
        t = grp[time_col].values
        s = T1 / t
        q25 = float(np.percentile(s, 25))
        med = float(np.percentile(s, 50))
        q75 = float(np.percentile(s, 75))
        res[k] = (med, q25, q75, q75 - q25)
    return res

def format_stat(tup):
    if not tup:
        return "N/A"
    return f"{tup[0]:.2f} [{tup[1]:.2f}-{tup[2]:.2f}]"

def cmp_verdict(test_tup, ref_tup):
    if not test_tup or not ref_tup:
        return "N/A"
    m1, l1, h1, _ = test_tup
    m2, l2, h2, _ = ref_tup
    if l1 > h2:
        return "Vince"
    elif h1 < l2:
        return "Perde"
    else:
        return "Indist."

def main():
    e10 = pd.read_csv("hpc-engine/results/m13/results_e10_dynamic_hybrid.csv")
    e3b = pd.read_csv("hpc-engine/results/m13/results_e3b_hybrid_map_core.csv")
    e6b = pd.read_csv("hpc-engine/results/m13/results_e6b_dynamic_map_core.csv")
    e2b = pd.read_csv("hpc-engine/results/m13/results_e2b_mpi_map_core.csv")
    e1c = pd.read_csv("hpc-engine/results/m13/results_e1c_omp_cores_close.csv")

    stats_e2b = get_stats(e2b, "ranks")
    stats_e1c = get_stats(e1c, "threads")
    
    # E6b by ranks (physical cores)
    stats_e6b_25 = get_stats(e6b[e6b["chunk_size"] == 25], "ranks")
    stats_e6b_100 = get_stats(e6b[e6b["chunk_size"] == 100], "ranks")

    # E3b: group by (physical_cores, ranks, threads)
    stats_e3b = {}
    for (cores, r, th), grp in e3b.groupby(["physical_cores", "ranks", "threads"]):
        t = grp["time_seconds"].values
        s = T1 / t
        stats_e3b[(cores, r, th)] = (float(np.percentile(s, 50)), float(np.percentile(s, 25)), float(np.percentile(s, 75)), 0.0)

    # E10: group by (physical_cores, ranks, threads, chunk_size)
    stats_e10 = {}
    for (cores, r, th, chunk), grp in e10.groupby(["physical_cores", "ranks", "threads", "chunk_size"]):
        t = grp["time_seconds"].values
        s = T1 / t
        stats_e10[(cores, r, th, chunk)] = (float(np.percentile(s, 50)), float(np.percentile(s, 25)), float(np.percentile(s, 75)), 0.0)

    print("\n" + "="*160)
    print("CONFRONTO GENERALE A PARI CORE FISICI: E10 vs E3b, E6b, E2b, E1c")
    print("="*160)

    # Cores to examine: 8, 10, 12, 14
    for cores in [8, 10, 12, 14]:
        print(f"\n>>> CORE FISICI: {cores}")
        print(f"{'Modello':<28} | {'Config / Chk':<14} | {'Inattivi':<12} | {'S [IQR]':<20} | {'vs E3b':<8} | {'vs E6b_25':<10} | {'vs E6b_100':<10} | {'vs E2b':<8} | {'vs E1c':<8}")
        print("-" * 145)

        s_e2b = stats_e2b.get(cores)
        s_e1c = stats_e1c.get(cores)
        s_e6b_25 = stats_e6b_25.get(cores)
        s_e6b_100 = stats_e6b_100.get(cores)

        print(f"{'E2b (MPI statico)':<28} | {f'R={cores}':<14} | {'0 (0%)':<12} | {format_stat(s_e2b):<20} | {'—':<8} | {'—':<10} | {'—':<10} | {'rif':<8} | {'—':<8}")
        print(f"{'E1c (OpenMP close)':<28} | {f'T={cores}':<14} | {'0 (0%)':<12} | {format_stat(s_e1c):<20} | {'—':<8} | {'—':<10} | {'—':<10} | {'—':<8} | {'rif':<8}")
        print(f"{'E6b (Dyn T=1, c25)':<28} | {f'R={cores} c25':<14} | {'1 core':<12} | {format_stat(s_e6b_25):<20} | {'—':<8} | {'rif':<10} | {'—':<10} | {'—':<8} | {'—':<8}")
        print(f"{'E6b (Dyn T=1, c100)':<28} | {f'R={cores} c100':<14} | {'1 core':<12} | {format_stat(s_e6b_100):<20} | {'—':<8} | {'—':<10} | {'rif':<10} | {'—':<8} | {'—':<8}")

        # E3b configs for this core
        e3b_configs = [k for k in stats_e3b.keys() if k[0] == cores]
        for cfg in e3b_configs:
            s_e3b = stats_e3b[cfg]
            _, r, th = cfg
            print(f"{'E3b (Ibrido statico)':<28} | {f'{r}x{th}':<14} | {'0 (0%)':<12} | {format_stat(s_e3b):<20} | {'rif':<8} | {'—':<10} | {'—':<10} | {'—':<8} | {'—':<8}")

        # E10 configs for this core
        e10_configs = [k for k in stats_e10.keys() if k[0] == cores]
        for cfg in sorted(e10_configs):
            s_e10 = stats_e10[cfg]
            _, r, th, chunk = cfg
            inact = th
            inact_str = f"{inact} ({inact/cores*100:.1f}%)"
            # Matching E3b
            matching_e3b = stats_e3b.get((cores, r, th))
            v_e3b = cmp_verdict(s_e10, matching_e3b)
            v_e6b_25 = cmp_verdict(s_e10, s_e6b_25)
            v_e6b_100 = cmp_verdict(s_e10, s_e6b_100)
            v_e2b = cmp_verdict(s_e10, s_e2b)
            v_e1c = cmp_verdict(s_e10, s_e1c)

            print(f"{f'E10 (Dyn {r}x{th})':<28} | {f'chk={chunk}':<14} | {inact_str:<12} | {format_stat(s_e10):<20} | {v_e3b:<8} | {v_e6b_25:<10} | {v_e6b_100:<10} | {v_e2b:<8} | {v_e1c:<8}")

if __name__ == "__main__":
    main()
