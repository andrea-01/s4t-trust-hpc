# HPC Engine - Benchmark di Verifica Firme Parallele (M5)

Questo modulo esegue un benchmark isolato C++ per valutare l'accelerazione ottenibile parallelizzando la verifica di firme ECDSA (curva P-256) tramite **OpenMP**. Il modulo non richiede la blockchain ed è inteso per la validazione delle prestazioni.

## Compilazione

Il modulo è configurato per l'esecuzione tramite un container Docker per fornire una toolchain isolata (`g++` >= 13, `cmake`, `libssl-dev`).

Per compilare:
```bash
docker build -t hpc-engine-build .
docker run --rm -v $(pwd):/app -w /app hpc-engine-build bash -c "mkdir -p build && cd build && cmake .. && make -j"
```

Per eseguire i test (verificano la corretta implementazione OpenSSL 3.x con firme valide, invalidate e messaggi alterati):
```bash
docker run --rm -v $(pwd):/app -w /app hpc-engine-build bash -c "cd build && ctest -V"
```

## Esecuzione del Benchmark

L'eseguibile accetta argomenti posizionali: dimensione dataset, range dei batch size e range del numero dei thread.

```bash
docker run --rm -v $(pwd):/app -w /app hpc-engine-build bash -c "cd build && ./hpc_engine_bench 500 \"100,250,500\" \"1,2,4,8\" results.csv"
```

## Interpretazione dei Risultati

Nel run di riferimento su un batch massimo di 500 device sintetici, la baseline sequenziale processa circa **18,000 firme al secondo**.

- **1 thread (sequenziale/parallelo con 1 thread)**: ~17,700 sigs/sec
- **2 threads**: ~23,200 sigs/sec
- **4 threads**: ~35,400 sigs/sec
- **8 threads**: ~67,400 sigs/sec

La scalabilità sub-lineare riscontrata nel passaggio da 1 a 2 thread (speedup di ~1.3x invece di ~2.0x, su un sistema a 20 core totali validato via `nproc`) è **verosimilmente** riconducibile al sovraccarico di allocazione e lock contention causato da `EVP_MD_CTX_new()`. Attualmente, il contesto OpenSSL viene allocato e deallocato **per ogni singola verifica** all'interno del loop OpenMP; si tratta tuttavia di un'ipotesi plausibile in attesa di misurazioni sperimentali dedicate.

**Nota di Ottimizzazione Futura:**
Per ottenere uno scaling perfettamente lineare (imbarazzantemente parallelo) occorre implementare il *context reuse per thread*. Ciò comporterebbe l'allocazione di un singolo `EVP_MD_CTX` per ciascun thread OpenMP (usando, ad esempio, strutture thread-local o array preallocati in base all'ID del thread) e l'uso di `EVP_DigestVerifyInit()` per resettare lo stesso contesto ad ogni interazione, abbattendo drasticamente l'overhead del gestore della memoria di sistema.

Nonostante questo collo di bottiglia, scalando a 4 e 8 thread le performance aumentano in modo significativo (speedup di **3.7x** con 8 thread rispetto al sequenziale puro, raggiungendo le 67k verifiche/sec), dimostrando la solidità dell'approccio.

---

## Worker gRPC per Pipeline Multi-Nodo (M6)

La fase M6 introduce il **worker gRPC** (implementato in `src/pipeline/`). A differenza dei benchmark isolati (M5/M7), questo componente è un vero demone di produzione progettato per ascoltare task di calcolo (es. il task predefinito `INCREMENT_COUNTER` o rispondere con errore `UNIMPLEMENTED` a task sconosciuti).
Questo server gRPC costituisce il target fisico di esecuzione della pipeline, coordinato centralmente dal satellite.

### Compilazione ed Esecuzione (Isolamento)

Il componente utilizza l'infrastruttura CMake principale ma definisce un proprio target di build dedicato, `pipeline_worker`.
Può essere eseguito localmente o tramite il container (es. con il tag `deploy-worker-1`). L'entrypoint (`main_worker.cpp`) dipende dalle seguenti variabili d'ambiente:
- `PORT`: Porta di ascolto gRPC (default: `50051`)
- `NODE_ID`: L'identificativo esatto del device associato a questo worker, utile in log e debug (default: `worker-default`)

### Esecuzione dei Test

I test dedicati al worker verificano in locale i metodi base (`Ping` ed `ExecuteTask`) avviando un server in background. Si richiamano tramite CTest eseguendo la specifica test suite registrata nel `CMakeLists.txt`:
```bash
docker run --rm -v $(pwd):/app -w /app hpc-engine-build bash -c "cd build && ctest -V -R WorkerCorrectness"
```

### Contesto End-to-End

Da solo il worker gRPC rimane passivo e non fa nulla. Per testare il vero flusso distribuito del progetto (lease dei nodi, distribuzione dei task paralleli e successivo release) fai riferimento al demone in Python:
👉 **[satellite/README.md](../satellite/README.md)**

---

## Esperimento OpenMPI e Ibrido MPI+OpenMP (M7 / M11.1)

