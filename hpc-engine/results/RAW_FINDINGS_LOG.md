# RAW FINDINGS LOG — Benchmark HPC, Profiling e PCAM Evaluation
**Milestone M11 / Stadio 11.5**
**Environment ID:** `i7_12700h_20260908`
**Fingerprint File:** `hpc-engine/results/environment_fingerprint_20260908.txt`
**Hardware:** Intel Core i7-12700H (14 core fisici: 6 P-cores + 8 E-cores, 20 thread logici), 31 GiB RAM DDR5, Linux Kernel 7.0.0-31-generic (Ubuntu 24.04 / Zorin OS 18.1).
**Soglia di Non-Oversubscription:** $P_{eff} = N_{nodi} \times N_{thread} \le 20$. Tutte le configurazioni con $P_{eff} > 20$ sono tracciate esplicitamente come `oversubscribed` in tutti i CSV.

> [!NOTE]
> **Nota metodologica su file pilota:**
> Il file `hpc-engine/results/pilot_32x8_5000.csv` rappresenta una singola run pilota preliminare a 32 nodi × 8 thread (batch 5.000, tempo $88.31\text{ ms}$, throughput $56.618,9\text{ sig/s}$) eseguita per validare l'infrastruttura prima del batch di misura, ed è esplicitamente **escluso** dalle tabelle statistiche formali sottostanti.

---

## 1. Decomposition (Decomposizione e Partizionamento)

Il progetto implementa quattro modelli distinti di decomposizione del carico di calcolo, coprendo l'intero spettro Flynn/PCAM:

| Modello | Livello Architetturale | Tipo di Decomposizione | Grana (Granularity) | Meccanismo di Partizionamento | Modulo Implementativo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Data Parallelism (OpenMP)** | Intra-nodo / Intra-processo (Shared Memory) | Domain / Data Decomposition | Fine-grained (loop-level su firme ECDSA) | `#pragma omp parallel for schedule(static)` su `std::vector<Device>` | `hpc-engine/src/onboarding/signature_bench.cpp` |
| **Task Parallelism (MPI)** | Multi-processo distribuito (POSIX Message Passing) | Task Decomposition embarrassingly parallel | Coarse-grained (chunking $W/N$ con resto) | Suddivisione deterministica $base + (1 \text{ if } rank < rem)$ con seed per rank | `hpc-engine/src/mpi_experiment/main_mpi.cpp` |
| **Task Parallelism (gRPC)** | Multi-nodo a microservizi (TCP Network) | Task Decomposition concorrente asincrono | Coarse-grained ($W/N$ firme per container) | Dispatch asincrono `asyncio.gather` verso worker gRPC indipendenti | `hpc-engine/benchmarks/run_full_campaign.py` |
| **Pipeline Parallelism** | Multi-stadio dipendente (Satellite ↔ IoTronic ↔ Worker) | Functional / Pipelined Stream Decomposition | Staged (dipendenza $X_{i+1} = f(X_i)$) | Catena sequenziale a 3 stadi ($k=3$: worker-1 $\to$ worker-2 $\to$ worker-3) con overlap concorrente di richieste | `satellite/app/pipeline_client.py` & `pipeline_throughput_benchmark.py` |

---

## 2. Communication (Pattern di Comunicazione e Overhead)

La comunicazione è stata misurata sia nel contesto isolato (gRPC e MPI) sia nella catena a 3 stadi IoTronic/WAMP:

