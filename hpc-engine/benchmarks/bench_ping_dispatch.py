#!/usr/bin/env python3
"""
V1.3: Measure fixed gRPC network / async dispatch cost without computation using Ping RPC.
Targets k concurrent containers (k = 1, 2, 4, 8, 16, 20, 32), with 10 repetitions each.
"""

import sys
import time
import asyncio
import csv
from pathlib import Path
from typing import List, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "hpc-engine" / "results" / "m13"
PROTO_DIR = REPO_ROOT / "satellite" / "app"

if str(PROTO_DIR) not in sys.path:
    sys.path.insert(0, str(PROTO_DIR))

try:
    import grpc
    import pipeline_pb2
    import pipeline_pb2_grpc
    from google.protobuf.empty_pb2 import Empty
except ImportError:
    venv_py = REPO_ROOT / "satellite" / "venv" / "lib" / "python3.12" / "site-packages"
    if venv_py.exists() and str(venv_py) not in sys.path:
        sys.path.insert(0, str(venv_py))
    import grpc
    import pipeline_pb2
    import pipeline_pb2_grpc
    from google.protobuf.empty_pb2 import Empty

ALL_WORKERS = [f"127.0.0.1:{51051 + i}" for i in range(32)]

async def ping_single(addr: str, timeout: float = 5.0) -> float:
    async with grpc.aio.insecure_channel(addr) as channel:
        stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
        t0 = time.perf_counter()
        resp = await stub.Ping(Empty(), timeout=timeout)
        t1 = time.perf_counter()
        if not resp.healthy:
            raise RuntimeError(f"Unhealthy ping response from {addr}")
        return t1 - t0

async def ping_batch(addrs: List[str]) -> float:
    tasks = [ping_single(addr) for addr in addrs]
    t0 = time.perf_counter()
    await asyncio.gather(*tasks)
    t1 = time.perf_counter()
    return t1 - t0

def main():
    k_list = [1, 2, 4, 8, 16, 20, 32]
    repeats = 10
    out_csv = RESULTS_DIR / "v1_ping_dispatch.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    print("==========================================================")
    print(" V1.3: gRPC Concurrent Ping Dispatch Benchmark")
    print(" Target: Measure network/dispatch cost without computation")
    print(f" Output: {out_csv}")
    print("==========================================================\n")

    # Warmup all 32
    print("[*] Performing warmup ping across all 32 containers...")
    asyncio.run(ping_batch(ALL_WORKERS))
    print("[+] Warmup complete.\n")

    results = []
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["k", "rep", "time_seconds"])

        for k in k_list:
            addrs = ALL_WORKERS[:k]
            times = []
            for rep in range(repeats):
                dur = asyncio.run(ping_batch(addrs))
                times.append(dur)
                writer.writerow([k, rep, f"{dur:.6f}"])
                f.flush()

            times.sort()
            med = (times[4] + times[5]) / 2.0
            p25 = times[2]
            p75 = times[7]
            iqr = p75 - p25
            print(f"  k = {k:2d} | Ping Wall Time: median = {med*1000:6.2f} ms (IQR = {iqr*1000:5.2f} ms)")

    print(f"\n[+] Raw results written to {out_csv}")

if __name__ == "__main__":
    main()
