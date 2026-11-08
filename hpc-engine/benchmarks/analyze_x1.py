import pandas as pd
import numpy as np

e2b = pd.read_csv("hpc-engine/results/m13/results_e2b_mpi_map_core.csv")
e6b = pd.read_csv("hpc-engine/results/m13/results_e6b_dynamic_map_core.csv")

T1 = 1.063555

def get_stats(df, rank_col="ranks", time_col="time_seconds"):
    res = {}
    for r, grp in df.groupby(rank_col):
        t = grp[time_col].values
        s = T1 / t
        q25 = float(np.percentile(s, 25))
        med = float(np.percentile(s, 50))
        q75 = float(np.percentile(s, 75))
        res[r] = (med, q25, q75, q75 - q25)
    return res

stats_e2b = get_stats(e2b)

e6b_c25 = e6b[e6b["chunk_size"] == 25]
e6b_c100 = e6b[e6b["chunk_size"] == 100]

stats_e6b_25 = get_stats(e6b_c25)
stats_e6b_100 = get_stats(e6b_c100)

print(f"{'R':>2} | {'E2b S (static)':<20} | {'S/R':>5} | {'E6b c25 S':<20} | {'S/R':>5} | {'Cmp25':<15} | {'E6b c100 S':<20} | {'S/R':>5} | {'Cmp100':<15}")
print("-" * 135)

ranks = sorted(list(set(list(stats_e2b.keys()) + list(stats_e6b_25.keys()))))
for r in ranks:
    s_e2b_str = "N/A"
    sr_e2b_str = "N/A"
    e2b_tuple = stats_e2b.get(r)
    if e2b_tuple:
        med, q25, q75, iqr = e2b_tuple
        s_e2b_str = f"{med:.2f} [{q25:.2f}-{q75:.2f}]"
        sr_e2b_str = f"{med/r:.3f}"

    def cmp_str(e6b_tuple, e2b_tuple):
        if not e6b_tuple or not e2b_tuple:
            return "N/A"
        m1, l1, h1, _ = e6b_tuple
        m2, l2, h2, _ = e2b_tuple
        if l1 > h2:
            return "Vince E6b"
        elif h1 < l2:
            return "Perde E6b"
        else:
            return "Indistinguibile"

    # c25
    t25 = stats_e6b_25.get(r)
    s25_str = "N/A"
    sr25_str = "N/A"
    c25_cmp = "N/A"
    if t25:
        med, q25, q75, iqr = t25
        s25_str = f"{med:.2f} [{q25:.2f}-{q75:.2f}]"
        sr25_str = f"{med/r:.3f}"
        c25_cmp = cmp_str(t25, e2b_tuple)

    # c100
    t100 = stats_e6b_100.get(r)
    s100_str = "N/A"
    sr100_str = "N/A"
    c100_cmp = "N/A"
    if t100:
        med, q25, q75, iqr = t100
        s100_str = f"{med:.2f} [{q25:.2f}-{q75:.2f}]"
        sr100_str = f"{med/r:.3f}"
        c100_cmp = cmp_str(t100, e2b_tuple)

    print(f"{r:2d} | {s_e2b_str:<20} | {sr_e2b_str:>5} | {s25_str:<20} | {sr25_str:>5} | {c25_cmp:<15} | {s100_str:<20} | {sr100_str:>5} | {c100_cmp:<15}")