| Modello | Meccanismo di Trasporto | Topologia di Comunicazione | Volume Dati per Operazione | Overhead di Comunicazione Misurato |
| :--- | :--- | :--- | :--- | :--- |
| **MPI + OpenMP** | POSIX Shared Memory / In-process IPC | Collettiva 1-to-All (`MPI_Barrier`) e All-to-1 (`MPI_Reduce`) | 8 byte per rank (somma interi e max double) | **$< 0.05\text{ ms}$** (irrilevante rispetto al calcolo) |
| **gRPC Isolato (8 nodi)** | HTTP/2 su socket TCP loopback | Fan-out / Fan-in stella (client asincrono verso $N$ worker) | Richiesta RPC ($\sim 100$ B), Risposta RPC ($\sim 120$ B) | **$9.40\text{ ms}$** su batch 1.000 ($50.5\%$ del tempo RPC); **$38.39\text{ ms}$** su batch 5.000 ($45.9\%$) |
| **gRPC Isolato (16 nodi)** | HTTP/2 su socket TCP loopback | Fan-out / Fan-in stella | Idem | **$6.93\text{ ms}$** su batch 1.000 ($54.3\%$ del tempo RPC); **$24.47\text{ ms}$** su batch 5.000 ($46.5\%$) |
| **gRPC Isolato (32 nodi)** | HTTP/2 su socket TCP loopback | Fan-out / Fan-in stella concorrente su 32 canali | Idem | **$9.93\text{ ms}$ - $11.44\text{ ms}$** ($75.5\% - 80.1\%$ del tempo per chiamata) |
| **Pipeline Reale (k=3)** | REST HTTP + WAMP (WebSocket/Crossbar) + gRPC | Catena sequenziale lineare a $k=3$ hop | Payload JSON (`initial_value`, `trace`, token Keystone) | **$210\text{ ms} - 250\text{ ms}$** per stadio ($690\text{ ms}$ totali per transito a vuoto) |

*Fonte dati gRPC e Straggler:* `hpc-engine/results/amdahl_investigation_i7_12700h_20260908.csv`  
*Fonte dati Pipeline:* `hpc-engine/results/pipeline_throughput_i7_12700h_20260908.csv`

---

## 3. Aggregation (Meccanismi di Riduzione e Combinazione)

I risultati parziali prodotti dai task indipendenti o dagli stadi della pipeline vengono aggregati secondo tre paradigmi:

1. **Riduzione Collettiva MPI (`MPI_Reduce`):**
   - Somma algebrica del conteggio firme verificate: `MPI_Reduce(&local_res.batch_size, &total_verified, 1, MPI_UNSIGNED_LONG_LONG, MPI_SUM, 0, MPI_COMM_WORLD)`.
   - Riduzione al massimo per il tempo di esecuzione: `MPI_Reduce(&local_res.time_seconds, &max_time, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD)`.
   - Latenza di aggregazione: $O(\log_2 P)$, dominata da primitive vettoriali CPU in-process.

2. **Aggregazione Asincrona Client-Side (Satellite / Driver gRPC):**
   - Rientro concorrente via `asyncio.gather(*tasks)`.
   - Check di consistenza: $\sum_{i=1}^N \text{valid\_count}_i == \text{total\_batch}$ con validazione stringente al 100%.
   - Tempo globale misurato come intervallo wall-clock $T_{tot} = t_{end} - t_{start} = \max_i(T_i + \text{jitter}_i)$.

3. **Incatenamento Sequenziale Dato-a-Dato (Pipeline Stream):**
   - L'output di ciascuno stadio $S_i$ (valore intero e record di traccia firmato) costituisce direttamente l'input dello stadio successivo $S_{i+1}$.
   - Aggregazione incrementale di audit trail (`trace`: lista ordinata con `node_id`, `timestamp`, `output`, `raw_response`).

---

## 4. Mapping (Mappatura su Hardware e Architettura di Esecuzione)

- **Hardware Fisico:** Processore ibrido Intel Alder Lake (6 Performance Cores con Hyper-Threading = 12 thread logici, 8 Efficient Cores mono-thread = 8 thread logici, totale 20 core logici).
- **Binding Processi MPI:** Esecuzione con policy `--bind-to none` per consentire ai thread OpenMP di ciascun rank di migrare liberamente tra i core logici disponibili, superando la limitazione di default di Open MPI (che vincolava ogni processo a un singolo core).
- **Mappatura Container gRPC:** 32 container Docker isolati (`bench-worker-1..32`), ciascuno in ascolto sulla porta interna 50051 e mappato su un range di porte host dedicate non sovrapposte (`51051` - `51082`).
- **Mappatura Board IoTronic:** Mappatura 1-a-1 fissa tra le 3 board Lightning-Rod registrate su IoTronic e i 3 container worker C++ di produzione (`worker-1`, `worker-2`, `worker-3`) collegati tramite rete bridge `s4t-bridge`.

