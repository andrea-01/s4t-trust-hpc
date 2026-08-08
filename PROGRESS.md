# PROGRESS

## Sessione Attuale
**Data:** 2026-08-05

### Task Completati
- [x] M0: Scaffolding repo e placeholder creati.
- [x] M1: Smart contract `OnboardingTrust.sol`, test Hardhat, script di simulazione client in Node.js e setup testnet in Docker Compose completati.

### Note e Troubleshooting (Fase M1)
- **Compatibilità Node.js / `ts-node`**: L'ultima versione di Node.js presente (v24.19) ha mostrato incompatibilità con l'integrazione nativa TypeScript di Hardhat (errore interno di `ts-node` legato alla lettura dei file di configurazione). Il problema è stato isolato e risolto effettuando il downgrade di `typescript` (4.9.5) e vincolando il progetto all'ambiente Node.js 22 (inserito limite `engines` in `package.json` e creato file `.nvmrc`).
- **Valutazione `npm audit`**: Eseguito `npm audit` in `chain/` che riporta 46 vulnerabilità (17 high), legate prevalentemente alle versioni di `hardhat` (2.22.x) e le sue dipendenze storiche (`undici`, `serialize-javascript`, ecc.). Poiché le librerie infette sono limitate all'ambiente di `devDependencies` locale usato solo per lo sviluppo e il deploy dello smart contract (nessun web server di produzione esposto) e tentare un `npm audit fix --force` introdurrebbe breaking changes passando a Hardhat 3.x (che riaprirebbe i problemi ESM/TypeScript), ho giudicato l'audit report **non bloccante** per questa fase.

## Fase: M2 (Gateway Python)

### Task Completati
- [x] 0. Eccezione su M1: Modificato `chain/` per avere uno script di deploy unico `deploy.ts` che salva l'indirizzo su volume condiviso, introdotto servizio `contract-deployer` in docker-compose.yml per fornire l'indirizzo ai client M1 e (successivamente) al gateway. (Commit: fix(chain): add dedicated deploy script and shared address file).
- [x] 1. Scaffold gateway project and dependencies (Commit: feat: scaffold gateway project and dependencies).
- [x] 2. Add chain_client for smart contract interaction (Commit: feat: add chain_client for smart contract interaction).
- [x] 3. Add event_poller for background event caching (Commit: feat: add event_poller for background event caching).
- [x] 4. Implement FastAPI endpoints (Commit: feat: implement FastAPI endpoints).
- [x] 5. Add integration tests for gateway against local hardhat node (Commit: test: add integration tests for gateway against local hardhat node).
- [x] 6. Create gateway Dockerfile (Commit: feat: create gateway Dockerfile).
- [x] 7. Integrate gateway into docker-compose (Commit: feat: integrate gateway into docker-compose).
- [x] 8. Update README with gateway instructions (Commit: docs: update README with gateway instructions).
- [x] Fix correttivi M2: Rimosso requester_key in favore di ADMIN_PRIVATE_KEY da env, aggiunta validazione owner_address, gestite eccezioni web3.py. (Commit: fix(gateway): remove private key from API surface, add input validation).

## Fase: M3 (Notifiche Email)

### Task Completati
- [x] 1. Scaffold modulo `notification/` e `owners.json` (Punti 1 e 2)
- [x] 2. Implementazione di `owners_registry.py` e `mailer.py` con test (Punti 3 e 5)
- [x] 3. Gestione Checkpoint Idempotenza (Punto 4)
- [x] 4. Implementazione di `chain_listener.py` e `main.py` (Punti 3 e 6)
- [x] 5. Integrazione Docker Compose e Mailpit con test integrazione (Punti 8, 9, 10, 7)

### Note (Fase M3)
- Abbiamo mantenuto la condivisione tramite volume degli artifact on-chain. Il checkpoint è persistito in un file su `state/`. Mailpit è stato configurato per essere avviato e gestito tramite compose.
- **Chain Reset Detection**: È stata aggiunta un'estensione non originariamente pianificata ma essenziale per la robustezza locale. Se il nodo locale Hardhat viene distrutto e ricreato (ad esempio tramite un restart distruttivo di docker-compose), la chain riparte dal blocco 0. Il listener Python ora se ne accorge confrontando il blocco corrente col suo checkpoint e si resetta a 0 per non bloccarsi aspettando blocchi futuri inesistenti, garantendo resilienza durante lo sviluppo.