L'esperimento esegue un confronto isolato distribuendo il medesimo carico (500 verifiche complessive, in linea con l'esperimento originale M5) su processi OpenMPI combinati con il multithreading OpenMP. L'obiettivo è quantificare l'eventuale overhead o vantaggio derivante dal modello a memoria distribuita rispetto all'approccio multithread puro e valutare il comportamento del modello ibrido **MPI + OpenMP** (richiesto dai requisiti HPC per task e data parallelism combinati).

Per eseguire l'esperimento ibrido:
```bash
docker build -t hpc-engine-build -f hpc-engine/Dockerfile .
docker run --rm -v $(pwd)/hpc-engine:/app/hpc-engine -w /app/hpc-engine --entrypoint bash hpc-engine-build -c '
for np in 1 2 4 8; do
  for th in 1 2 4; do
    mpirun --allow-run-as-root -np $np /app/build/hpc_engine_mpi 500 $th results_hybrid_mpi_omp.csv
  done
done
'
```

### Risultati e Confronto

Tabella comparativa (throughput in verifiche/sec su batch totale di 500 firme):

| Livello di Concorrenza | OpenMP Puro (M5) | OpenMPI Puro (M7) | Ibrido MPI+OpenMP (M11.1) | Configurazione Ibrida (Ranks × Threads) |
|------------------------|------------------|-------------------|---------------------------|------------------------------------------|
| 1 core effettivo       | ~17,700          | ~16,500           | ~5,282                    | 1 rank × 1 thread                        |
| 2 core effettivi       | ~23,200          | ~30,300           | ~6,063                    | 1 rank × 2 threads                       |
|                        |                  |                   | ~10,110                   | 2 ranks × 1 thread                       |
| 4 core effettivi       | ~35,400          | ~48,900           | ~6,340                    | 1 rank × 4 threads                       |
|                        |                  |                   | ~12,410                   | 2 ranks × 2 threads                      |
|                        |                  |                   | ~16,726                   | 4 ranks × 1 thread                       |
| 8 core effettivi       | ~67,400          | ~59,800           | ~12,396                   | 2 ranks × 4 threads                      |
|                        |                  |                   | ~23,915                   | 4 ranks × 2 threads                      |
|                        |                  |                   | ~25,261                   | 8 ranks × 1 thread                       |
| 16 core effettivi      | N/A              | N/A               | ~38,624                   | 4 ranks × 4 threads                      |
|                        | N/A              | N/A               | ~40,239                   | 8 ranks × 2 threads                      |

*I dati completi dell'ibrido sono tracciati nel file `hpc-engine/results_hybrid_mpi_omp.csv`.*

### Interpretazione dei Risultati

1. **Riduzione dei tempi locali per rank tramite OpenMP**: All'interno di ogni configurazione a rank fissi, incrementare il numero di thread OpenMP riduce il tempo di esecuzione locale per rank e aumenta il throughput globale. Ad esempio, a 4 rank MPI, passando da 1 a 2 e poi a 4 thread OpenMP il throughput cresce progressivamente da **16,726** a **23,915** fino a **38,624 sig/s**.
2. **Overhead combinato su carichi a grana fine (Double Overhead)**: Su un dataset di dimensioni contenute (500 firme totali), suddividere il carico prima tra processi MPI e poi tra thread OpenMP produce porzioni di lavoro molto piccole per thread (es. a 4 rank con 4 thread, ciascun thread verifica solo ~31 firme). In questo regime:
   - L'overhead di gestione combinata (avvio e sincronizzazione MPI_Barrier / MPI_Reduce + fork/join OpenMP) incide in misura non trascurabile sul tempo totale.
   - A bassi rank, la combinazione 1 rank × 1 thread parte da un throughput inferiore rispetto al sequenziale isolato puro (~5.2k vs ~17.7k), riflettendo l'onere del setup MPI e della gestione del runtime OpenMP.
   - Nella configurazione a 2 rank × 4 thread (8 core totali), il throughput (~12,396 sig/s) rimane piatto rispetto a 2 rank × 2 thread (~12,410 sig/s): la contesa sull'allocazione dei contesti OpenSSL (`EVP_MD_CTX_new`) unita all'overhead di scheduling per sole ~62 verifiche a thread annulla il beneficio dell'ulteriore parallelizzazione.
3. **Scalabilità a configurazioni estese (16 core)**: Quando il parallelismo ibrido scala a 4 rank × 4 thread (38.6k sig/s) e 8 rank × 2 thread (40.2k sig/s), il sistema dimostra la reale combinazione di parallelismo a memoria distribuita (MPI) e data parallelism a memoria condivisa (OpenMP), fornendo la base architetturale per le metriche HPC di M11.

### Decisione Architetturale Confermata

Nonostante l'esperimento dimostri con successo il modello ibrido formale MPI+OpenMP, **l'architettura di produzione per il calcolo distribuito nel progetto rimane basata su Satellite + worker gRPC (M6/M9/M11)**.

**Motivazione**: MPI richiede una topologia di processi statica e prefissata al lancio (`mpirun`), che è strutturalmente incompatibile con il leasing dinamico on-chain dei nodi e l'onboarding elastico tipico degli ambienti IoT/Edge. L'estensione di calcolo distribuito ad alte prestazioni a regime viene pertanto realizzata tramite dispatch concorrente via gRPC verso worker C++ ottimizzati con OpenMP.