---

## 5. Performance Evaluation (Dati Sperimentali Misurati)

Tutti i numeri riportati provengono da misurazioni reali eseguite nella medesima sessione sull'ambiente `i7_12700h_20260908`.

### 5.1 Flat Profile della Baseline Sequenziale (Task A)
*File sorgente:* `hpc-engine/results/profile_i7_12700h_20260908.txt`
- Profiler: Valgrind Callgrind 3.22.0 con pacchetto simboli di debug `libssl3t64-dbgsym`.
- Totale istruzioni simulate: **$1.181.840.654\text{ Ir}$** (batch 500, 1 thread).
- **Aritmetica EC / BIGNUM (OpenSSL):** **$87.88\%$** ($1.038.637.233\text{ Ir}$)
  - `__ecp_nistz256_mul_montq`: $32.71\%$
  - `__ecp_nistz256_sqr_montq`: $19.97\%$
  - `ecp_nistz256_ord_sqr_mont`: $5.91\%$
  - `ecp_nistz256_point_double`: $4.03\%$
  - Operazioni BIGNUM (`BN_uadd`, `bn_div`, ecc.): $7.10\%$
- **Altro calcolo crittografico (SHA digest, parametri EVP):** **$6.26\%$**
- **Calcolo Crittografico Complessivo:** **$94.14\%$** ($>90\%$ atteso confermato empiricamente).
- **Gestione dinamica memoria (`malloc`/`free`):** **$3.20\%$**.
- **Codice applicativo harness del progetto:** **$1.80\%$**.

---

### 5.2 Griglia Completa Nodi × Thread — gRPC Isolato (Task B)
*File sorgente:* `hpc-engine/results/grid_grpc_i7_12700h_20260908.csv`  
*Sintesi:* 48 combinazioni testate (nodi $\in \{1,2,4,8,16,32\}$, thread $\in \{1,2,4,8\}$, batch $\in \{1000, 5000\}$), 3 ripetizioni ciascuna con validazione 100% su `valid_count`.

#### Estratto Batch Size = 1.000 firme (gRPC)
| Nodi ($N$) | Thread ($T$) | $P_{eff}$ | Stato | Tempo Medio (s) | StdDev (s) | Throughput Medio (sig/s) | Throughput Massimo (sig/s) | Speedup Medio |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 1 | 1 | CLEAN | 0.1244 | 0.0323 | 8.364,1 | 9.460,7 | 1.00x |
| 1 | 2 | 2 | CLEAN | 0.0793 | 0.0017 | 12.610,7 | 12.889,6 | 1.57x |
| 1 | 4 | 4 | CLEAN | 0.0724 | 0.0055 | 13.873,2 | 14.770,2 | 1.72x |
| 1 | 8 | 8 | CLEAN | 0.0597 | 0.0004 | 16.738,2 | 16.804,4 | 2.08x |
| 2 | 4 | 8 | CLEAN | 0.0456 | 0.0076 | 22.336,0 | 26.237,7 | 2.73x |
| 4 | 2 | 8 | CLEAN | 0.0358 | 0.0023 | 28.032,2 | 29.628,8 | 3.48x |
| 4 | 4 | 16 | CLEAN | 0.0307 | 0.0021 | 32.707,9 | 35.431,5 | 4.06x |
| 8 | 1 | 8 | CLEAN | 0.0261 | 0.0011 | 38.301,5 | 39.409,6 | 4.76x |
| 8 | 2 | 16 | CLEAN | 0.0294 | 0.0158 | 39.914,0 | 50.363,2 | 4.24x |
| 8 | 8 | 64 | OVERSUB | 0.0204 | 0.0025 | 49.362,5 | 52.956,7 | 6.09x |
| 16 | 1 | 16 | CLEAN | 0.0278 | 0.0161 | 43.769,9 | 62.489,4 | 4.48x |
| 16 | 8 | 128 | OVERSUB | 0.0160 | 0.0005 | 62.663,1 | 65.137,7 | 7.79x |
| 32 | 1 | 32 | OVERSUB | 0.0274 | 0.0116 | 40.558,7 | 53.894,5 | 4.54x |
| 32 | 8 | 256 | OVERSUB | 0.0265 | 0.0085 | 40.034,6 | 46.702,3 | 4.69x |