### Domande Aperte
- Nessuna.

## Fase: M4 (Interfaccia FastAPI)

### Task Completati
- [x] 1. Scaffold `ui/` module structure and dependencies (Punti 1 e 7)
- [x] 2. Implementazione di `gateway_client.py` con gestione errori (Punto 2)
- [x] 3. Implementazione main FastAPI app con route JSON aggiuntiva (`/api/requests`) (Punto 3)
- [x] 4. Creazione template Jinja2 per dashboard (Punto 4)
- [x] 5. Implementazione polling via JavaScript per auto-aggiornamento (Punto 5)
- [x] 6. Aggiunta integration test per la UI (Punto 6)
- [x] 7. Integrazione Docker Compose per esporre la porta 8080 (Punto 8)
- [x] 8. Aggiornamento documentazione (Punto 9)

### Note (Fase M4)
- È stato aggiunto un endpoint JSON `/api/requests` dedicato esclusivamente al polling JavaScript. Tutte le interazioni con il gateway sono incapsulate in blocchi `try/except` per gestire timeout e cadute del servizio, restituendo errori 503 HTTP o messaggi espliciti nell'HTML, impedendo crash non gestiti o ritorni `500` oscuri.
- Come verificato tramite l'esplorazione del codice, il gateway non espone alcun endpoint di `/health`, quindi la dipendenza del servizio `ui` in Docker Compose utilizza la notazione standard `depends_on: gateway` senza aspettare specifici test di integrità.
- **Eccezione documentata (owners.json):** Durante il test end-to-end della Fase M4, le richieste inserite dalla UI non producevano email. Modifica fuori scope (modulo `notification/`) effettuata: aggiunto l'elenco degli account di test predefiniti di Hardhat a `owners.json`. L'eccezione è giustificata dal fatto che per validare completamente l'integrazione M4, le chiamate asincrone della blockchain generate dalla UI dovevano propagarsi al poller di notifica, che falliva silenziosamente il match dell'email per indirizzi di test non mappati.

## Fase: M5 (HPC C++ Benchmark)

### Task Completati
- [x] 1. Scaffold `hpc-engine/` e creazione di `Dockerfile` per la compilazione in un ambiente C++17 pulito.
- [x] 2. Implementazione di `device_generator` deterministico utilizzando l'API moderna OpenSSL 3.x `EVP_PKEY_Q_keygen` per ECDSA P-256 e gestione memoria sicura tramite custom deleters su `std::unique_ptr`.
- [x] 3. Implementazione di `signature_bench` con logica di validazione sequenziale.
- [x] 4. Estensione di `signature_bench` con `#pragma omp parallel for` di OpenMP per validazione parallela.
- [x] 5. Implementazione esportazione risultati in CSV.
- [x] 6. Integrazione della CLI nel `main` per la parametrizzazione di size del dataset, ranges di batch_size e ranges di threads.
- [x] 7. Scrittura di unit test con custom runner (basato su `cassert`) per testare correttezza firma (validazione, manomissione messaggio, manomissione firma).
- [x] 8. Esecuzione benchmark e creazione `hpc-engine/README.md` con risultati e report.

### Note (Fase M5)
- Le prestazioni su benchmark di 500 records sintetici mostrano uno speedup effettivo di ~3.7x utilizzando 8 threads (67k vs 18k validazioni al secondo), confermando l'efficacia dell'approccio OpenMP.
- L'allocazione dei contesti OpenSSL (`EVP_MD_CTX_new()`) è eseguita ad ogni interazione nel loop. Si ipotizza che l'anomalia di scaling (da 1 a 2 thread con speedup solo 1.3x) sia imputabile a questo, sebbene manchi ancora una verifica sperimentale della performance dopo un eventuale context reuse. La potenziale soluzione è stata documentata esplicitamente nel README come ottimizzazione futura. Il numero di core fisici sulla macchina è stato verificato in 20.
- Gestione della memoria verificata per l'oggetto `EVP_PKEY`, e i contesti `EVP_MD_CTX`, `EVP_PKEY_CTX` tramite `std::unique_ptr` con relativi deleters. Un residuo di debug/refactoring su `EVP_MD_CTX_Deleter` è stato correttamente individuato e storicizzato con un commit dedicato, garantendo uno staging pulito.
- Codice compilato con successo mantenendo `-Wall -Wextra` senza warning a compile-time (incluso il controllo esplicito sui parametri della logica).
- La validazione tramite Test Runner nativo basato su `cassert` garantisce sicurezza contro manomissioni su messaggi e firme su API OpenSSL 3.x moderne senza aggiungere librerie esterne di dependency.

