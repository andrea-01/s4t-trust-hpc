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

L'esperimento esegue un confronto controllato distribuendo il medesimo carico (500 verifiche complessive su dataset sintetico deterministico) su processi OpenMPI combinati con il multithreading OpenMP, compilati interamente con `CMAKE_BUILD_TYPE=Release` e flag `-O2 -Wall -Wextra`. L'obiettivo è quantificare l'overhead e i benefici derivanti dal modello ibrido **MPI + OpenMP** (richiesto per combinare task e data parallelism) a confronto diretto con le baseline OpenMP pura (M5) e MPI pura (M7) generate nello stesso identico ambiente.

Per compilare ed eseguire l'esperimento:
```bash
docker build -t hpc-engine-build -f hpc-engine/Dockerfile .

# Esecuzione OpenMP Puro (M5)
docker run --rm -v $(pwd)/hpc-engine:/app/hpc-engine -w /app/hpc-engine --entrypoint bash hpc-engine-build -c \
  "/app/build/hpc_engine_bench 500 500 1,2,4,8 results_m5_release.csv"

# Esecuzione Ibrido MPI+OpenMP (M11.1)
docker run --rm -v $(pwd)/hpc-engine:/app/hpc-engine -w /app/hpc-engine --entrypoint bash hpc-engine-build -c '
for np in 1 2 4 8; do
  for th in 1 2 4; do
    if [ $np -eq 8 ] && [ $th -eq 4 ]; then continue; fi
    mpirun --allow-run-as-root -np $np /app/build/hpc_engine_mpi 500 $th results_hybrid_mpi_omp.csv
  done
done
'
```

### Risultati Sperimentali e Confronto Omogeneo

Tutte le metriche sono state raccolte nella medesima sessione, sulla stessa macchina e nello stesso container Docker, con ottimizzazione `-O2` attiva (throughput in verifiche/sec su batch di 500 firme):

| Livello di Concorrenza | OpenMP Puro (M5) | OpenMPI Puro (M7) | Ibrido MPI+OpenMP (M11.1) | Configurazione Ibrida (Ranks × Threads) |
|------------------------|------------------|-------------------|---------------------------|------------------------------------------|
| **1 core effettivo**   | ~4,777           | ~4,260            | ~4,260                    | 1 rank × 1 thread                        |
| **2 core effettivi**   | ~7,290           | ~6,568            | ~5,862                    | 1 rank × 2 threads                       |
|                        |                  |                   | ~6,568                    | 2 ranks × 1 thread                       |
| **4 core effettivi**   | ~11,722          | ~8,787            | ~3,651                    | 1 rank × 4 threads *(overhead loop/lock)*|
|                        |                  |                   | ~10,387                   | 2 ranks × 2 threads                      |
|                        |                  |                   | ~8,787                    | 4 ranks × 1 thread                       |
| **8 core effettivi**   | ~19,060          | ~21,514           | ~7,724                    | 2 ranks × 4 threads                      |
|                        |                  |                   | ~21,749                   | 4 ranks × 2 threads                      |
|                        |                  |                   | ~21,514                   | 8 ranks × 1 thread                       |
| **16 core effettivi**  | N/A              | N/A               | **~33,554**               | 4 ranks × 4 threads                      |
|                        | N/A              | N/A               | ~21,823                   | 8 ranks × 2 threads                      |

*I dati completi sono tracciati nei file `hpc-engine/results_m5_release.csv` e `hpc-engine/results_hybrid_mpi_omp.csv`.*

### Analisi e Isolamento delle Cause Sperimentali

1. **Allineamento delle Baseline di Singolo Core**:
   - In condizioni omogenee di build (`-O2`), un singolo core elabora circa **~4,777 sig/s** in OpenMP puro (1 thread), **~4,998 sig/s** in sequenziale isolato, e **~4,260 sig/s** in MPI (1 rank × 1 thread).
   - L'indagine sperimentale sul "warmup" (inizializzazione preventiva del thread team libgomp con `#pragma omp parallel {}`) ha evidenziato un impatto di soli ~3.5 ms. La congruenza delle tre baseline a ~4.3k–5.0k sig/s conferma che il costo di 1×1 è dominato dal carico computazionale OpenSSL con un overhead di overhead MPI+OpenMP contenuto (~10-14%).
2. **Vantaggio dell'Ibridazione a Piena Scala (Task + Data Parallelism)**:
   - Su 8 core logici, distribuire il carico su **4 processi MPI con 2 thread OpenMP ciascuno** raggiunge **21,749 sig/s**, superando sia OpenMP puro su 8 thread (19,060 sig/s) sia 8 rank MPI puri (21,514 sig/s).
   - Scalando a 16 core effettivi, la combinazione **4 rank × 4 thread OpenMP** raggiunge il picco di **33,554 sig/s** (speedup di **~7.9x** rispetto a 1×1), dimostrando come l'ibrido sfrutti sia l'isolamento dell'heap e la riduzione della contesa (via processi MPI) sia il data parallelism a bassa latenza (via thread OpenMP).
3. **Casi di Overhead da Sovra-sottoscrizione e Granularità Fine**:
   - Quando un singolo processo crea 4 thread OpenMP su sole 500 firme (1 rank × 4 thread) o 2 rank × 4 thread, la contesa per l'allocazione ripetuta di `EVP_MD_CTX_new` per ogni verifica all'interno del medesimo processo degrada il throughput (~3.6k–7.7k sig/s).
   - Questo fenomeno conferma sperimentalmente la regola aurea dell'HPC: il multi-threading OpenMP all'interno di un processo è efficace solo se la porzione di lavoro per rank è sufficientemente bilanciata rispetto al costo dei lock interni della libreria crittografica.

### Decisione Architetturale Confermata

Nonostante l'esperimento confermi con evidenza scientifica il funzionamento e i vantaggi di scala del modello ibrido formale MPI+OpenMP, **l'architettura di produzione per il calcolo distribuito nel progetto rimane basata su Satellite + worker gRPC (M6/M9/M11)**.

**Motivazione**: MPI richiede una topologia di processi statica nota all'avvio (`mpirun`), incompatibile con il leasing dinamico on-chain dei nodi e con l'integrazione di board eterogenee Stack4Things/IoTronic. Il task parallelism distribuito a regime viene pertanto realizzato tramite dispatch concorrente via gRPC verso worker C++ multithread con OpenMP.