#### Estratto Batch Size = 5.000 firme (gRPC)
| Nodi ($N$) | Thread ($T$) | $P_{eff}$ | Stato | Tempo Medio (s) | StdDev (s) | Throughput Medio (sig/s) | Throughput Massimo (sig/s) | Speedup Medio |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 1 | 1 | CLEAN | 0.4989 | 0.0136 | 10.027,9 | 10.260,6 | 1.00x |
| 1 | 2 | 2 | CLEAN | 0.3858 | 0.0103 | 12.967,4 | 13.359,4 | 1.29x |
| 1 | 8 | 8 | CLEAN | 0.2839 | 0.0085 | 17.625,6 | 18.243,9 | 1.76x |
| 2 | 4 | 8 | CLEAN | 0.1611 | 0.0021 | 31.047,2 | 31.519,1 | 3.10x |
| 4 | 4 | 16 | CLEAN | 0.0999 | 0.0077 | 50.224,7 | 52.977,3 | 5.01x |
| 8 | 1 | 8 | CLEAN | 0.1041 | 0.0022 | 48.070,5 | 49.163,0 | 4.79x |
| 8 | 2 | 16 | CLEAN | 0.0904 | 0.0036 | 55.392,1 | 57.031,1 | 5.52x |
| 8 | 4 | 32 | OVERSUB | 0.0732 | 0.0009 | 68.346,6 | 69.004,0 | 6.82x |
| 16 | 1 | 16 | CLEAN | 0.0693 | 0.0072 | 72.699,7 | 77.119,3 | 7.20x |
| 16 | 2 | 32 | OVERSUB | 0.0634 | 0.0035 | 78.989,2 | **82.178,1** | **7.87x** |
| 16 | 8 | 128 | OVERSUB | 0.0641 | 0.0033 | 78.088,9 | **82.467,0** | **7.78x** |
| 32 | 1 | 32 | OVERSUB | 0.0823 | 0.0262 | 64.468,0 | 75.197,7 | 6.06x |
| 32 | 8 | 256 | OVERSUB | 0.0634 | 0.0013 | 78.882,3 | 80.805,9 | 7.87x |

---

### 5.3 Griglia Completa Nodi × Thread — Ibrido MPI + OpenMP (Task B)
*File sorgente:* `hpc-engine/results/grid_mpi_omp_i7_12700h_20260908.csv`  
*Sintesi:* 48 combinazioni testate (rank MPI $\in \{1,2,4,8,16,32\}$, thread OpenMP $\in \{1,2,4,8\}$, batch $\in \{1000, 5000\}$), 3 ripetizioni ciascuna con `--bind-to none` e `--oversubscribe`.

