"""
Misura del pipeline speedup (throughput) sulla catena sequenziale
satellite -> worker-1 -> worker-2 -> worker-3 (k=3 stadi).

Metodologia: non serve nessuna infrastruttura nuova. La catena a 3 stadi
esiste gia' (M6); questo script la usa esattamente come nella demo, con
un'unica differenza: invece di inviare N richieste `/run` una alla volta
(attese in sequenza), le invia CONCORRENTEMENTE con asyncio.gather.

Se il satellite (FastAPI, asincrono) e i worker (gRPC, stateless) gestiscono
correttamente richieste indipendenti in overlap, il tempo totale per N
richieste concorrenti dovrebbe avvicinarsi a quello dato dalla formula del
corso per un pipeline a k stadi:

    S(n, k) = n * k / (k + n - 1)

dove n = numero di richieste indipendenti fatte scorrere nella pipeline,
k = numero di stadi (3, qui). Questo script calcola sia lo speedup
PREDETTO da questa formula sia quello MISURATO (T_sequenziale / T_concorrente),
esattamente come gia' fatto per la legge di Amdahl in M11.3 -- stesso
principio, "confronto esplicito predetto vs misurato", applicato al
pipelining invece che al task parallelism.

NOTA IMPORTANTE (onestà sperimentale, da riportare nel report):
Questo NON è un pipeline scheduler esplicito -- non c'è un componente che
assegna deliberatamente stadi diversi a batch diversi in overlap. È una
misura di quanto la concorrenza asincrona già presente nell'infrastruttura
(satellite FastAPI + worker gRPC stateless) approssima naturalmente il
comportamento di un pipeline a k stadi. Se il risultato si discosta molto
dalla formula, la causa più probabile non è un errore di misura ma un
collo di bottiglia reale (es. un lock/risorsa condivisa nel satellite che
serializza le richieste concorrenti) -- in tal caso va investigato e
riportato, non nascosto, seguendo lo stesso standard già applicato ai tre
episodi di verifica sperimentale del report (build non ottimizzata, CPU
binding OpenMPI, straggler tail effect).

Uso:
    python3 pipeline_throughput_benchmark.py --satellite-url http://localhost:8001 \
        --pipeline-id <id-gia-leasato-con-3-nodi> --n-values 1,2,4,8 --repeats 3
"""

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass
class RunResult:
    n: int
    t_sequential: float
    t_concurrent: float
    speedup_measured: float
    speedup_predicted: float


def predicted_pipeline_speedup(n: int, k: int) -> float:
    """S(n, k) = n * k / (k + n - 1) -- formula esatta del corso."""
    return (n * k) / (k + n - 1)


async def run_once(client: httpx.AsyncClient, base_url: str, pipeline_id: str, initial_value: int) -> float:
    t0 = time.perf_counter()
    resp = await client.post(
        f"{base_url}/pipeline/{pipeline_id}/run",
        json={"initial_value": initial_value},
        timeout=60.0,
    )
    resp.raise_for_status()
    return time.perf_counter() - t0


async def measure_sequential(client: httpx.AsyncClient, base_url: str, pipeline_id: str, n: int) -> float:
    t0 = time.perf_counter()
    for i in range(n):
        await run_once(client, base_url, pipeline_id, initial_value=i)
    return time.perf_counter() - t0


async def measure_concurrent(client: httpx.AsyncClient, base_url: str, pipeline_id: str, n: int) -> float:
    t0 = time.perf_counter()
    await asyncio.gather(*[
        run_once(client, base_url, pipeline_id, initial_value=i) for i in range(n)
    ])
    return time.perf_counter() - t0


async def main_async(base_url: str, pipeline_id: str, n_values: list[int], repeats: int, k_stages: int, output_csv: str = None, env_id: str = "i7_12700h_20260908"):
    results: list[dict] = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        # warmup, come nella metodologia gia' usata in M11.3
        print(f"[*] Warming up pipeline {pipeline_id}...")
        await run_once(client, base_url, pipeline_id, initial_value=-1)
        print("[+] Warmup complete. Starting measurements...\n")

        for n in n_values:
            seq_times, conc_times = [], []
            print(f">>> Testing n={n} ({repeats} repeats) <<<")
            for rep in range(repeats):
                t_s = await measure_sequential(client, base_url, pipeline_id, n)
                t_c = await measure_concurrent(client, base_url, pipeline_id, n)
                seq_times.append(t_s)
                conc_times.append(t_c)
                print(f"  [rep {rep+1}/{repeats}] T_seq={t_s:6.3f}s | T_conc={t_c:6.3f}s | Speedup={t_s/t_c if t_c>0 else 0:5.2f}x")

            t_seq_med = statistics.median(seq_times)
            t_seq_mean = statistics.mean(seq_times)
            t_seq_std = statistics.stdev(seq_times) if len(seq_times) > 1 else 0.0

            t_conc_med = statistics.median(conc_times)
            t_conc_mean = statistics.mean(conc_times)
            t_conc_std = statistics.stdev(conc_times) if len(conc_times) > 1 else 0.0

            speedup_measured = t_seq_med / t_conc_med if t_conc_med > 0 else float("nan")
            speedup_predicted = predicted_pipeline_speedup(n, k_stages)
            err_pct = abs(speedup_measured - speedup_predicted) / speedup_predicted * 100

            results.append({
                "env_id": env_id,
                "n": n,
                "k_stages": k_stages,
                "t_sequential_median_s": t_seq_med,
                "t_sequential_mean_s": t_seq_mean,
                "t_sequential_stddev_s": t_seq_std,
                "t_concurrent_median_s": t_conc_med,
                "t_concurrent_mean_s": t_conc_mean,
                "t_concurrent_stddev_s": t_conc_std,
                "speedup_measured": speedup_measured,
                "speedup_predicted": speedup_predicted,
                "error_percent": err_pct
            })
            print(
                f"  ==> Summary n={n:>2}: T_seq_med={t_seq_med:6.3f}s (±{t_seq_std:5.3f}) | "
                f"T_conc_med={t_conc_med:6.3f}s (±{t_conc_std:5.3f}) | "
                f"Speedup_misurato={speedup_measured:5.2f}x | "
                f"Speedup_predetto(k={k_stages})={speedup_predicted:5.2f}x | "
                f"Errore={err_pct:5.1f}%\n"
            )

    if output_csv:
        import csv
        from pathlib import Path
        out_path = Path(output_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            for r in results:
                writer.writerow(r)
        print(f"[+] Saved results to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--satellite-url", default="http://localhost:8001")
    parser.add_argument("--pipeline-id", required=True, help="ID di un pipeline gia' leasato (POST /pipeline/lease)")
    parser.add_argument("--n-values", default="1,2,4,8", help="Numero di richieste concorrenti da testare")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--k-stages", type=int, default=3, help="Numero di stadi della pipeline (worker-1/2/3 = 3)")
    parser.add_argument("--output-csv", default=None, help="Path di output del CSV")
    parser.add_argument("--env-id", default="i7_12700h_20260908", help="Environment ID")
    args = parser.parse_args()

    n_values = [int(x) for x in args.n_values.split(",")]
    asyncio.run(main_async(args.satellite_url, args.pipeline_id, n_values, args.repeats, args.k_stages, args.output_csv, args.env_id))


if __name__ == "__main__":
    main()
