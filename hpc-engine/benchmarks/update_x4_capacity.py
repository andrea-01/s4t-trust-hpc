import pandas as pd
import numpy as np

T1_E0b = 1.063555
v_E0b = 20000.0 / T1_E0b

df = pd.read_csv("hpc-engine/results/m13/results_e9b_capacity_fill.csv")

print(f"Baseline v_E0b = {v_E0b:.2f} sig/s (T1 = {T1_E0b:.6f} s)")
print(" q |  C_static(q)  |    C_dyn(q)   |  C_model(q)")
print("-" * 50)

rows = []
for q in range(1, 21):
    sub = df[df["q"] == q]
    tp_s = sub["throughput_static"].values
    tp_d = sub["throughput_dyn"].values
    c_s = float(np.percentile(tp_s, 50)) / v_E0b
    c_d = float(np.percentile(tp_d, 50)) / v_E0b
    
    # Model from isolated measurements:
    # 6 P-cores + 8 E-cores + 6 SMT
    if q <= 6:
        c_mod = float(q)
    elif q <= 14:
        c_mod = 6.0 + (q - 6) * 0.5081
    else:
        c_mod = 6.0 + 8 * 0.5081 + (q - 14) * 0.1999

    rows.append({"p": q, "c_static": round(c_s, 4), "c_dyn": round(c_d, 4), "c_model": round(c_mod, 4)})
    print(f"{q:2d} | {c_s:12.4f}  | {c_d:12.4f}  | {c_mod:10.4f}")

out_df = pd.DataFrame(rows)
out_df.to_csv("hpc-engine/results/m13/v3_machine_capacity_curve.csv", index=False)
print("[+] Successfully updated hpc-engine/results/m13/v3_machine_capacity_curve.csv")