#### Estratto Batch Size = 5.000 firme (MPI+OpenMP)
| Rank ($P$) | Thread ($T$) | $P_{eff}$ | Stato | Tempo Medio (s) | StdDev (s) | Throughput Medio (sig/s) | Throughput Massimo (sig/s) | Speedup Medio |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 1 | 1 | CLEAN | 0.3315 | 0.0640 | 15.426,2 | 17.098,2 | 1.00x |
| 1 | 2 | 2 | CLEAN | 0.1820 | 0.0176 | 27.632,8 | 29.897,2 | 1.82x |
| 1 | 8 | 8 | CLEAN | 0.0722 | 0.0005 | 69.299,2 | 69.640,1 | 4.59x |
| 2 | 8 | 16 | CLEAN | 0.0370 | 0.0011 | 135.323,0 | 137.971,0 | 8.97x |
| 4 | 4 | 16 | CLEAN | 0.0461 | 0.0089 | 111.476,8 | 139.059,0 | 7.19x |
| 8 | 2 | 16 | CLEAN | 0.0385 | 0.0028 | 130.294,0 | 137.439,0 | 8.61x |
| 8 | 8 | 64 | OVERSUB | 0.0356 | 0.0024 | 140.735,0 | 151.514,0 | 9.30x |
| 16 | 1 | 16 | CLEAN | 0.0362 | 0.0013 | 138.321,7 | 141.593,0 | 9.16x |
| 16 | 8 | 128 | OVERSUB | 0.0349 | 0.0008 | 143.315,7 | 145.843,0 | 9.50x |
| 32 | 4 | 128 | OVERSUB | 0.0339 | 0.0037 | 148.531,0 | **163.922,0** | **9.78x** |
| 32 | 8 | 256 | OVERSUB | 0.0338 | 0.0032 | 148.927,0 | 157.067,0 | **9.81x** |

---

### 5.4 Throughput Pipelining su Catena Reale a 3 Stadi (Task D)
*File sorgente:* `hpc-engine/results/pipeline_throughput_i7_12700h_20260908.csv`  
*Sintesi:* Catena sequenziale reale Satellite $\to$ IoTronic/Lightning-Rod $\to$ Worker-1 $\to$ Worker-2 $\to$ Worker-3 ($k=3$), testata per $n \in \{1, 2, 4, 8\}$ con 5 ripetizioni per valore.

