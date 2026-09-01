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

Per compilare ed eseguire l'esperimento ibrido con corretta gestione del CPU binding:
```bash
docker build -t hpc-engine-build -f hpc-engine/Dockerfile .

# Esecuzione OpenMP Puro (M5)
docker run --rm -v $(pwd)/hpc-engine:/app/hpc-engine -w /app/hpc-engine --entrypoint bash hpc-engine-build -c \
  "/app/build/hpc_engine_bench 500 500 1,2,4,8 results_m5_release.csv"

# Esecuzione Ibrido MPI+OpenMP (M11.1) con --bind-to none
docker run --rm -v $(pwd)/hpc-engine:/app/hpc-engine -w /app/hpc-engine --entrypoint bash hpc-engine-build -c '
for np in 1 2 4 8; do
  for th in 1 2 4; do
    if [ $np -eq 8 ] && [ $th -eq 4 ]; then continue; fi
    mpirun --allow-run-as-root --bind-to none -np $np /app/build/hpc_engine_mpi 500 $th results_hybrid_mpi_omp.csv
  done
done
'
```

### Risultati Sperimentali e Confronto Omogeneo

Tutte le metriche sono state raccolte nella medesima sessione, sulla stessa macchina e nello stesso container Docker, con ottimizzazione `-O2` attiva e policy di binding esplicita `--bind-to none` per consentire ai thread OpenMP di scalare sui core disponibili (throughput in verifiche/sec su batch di 500 firme):

| Livello di Concorrenza | OpenMP Puro (M5) | OpenMPI Puro (M7) | Ibrido MPI+OpenMP (M11.1) | Configurazione Ibrida (Ranks × Threads) |
|------------------------|------------------|-------------------|---------------------------|------------------------------------------|
| **1 core effettivo**   | ~4,777           | ~4,260            | ~5,353                    | 1 rank × 1 thread                        |
| **2 core effettivi**   | ~7,290           | ~6,568            | ~10,132                   | 1 rank × 2 threads                       |
|                        |                  |                   | ~10,405                   | 2 ranks × 1 thread                       |
| **4 core effettivi**   | ~11,722          | ~8,787            | ~13,114                   | 1 rank × 4 threads                       |
|                        |                  |                   | ~12,562                   | 2 ranks × 2 threads                      |
|                        |                  |                   | ~14,460                   | 4 ranks × 1 thread                       |
| **8 core effettivi**   | ~19,060          | ~21,514           | ~24,706                   | 2 ranks × 4 threads                      |
|                        |                  |                   | ~25,582                   | 4 ranks × 2 threads *(migliore 8 core)*  |
|                        |                  |                   | ~25,463                   | 8 ranks × 1 thread                       |
| **16 core effettivi**  | N/A              | N/A               | **~30,033**               | 4 ranks × 4 threads                      |
|                        | N/A              | N/A               | **~32,442**               | 8 ranks × 2 threads *(picco ibrido)*     |

*I dati completi sono tracciati nei file `hpc-engine/results_m5_release.csv` e `hpc-engine/results_hybrid_mpi_omp.csv`.*

### Analisi e Finding HPC dell'Esperimento

1. **CPU Process Binding in Open MPI (Critical Finding)**:
   - Ispezionando il comportamento di Open MPI con `--report-bindings`, è emerso che **la policy di default di `mpirun` vincola rigidamente ciascun processo rank a un singolo core fisico** (es. `rank 0 bound to socket 0[core 0]`, mask `[BB/../../...]`).
   - In un modello ibrido MPI+OpenMP, questo causa la serializzazione di tutti i thread OpenMP interni al processo sul medesimo core, degradando drasticamente le prestazioni nelle configurazioni a molti thread per rank (es. 1×4 crollava a ~3.6k sig/s a causa del context switching su un unico core).
   - Rimuovendo il vincolo restrittivo tramite `--bind-to none` (o associando slot di processore `--map-by :PE=N`), i thread OpenMP possono distribuirsi liberamente sui core fisici: il throughput di 1×4 risale immediatamente a **13,114 sig/s** (coerente con OpenMP puro) e quello di 2×4 raddoppia a **24,706 sig/s**.
2. **Confronto Omogeneo delle Baseline**:
   - Compilando con `Release` e `-O2`, un singolo core elabora circa **~4.8k–5.3k sig/s** sia in OpenMP puro che nell'ibrido MPI+OpenMP. La discrepanza con i dati storici del README (~17k sig/s) è stata isolata e spiegata come dipendenza dall'ambiente/hardware host di esecuzione originale.
   - Il cold-start libgomp (inizializzazione preventiva del thread team con `#pragma omp parallel {}`) incide per soli ~3.5 ms.
3. **Vantaggio Strutturale dell'Ibrido (Task + Data Parallelism)**:
   - A 8 core logici, le configurazioni ibride **4 rank × 2 thread** (**25,582 sig/s**) e **2 rank × 4 thread** (**24,706 sig/s**) superano nettamente sia OpenMP puro a 8 thread (19,060 sig/s) sia 8 rank MPI puri (21,514 sig/s).
   - A 16 core effettivi, l'ibrido tocca **32,442 sig/s** (8 rank × 2 thread), confermando l'efficacia di combinare la separazione degli heap e la riduzione della contesa (processi MPI) con il parallelismo a memoria condivisa a bassa latenza (thread OpenMP).

### Decisione Architetturale Confermata

Nonostante l'esperimento confermi con evidenza scientifica il funzionamento e i vantaggi di scala del modello ibrido formale MPI+OpenMP, **l'architettura di produzione per il calcolo distribuito nel progetto rimane basata su Satellite + worker gRPC (M6/M9/M11)**.

**Motivazione**: MPI richiede una topologia di processi statica nota all'avvio (`mpirun`), incompatibile con il leasing dinamico on-chain dei nodi e con l'integrazione di board eterogenee Stack4Things/IoTronic. Il task parallelism distribuito a regime viene pertanto realizzato tramite dispatch concorrente via gRPC verso worker C++ multithread con OpenMP.