## Fase: M6 (Pipeline Multi-Nodo HPC)

### Task Completati
- [x] 1. Creazione contratto gRPC `proto/pipeline.proto` con operazioni base (Ping, ExecuteTask e enum INCREMENT_COUNTER).
- [x] 2. Implementazione Worker gRPC C++ (`hpc-engine/src/pipeline/`) e aggiornamento `CMakeLists.txt` (stub autogenerati).
- [x] 3. Aggiornamento `hpc-engine/Dockerfile` e aggiunta logica di build gRPC (installati `protobuf-compiler-grpc`, `libgrpc++-dev` su immagine base Ubuntu 24.04).
- [x] 4. Scaffold modulo `satellite/` (FastAPI + stub generation python via `grpcio-tools` built into the Dockerfile).
- [x] 5. Implementazione leasing in-memory in `satellite/app/node_registry.py` protetto esplicitamente da `asyncio.Lock`.
- [x] 6. Implementazione `satellite/app/pipeline_client.py` e `main.py` per l'orchestrazione gRPC in serie sui nodi leased.
- [x] 7. Sviluppo test Python (`pytest` e `httpx`) per verificare la concorrenza sul leasing (il doppio leasing fallisce come previsto).
- [x] 8. Creazione stack isolato in `deploy/docker-compose.pipeline.yml`.
- [x] 9. Aggiornamento `README.md` principale e `PROGRESS.md` documentando i due flussi di build per il worker (sviluppo locale montato in volume vs execution compose context).

