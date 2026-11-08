import pandas as pd
import numpy as np

T1 = 1.063555

cap_df = pd.read_csv("hpc-engine/results/m13/v3_machine_capacity_curve.csv").set_index("p")

def get_s_stats(df, key_col, time_col="time_seconds"):
    res = {}
    for k, grp in df.groupby(key_col):
        t = grp[time_col].values
        s = T1 / t
        res[k] = (float(np.percentile(s, 50)), float(np.percentile(s, 25)), float(np.percentile(s, 75)))
    return res

e1c = pd.read_csv("hpc-engine/results/m13/results_e1c_omp_cores_close.csv")
e2b = pd.read_csv("hpc-engine/results/m13/results_e2b_mpi_map_core.csv")
e3b = pd.read_csv("hpc-engine/results/m13/results_e3b_hybrid_map_core.csv")
e5 = pd.read_csv("hpc-engine/results/m13/results_e5_schedule.csv")
e6b = pd.read_csv("hpc-engine/results/m13/results_e6b_dynamic_map_core.csv")
e10 = pd.read_csv("hpc-engine/results/m13/results_e10_dynamic_hybrid.csv")

s_e1c = get_s_stats(e1c, "threads")
s_e2b = get_s_stats(e2b, "ranks")

# E3b by physical_cores
s_e3b = {}
for (cores, r, th), grp in e3b.groupby(["physical_cores", "ranks", "threads"]):
    t = grp["time_seconds"].values
    s = T1 / t
    s_e3b[(cores, f"{r}x{th}")] = (float(np.percentile(s, 50)), float(np.percentile(s, 25)), float(np.percentile(s, 75)))

# E6b
s_e6b_25 = get_s_stats(e6b[e6b["chunk_size"] == 25], "ranks")
s_e6b_100 = get_s_stats(e6b[e6b["chunk_size"] == 100], "ranks")

# E10
s_e10 = {}
for (cores, r, th, chunk), grp in e10.groupby(["physical_cores", "ranks", "threads", "chunk_size"]):
    t = grp["time_seconds"].values
    s = T1 / t
    s_e10[(cores, f"{r}x{th}", chunk)] = (float(np.percentile(s, 50)), float(np.percentile(s, 25)), float(np.percentile(s, 75)))

# E5 schedules at T=16 and T=20
s_e5 = {}
for (sched, p), grp in e5.groupby(["schedule", "threads"]):
    t = grp["time_seconds"].values
    s = T1 / t
    s_e5[(sched, p)] = (float(np.percentile(s, 50)), float(np.percentile(s, 25)), float(np.percentile(s, 75)))

print("\n=== E1c (OpenMP close) ===")
print(" p | S [IQR]             | C_static | E_cap_static       | C_dyn   | E_cap_dyn")
print("-" * 75)
for p in [1, 2, 4, 6, 8, 10, 12, 14, 16, 20]:
    if p in s_e1c and p in cap_df.index:
        med, q25, q75 = s_e1c[p]
        cs = cap_df.loc[p, "c_static"]
        cd = cap_df.loc[p, "c_dyn"]
        ec_s_med = med / cs * 100
        ec_s_l = q25 / cs * 100
        ec_s_h = q75 / cs * 100
        ec_d_med = med / cd * 100
        ec_d_l = q25 / cd * 100
        ec_d_h = q75 / cd * 100
        print(f"{p:2d} | {med:.2f} [{q25:.2f}-{q75:.2f}] | {cs:8.4f} | {ec_s_med:5.1f}% [{ec_s_l:5.1f}-{ec_s_h:5.1f}%] | {cd:7.4f} | {ec_d_med:5.1f}% [{ec_d_l:5.1f}-{ec_d_h:5.1f}%]")

print("\n=== E2b (MPI map-core) ===")
print(" p | S [IQR]             | C_static | E_cap_static       | C_dyn   | E_cap_dyn")
print("-" * 75)
for p in [1, 2, 4, 6, 8, 10, 12, 14, 16, 20]:
    if p in s_e2b and p in cap_df.index:
        med, q25, q75 = s_e2b[p]
        cs = cap_df.loc[p, "c_static"]
        cd = cap_df.loc[p, "c_dyn"]
        ec_s_med = med / cs * 100
        ec_s_l = q25 / cs * 100
        ec_s_h = q75 / cs * 100
        ec_d_med = med / cd * 100
        ec_d_l = q25 / cd * 100
        ec_d_h = q75 / cd * 100
        print(f"{p:2d} | {med:.2f} [{q25:.2f}-{q75:.2f}] | {cs:8.4f} | {ec_s_med:5.1f}% [{ec_s_l:5.1f}-{ec_s_h:5.1f}%] | {cd:7.4f} | {ec_d_med:5.1f}% [{ec_d_l:5.1f}-{ec_d_h:5.1f}%]")

print("\n=== E6b (Dynamic T=1, c25) ===")
print(" p | S [IQR]             | C_static | E_cap_static       | C_dyn   | E_cap_dyn")
print("-" * 75)
for p in [3, 4, 5, 6, 7, 8, 9, 10, 12, 14]:
    if p in s_e6b_25 and p in cap_df.index:
        med, q25, q75 = s_e6b_25[p]
        cs = cap_df.loc[p, "c_static"]
        cd = cap_df.loc[p, "c_dyn"]
        ec_s_med = med / cs * 100
        ec_s_l = q25 / cs * 100
        ec_s_h = q75 / cs * 100
        ec_d_med = med / cd * 100
        ec_d_l = q25 / cd * 100
        ec_d_h = q75 / cd * 100
        print(f"{p:2d} | {med:.2f} [{q25:.2f}-{q75:.2f}] | {cs:8.4f} | {ec_s_med:5.1f}% [{ec_s_l:5.1f}-{ec_s_h:5.1f}%] | {cd:7.4f} | {ec_d_med:5.1f}% [{ec_d_l:5.1f}-{ec_d_h:5.1f}%]")

print("\n=== E5 Schedules (T=16 e T=20) ===")
for p in [16, 20]:
    cs = cap_df.loc[p, "c_static"]
    cd = cap_df.loc[p, "c_dyn"]
    for sched in ["static", "dynamic", "guided"]:
        # Find matching in s_e5
        matching = [k for k in s_e5.keys() if sched in k[0] and k[1] == p]
        for m in matching:
            med, q25, q75 = s_e5[m]
            ec_s = med / cs * 100
            ec_d = med / cd * 100
            print(f"p={p:2d} | {m[0]:<15} | S={med:.2f} [{q25:.2f}-{q75:.2f}] | E_cap_static={ec_s:5.1f}% | E_cap_dyn={ec_d:5.1f}%")
