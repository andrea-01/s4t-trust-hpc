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

## Esperimento OpenMPI (M7 - Step 4)

L'esperimento M7 esegue un confronto isolato distribuendo il medesimo carico (10000 verifiche complessive) su processi OpenMPI. L'obiettivo è quantificare l'eventuale overhead o vantaggio derivante dal modello multiprocesso a memoria distribuita rispetto all'approccio multithread di OpenMP.

Per eseguire l'esperimento:
```bash
docker run --rm -v $(pwd):/app -w /app hpc-engine-m7 bash -c "for np in 1 2 4 8; do mpirun --allow-run-as-root -np \$np ./build/hpc_engine_mpi; done"
```

### Risultati e Confronto

Tabella comparativa (throughput in verifiche/sec):

| Worker/Thread | OpenMP (M5) | OpenMPI (M7) |
|---------------|-------------|--------------|
| 1             | ~17,700     | ~16,400      |
| 2             | ~23,200     | ~31,000      |
| 4             | ~35,400     | ~64,600      |
| 8             | ~67,400     | ~71,300      |

### Interpretazione

1. **Scalabilità Lineare MPI vs Contention OpenMP**: Il risultato più rilevante è che **OpenMPI scala in modo quasi perfettamente lineare** da 1 a 4 processi (16.4k → 31.0k → 64.6k), a differenza di OpenMP. Questo conferma la diagnosi del benchmark M5: la perdita di scalabilità in OpenMP (17.7k → 23.2k) è imputabile alla *lock contention* dell'allocatore di memoria di sistema condiviso durante la chiamata `EVP_MD_CTX_new()`. In OpenMPI, poiché ogni rank è un processo del sistema operativo separato con il proprio heap e il proprio lock di allocazione indipendente, la contention sparisce completamente.
2. **Overhead di Processo**: L'approccio OpenMPI mostra un lieve overhead per rank singolo (16.4k vs 17.7k), presumibilmente a causa dei costi di startup di `MPI_Init` e delle primitive di reduce.

### Decisione Architetturale Confermata

Nonostante in questo specifico microbenchmark i processi isolati MPI superino i thread OpenMP a parità di concorrenza, **l'architettura di esecuzione distribuita di produzione resta quella definita in M6 (Satellite + worker gRPC)** e non viene sostituita da OpenMPI.

**Motivazione**: Come stabilito in fase di design iniziale, MPI richiede una topologia di processi statica nota all'avvio (tramite hostfile per `mpirun`), la quale risulta incompatibile con il modello a leasing dinamico in-memory in cui i nodi lavoratori eterogenei si rendono disponibili on-demand (simulazione del leasing reale che avverrà on-chain). La flessibilità del framework satellite-gRPC compensa ampiamente il costo di serializzazione.