### Note (Fase M6)
- È stata applicata rigorosamente la direttiva di non eseguire codice arbitrario: il client gRPC inietta soltanto la scelta del task definita staticamente dall'enum `OPERATION_UNKNOWN` = 0, `INCREMENT_COUNTER` = 1.
- Abbiamo implementato un setup di generazione di stub dry (don't repeat yourself): i `.proto` vivono nella root `/proto` e sia il satellite (Dockerfile copy) sia l'hpc-engine (add_custom_command in CMake) li generano "al volo" durante la build e non vengono versionati nel repository.
- Aggiunto `pytest-asyncio` nei requirements del modulo satellite a fronte del primo warning per `PytestUnhandledCoroutineWarning`. I test concorrenziali (con 5 richieste `asyncio.gather` in parallelo) confermano empiricamente il corretto rigetto con status code 400 e la solidità del lock `asyncio.Lock` nell'assegnazione, impedendo che i nodi leased superino il pool totale a disposizione.
- Aggiunto un test diretto in C++ (ctest `WorkerCorrectness`) per verificare esplicitamente che le chiamate del client gRPC a `ExecuteTask` gestiscano l'incremento di valore o falliscano in caso di `OPERATION_UNKNOWN` ritornando lo status `UNIMPLEMENTED`.
- La porta esposta per il Satellite è stata settata a `8001` per non interferire con il Gateway (`8000`) attivo nel compose principale.

### Domande Aperte
- Nessuna per la fase M6. M6 completato e verificato a tutto tondo.

## Fase: M7 (Esperimento OpenMPI)

### Task Completati
- [x] 1. Aggiunti `openmpi-bin` e `libopenmpi-dev` al Dockerfile di `hpc-engine`.
- [x] 2. Creato scaffold dell'esperimento `hpc-engine/src/mpi_experiment/main_mpi.cpp` e aggiornato `CMakeLists.txt` per includere `MPI` e linkare i moduli di `M5` senza modificarli.
- [x] 3. Implementata la logica del benchmark MPI: `MPI_Init`, seed basato sul rank, reduce sul `total_verified` e `max_time`.
- [x] 4. Implementato sanity check (validazione corretta per firma valida e fallimento atteso per firma alterata).
- [x] 5. Esecuzione test `-np 1, 2, 4, 8` e salvataggio in `results_mpi.csv`.
- [x] 6. Aggiornamento `hpc-engine/README.md`.

## Fase: M8 (Integrazione Leasing Blockchain)

### Task Completati
Questa fase ha unito le due anime del progetto (l'infrastruttura HPC e il trust decentralizzato su chain), gestendo il ciclo di vita dei worker in base al loro stato effettivo sulla Blockchain. Il lavoro è stato organizzato e unito in **6 commit testati**:

1. **`feat(chain): M8 add LeasingRegistry and device status query`**: Aggiunta della query di stato su `OnboardingTrust.sol` e creazione dello smart contract isolato `LeasingRegistry.sol`.
2. **`feat(chain): M8 automatic onboarding of worker nodes`**: Creazione dello script TypeScript effimero `auto-onboard-workers.ts` e aggiornamento di `deploy.ts` per istanziare e registrare la trustnet automaticamente all'avvio dell'infrastruttura.
3. **`feat(gateway): M8 gateway endpoints for blockchain leasing`**: Integrazione di `leasing_client.py` e nuovi endpoint nel Gateway (tramite `web3.py` e Pydantic) per mediare con lo smart contract.
4. **`refactor(satellite): M8 migrate from in-memory to real gateway leasing`**: Rimossa la gestione in memoria dal Satellite. Ora i task orchestrati delegano il tracciamento dei lock all'effettivo leasing on-chain tramite API HTTP verso il Gateway.
5. **`chore(deploy): M8 shared network and auto-onboard service`**: Creazione della rete bridge condivisa (`s4t-bridge`) tra i due Compose stack isolati e configurazione del servizio `auto-onboard`.
6. **`docs: M8 update README, .gitignore and E2E test script`**: Completamento della documentazione architetturale nel README, pulizia dei path hardhat generati dal tracciamento git e spostamento strategico dello script end-to-end (`run_e2e.sh`).

### Decisioni Architetturali Note (Gas Cost `getDeviceStatus`)
Nel contratto `OnboardingTrust.sol`, l'iterazione a ritroso implementata per risolvere l'ultima tupla in `getDeviceStatus` ha un costo in gas crescente col variare del numero totale delle transazioni storiche. Questa è stata una **decisione nota e documentata intenzionalmente tramite NatSpec** come parte del compromesso progettuale, giustificabile per interrogazioni prevalentemente off-chain, o limitate alla finestra contenuta della Proof of Concept.

Per convalidare la tenuta del limite del gas, è stato introdotto **un test specifico in Hardhat** (`OnboardingTrust.test.ts`) che popola deliberatamente lo storico con 30 "filler devices" iniziali, seguiti dal "worker-1", seguiti a loro volta da ulteriori filler. In questo scenario reale (scorrere ~35 record prima di estrarre lo stato corretto), lo script stima un esborso di **circa 42.445 gas**. Questo log fornisce una baseline affidabile da monitorare per scenari futuri in cui lo storico crescerà significativamente.

### Bug Risolti & Strutturali
Il problema più rilevante in questa fase è stato il riscontro di una **Race Condition** fatale durante la partenza dell'infrastruttura e del primo testing E2E.
Il `gateway` e lo script di verifica E2E provavano a leggere e manipolare lo stato dei device prima che il container `auto-onboard` avesse finito di richiedere/approvare effettivamente l'onboarding di tali nodi sulla chain.
Questo portava il Gateway a rifiutare costantemente le risorse restituendo l'eccezione interna `Device not found`.

**Risoluzione**: La fix è stata applicata **strutturalmente** nel file `docker-compose.yml`, introducendo per il servizio gateway l'obbligo formale di aspettare la corretta conclusione del task:
```yaml
    depends_on:
      auto-onboard:
        condition: service_completed_successfully
```
Tramite questa correzione, l'architettura attende intrinsecamente che la sincronizzazione fittizia dei worker sulla blockchain sia stata interamente scritta, sigillando la race condition all'avvio.
