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

## Esperimento OpenMPI (M7 - Step 4)

L'esperimento M7 esegue un confronto isolato distribuendo il medesimo carico (500 verifiche complessive, in linea con l'esperimento originale M5) su processi OpenMPI. L'obiettivo è quantificare l'eventuale overhead o vantaggio derivante dal modello multiprocesso a memoria distribuita rispetto all'approccio multithread di OpenMP.

Per eseguire l'esperimento:
```bash
docker run --rm -v $(pwd):/app -w /app hpc-engine-m7 bash -c "for np in 1 2 4 8; do mpirun --allow-run-as-root -np \$np ./build/hpc_engine_mpi 500; done"
```

### Risultati e Confronto

Tabella comparativa (throughput in verifiche/sec, batch 500):

| Worker/Thread | OpenMP (M5) | OpenMPI (M7) |
|---------------|-------------|--------------|
| 1             | ~17,700     | ~16,500      |
| 2             | ~23,200     | ~30,300      |
| 4             | ~35,400     | ~48,900      |
| 8             | ~67,400     | ~59,800      |

### Interpretazione

1. **Scalabilità a Bassi Core (MPI vs Contention OpenMP)**: Inizialmente, passando da 1 a 2 processi, **OpenMPI scala meglio** (16.5k → 30.3k). Questo è coerente con l'ipotesi di M5 sulla lock contention di EVP_MD_CTX, ma non la conferma in modo definitivo: nel passaggio da thread a processi cambiano più variabili insieme (heap separato, niente cache condivisa, overhead di comunicazione MPI), non solo il riuso del contesto OpenSSL. Una conferma diretta richiederebbe l'esperimento di context-reuse-per-thread già proposto come ottimizzazione futura in M5. In OpenMPI, poiché ogni rank è un processo separato con il proprio heap, la contention sparisce.
2. **Crossover e Overhead di Sincronizzazione MPI**: Scalando da 4 a 8 processi su un batch totale fisso (500), si assiste a un **crossover**: MPI si appiattisce visibilmente (+20%, da 48.9k a 59.8k), mentre OpenMP quasi raddoppia (+90%, da 35.4k a 67.4k). La spiegazione risiede nel rapporto tra carico utile e *overhead*. Con 8 processi su 500 task totali, ogni rank MPI esegue solo ~62 verifiche. Il lavoro utile per processo si riduce così tanto che il costo fisso di inizializzazione (`MPI_Init`), lo startup multiprocesso e la sincronizzazione (`MPI_Reduce`) di MPI — strutturalmente più pesanti dello startup di un thread OpenMP — diventa il fattore dominante (Amdahl's law effect). Al crescere vertiginoso del carico (es. batch da 10.000, tracciati in `results_mpi_10k.csv`), l'overhead MPI si diluisce nel lungo tempo di calcolo e le due soluzioni tornano a competere alla pari (71.3k per MPI a 8 processi contro i 67.4k di OpenMP).

### Decisione Architetturale Confermata

Nonostante in questo specifico microbenchmark i processi isolati MPI superino i thread OpenMP a parità di concorrenza, **l'architettura di esecuzione distribuita di produzione resta quella definita in M6 (Satellite + worker gRPC)** e non viene sostituita da OpenMPI.

**Motivazione**: Come stabilito in fase di design iniziale, MPI richiede una topologia di processi statica nota all'avvio (tramite hostfile per `mpirun`), la quale risulta incompatibile con il modello a leasing dinamico in-memory in cui i nodi lavoratori eterogenei si rendono disponibili on-demand (simulazione del leasing reale che avverrà on-chain). La flessibilità del framework satellite-gRPC compensa ampiamente il costo di serializzazione.