| Richieste Concorrenti ($n$) | $T_{seq}$ Mediana (s) | $T_{seq}$ StdDev (s) | $T_{conc}$ Mediana (s) | $T_{conc}$ StdDev (s) | Speedup Misurato ($S_{mis}$) | Speedup Predetto ($S_{pred}$) | Scarto Relativo (\%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 0.690 | 2.271 | 0.708 | 0.044 | **0.97x** | 1.00x | 2.7% |
| **2** | 1.386 | 0.118 | 0.997 | 0.183 | **1.39x** | 1.50x | 7.3% |
| **4** | 2.635 | 0.110 | 1.999 | 0.097 | **1.32x** | 2.00x | 34.1% |
| **8** | 5.584 | 0.101 | 3.532 | 0.130 | **1.58x** | 2.40x | 34.1% |

*Formula teorica adottata:* $S(n, k) = \frac{n \cdot k}{k + n - 1}$ con $k=3$.

---

## 6. Appendice — Anomalie Investigate

### 6.1 Investigazione dell'Anomalia di Amdahl a 8, 16 e 32 Nodi (Task C)
*File sorgente:* `hpc-engine/results/amdahl_investigation_i7_12700h_20260908.csv`  
*Campione:* 12 configurazioni analizzate su **10 ripetizioni ciascuna** (120 round complessivi), registrando singolarmente per ogni chiamata: tempo di calcolo C++ restituito dal worker (`worker_time_seconds`) e latenza RPC totale percepita dal client (`rpc_latency_seconds`).

#### Risultati della Scomposizione di Overhead su 10 Run:
| Configurazione ($N$, $T$, Batch) | Tempo Totale Mediano (ms) | Tempo Calcolo C++ Medio (ms) | Overhead Rete Medio per Chiamata (ms) | Frazione Overhead su Chiamata (\%) | Throughput Mediano (sig/s) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| $N=8, T=1$, Batch 1.000 | 28.45 | 9.23 | 9.40 | **50.5%** | 35.150,3 |
| $N=8, T=1$, Batch 5.000 | 117.04 | 45.43 | 38.39 | **45.9%** | 42.735,3 |
| $N=8, T=8$, Batch 1.000 | 18.08 | 3.60 | 9.63 | **72.8%** | 55.305,0 |
| $N=8, T=8$, Batch 5.000 | 71.90 | 17.19 | 39.25 | **69.6%** | 69.550,4 |
| $N=16, T=1$, Batch 1.000 | 18.12 | 5.83 | 6.93 | **54.3%** | 55.220,4 |
| $N=16, T=1$, Batch 5.000 | 64.68 | 28.13 | 24.47 | **46.5%** | 77.301,3 |
| $N=16, T=8$, Batch 1.000 | 15.71 | 3.97 | 8.03 | **66.7%** | 63.672,1 |
| $N=16, T=8$, Batch 5.000 | 57.31 | 18.24 | 29.58 | **61.9%** | 87.239,7 |
| $N=32, T=1$, Batch 1.000 | 18.77 | 3.22 | 9.93 | **75.5%** | 53.280,5 |
| $N=32, T=1$, Batch 5.000 | 67.10 | 17.29 | 28.68 | **62.3%** | 74.520,7 |
| $N=32, T=8$, Batch 1.000 | 18.85 | 2.84 | 11.44 | **80.1%** | 53.075,9 |
| $N=32, T=8$, Batch 5.000 | 57.31 | 13.06 | 31.88 | **71.0%** | 87.252,8 |

#### Verdetto Formale Task C:
- **(b) Fenomeno Reale e Strutturale (Confermato con Evidenza Numerica):**
  L'anomalia dello scarto tra lo speedup teorico di Amdahl ($S_{pred} \approx \frac{1}{f_s + (1-f_s)/P}$) e lo speedup misurato non è un artefatto di misura né un errore di campionamento.
  1. **Dominanza dell'Overhead Fisso:** Quando la dimensione del chunk per worker decresce (es. $5.000 / 32 = 156$ firme, o $1.000 / 32 = 31$ firme), il calcolo utile crolla a soli **$2.84\text{ ms} - 13.06\text{ ms}$**. L'overhead di coordinamento di rete (framing HTTP/2, multiplexing TCP gRPC, latenza di dispatch) si attesta invece a **$11.44\text{ ms} - 31.88\text{ ms}$**, rappresentando tra il **$71\%$ e l' $80\%$** dell'intera durata della chiamata RPC.
  2. **Straggler Tail Effect:** Il tempo aggregato è governato da $T_{tot} = \max_i(T_i)$. Con 32 canali concorrenti in regime oversubscribed ($P_{eff}=256$), la probabilità che almeno un socket sperimenti jitter di scheduling del kernel è prossima al $100\%$, fissando un asintoto di throughput a $\approx 80.000 - 87.000\text{ sig/s}$ oltre il quale la scalabilità di Amdahl convenzionale non è applicabile senza modellare il costo di comunicazione $O(P)$.

---

### 6.2 Investigazione dello Scarto nel Pipelining su Catena Reale (Task D)
- **Osservazione:** A $n=2$, il modello predice $1.50\times$ e la misura registra $1.39\times$ ($7.3\%$ scarto). A $n=4$ e $n=8$, lo speedup teorico salirebbe a $2.00\times$ e $2.40\times$, mentre la misura si stabilizza a **$1.32\times$** e **$1.58\times$** (scarto costante del $34.1\%$).
- **Fattori Investigati:**
  1. *Presenza di Lock nel Satellite:* Escluso. Il codice di `pipeline_client.py` invoca chiamate REST asincrone non bloccanti con `httpx.AsyncClient`.
  2. *Contesa e Serializzazione sul Worker:* **Causa primaria accertata.** In assenza di un pipeline queue scheduler centralizzato che sfasi le chiamate lungo gli stadi, le $n$ richieste inoltrate simultaneamente con `asyncio.gather` competono tutte contemporaneamente per il medesimo primo stadio (`worker-1`), accodandosi sulla coda WAMP/Lightning-Rod della prima board. Il pipelining opera come una sequenza di burst sovrapposti ma soggetti a head-of-line blocking al primo stadio, ammortizzandosi solo parzialmente man mano che i pacchetti avanzano sugli stadi 2 e 3.
  3. *Verdetto:* Risultato riproducibile e coerente con la natura del sistema a microservizi asincrono IoTronic. Confermato che la concorrenza asincrona approssima il pipelining fino a $\sim 1.6\times$ pur senza uno scheduler hardware dedicato.
