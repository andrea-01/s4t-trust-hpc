import pandas as pd
import numpy as np

df = pd.read_csv("hpc-engine/results/m13/results_e4c_smt_ecore_discrim.csv")

def stats(s):
    med = float(np.percentile(s, 50))
    q25 = float(np.percentile(s, 25))
    q75 = float(np.percentile(s, 75))
    return f"{med:.4f} [{q25:.4f}-{q75:.4f}]"

def stats_ms(s):
    med = float(np.percentile(s, 50)) * 1000.0
    q25 = float(np.percentile(s, 25)) * 1000.0
    q75 = float(np.percentile(s, 75)) * 1000.0
    return f"{med:.1f} [{q25:.1f}-{q75:.1f}]"

print(f"{'Config':<12} | {'p':>2} | {'T_wall (s)':<22} | {'verify_s (s)':<22} | {'gen_est (s)':>11} | {'ping (ms)':>9} | {'residuo (ms)':<22} | {'tp (sig/s)':>10}")
print("-" * 125)

for name, grp in df.groupby("config_name", sort=False):
    p = int(grp["p"].iloc[0])
    wall_str = stats(grp["wall_s"])
    ver_str = stats(grp["verify_s"])
    gen_est = float(grp["gen_est_s"].iloc[0])
    ping_ms = float(grp["ping_s"].iloc[0]) * 1000.0
    res_ms_str = stats_ms(grp["residual_s"])
    tp_med = float(np.percentile(grp["throughput"], 50))
    print(f"{name:<12} | {p:2d} | {wall_str:<22} | {ver_str:<22} | {gen_est:11.4f} | {ping_ms:8.1f} | {res_ms_str:<22} | {tp_med:10.1f}")

