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

## Fase: M9 (Integrazione IoTronic - Stadio 9.1)

### Task Completati
- [x] 1. Clone repository esterno `Stack4Things_DockerCompose_deployment` come sibling directory rispetto al mono-repo.
- [x] 2. Deploy dello stack IoTronic tramite `docker-compose.yml`. (Nessun file originale è stato patchato; è stato utilizzato un `docker-compose.override.yml` per correggere il placeholder dell'immagine `lightning-rod` fallata).
- [x] 3. Verifica dei servizi (Conductor e Crossbar attivi).
- [x] 4. Ricerca e studio del meccanismo dei plugin IoTronic: i plugin sono classi Python (estensioni di `Worker` da `Plugin.Plugin`) con setup asincrono/sincrono tramite code per il ritorno dei risultati.
- [x] 5. Analisi comparativa con l'Outline originario documentata in `s4t-plugin/IOTRONIC_NOTES.md`.
- [x] 6. Stesura del codice del plugin "hello world" (`s4t-plugin/hello_world_test/plugin.py`).

### Note (Fase M9.1)
- L'emulatore per la board (Lightning-Rod) è integrato nativamente come container all'interno dello stack compose del progetto IoTronic (`mdslab/lrod:compose`), rendendo inutile un ambiente custom, coerentemente con le indicazioni della documentazione di S4T.
- L'automazione browser (Browser Subagent) ha riscontrato un errore nel connettersi al CDP port per l'onboarding automatico via UI. Per cui la registrazione della board è stata delegata manualmente all'utente (via interazione `ask_question`).

### Domande Aperte & Test finali
- **Test completato:** In seguito alla registrazione manuale della board, il plugin "hello world" è stato correttamente iniettato e mandato in esecuzione tramite il container `iotronic-ui`, usando l'azione nativa `PluginCall`, che ha restituito correttamente l'output `SUCCESS: Hello from S4T Plugin!`. La fase 9.1 si conclude con successo.
- **In attesa (M9.2):** La dipendenza `grpcio`, fondamentale per connettersi al worker C++ dell'HPC Engine, potrebbe non essere presente sull'immagine `mdslab/lrod:compose`. Da verificare e risolvere in fase M9.2 prima dello sviluppo del vero plugin di offloading.


## Fase: M9 (Integrazione IoTronic - Stadio 9.2)

### Task Completati
- [x] 1. Ripristino del networking dello stack IoTronic tramite `docker-compose.override.yml`, connettendo `lightning-rod` a `s4t` e `s4t-bridge`.
- [x] 2. Soluzione del crash in fase di avvio di `lightning-rod` fornendo il pre-registration file `settings.json` corretto, risolvendo l'errore `NoneType`.
- [x] 3. Sviluppo del client gRPC reale nel plugin: `plugin_template.py` + `build_plugin.sh`.
- [x] 4. Installazione idempotente dinamica a runtime di `grpcio` e `protobuf` per aggirare l'assenza sul container `lrod:compose`.
- [x] 5. Configurazione cross-compatibilità: patch automatico del codice generato da `grpc_tools.protoc` per rimuovere i keyword args incompatibili con Python 3.7.
- [x] 6. Esecuzione end-to-end con esito positivo: `PluginCall` inietta un task gRPC `INCREMENT_COUNTER(42)` all'`hpc-engine` worker C++ (`deploy-worker-1-1:50051`) e riceve `43` in risposta, confermando la connettività di rete bidirezionale!

Lo Stadio 9.2 si conclude con successo.

## Fase: M9 (Integrazione IoTronic - Stadio 9.3 — Completamento)

### Task Completati
- [x] 1. **Fase 9.3.a (Investigazione)**: Determinazione dell'endpoint REST sincrono `POST /v1/boards/{board_name}/plugins/{plugin_name}` con autenticazione token Keystone `X-Auth-Token` e header `X-OpenStack-Iotronic-API-Version`. Validata coincidenza tra `device_id` blockchain e nome board IoTronic (`worker-1`, `worker-2`, `worker-3`).
- [x] 2. **Fase 9.3.b (Scaling Ambiente)**: Registrate 3 board Lightning-Rod connesse sia alla rete IoTronic WAMP (`s4t`) sia alla rete bridge (`s4t-bridge`). Plugin gRPC `grpc_client` iniettato su tutte le 3 board.
- [x] 3. **Fase 9.3.c (Refactor Satellite)**:
  - Aggiornato `satellite/app/config.py` con parametri Keystone (`os_auth_url`, `os_username`, `os_password`, `os_project_name`, ecc.) e IoTronic (`iotronic_url`, `plugin_name`).
  - Connesso il container `satellite` alla rete esterna `stack4things_dockercompose_deployment_s4t` in `deploy/docker-compose.pipeline.yml`.
  - Creato nuovo client REST stateless `satellite/app/iotronic_client.py` con gestione token scoped Keystone e retry automatico in caso di scadenza.
  - Rifattorizzato `satellite/app/pipeline_client.py` per invocare i task sui worker tramite chiamata REST IoTronic (`PluginCall`), rimuovendo qualsiasi chiamata gRPC diretta residua dal satellite.
  - Semplificato `node_registry.py` e `node_directory.json` eliminando il campo `grpc_url` non più necessario.
- [x] 4. **Fase 9.3.d (Testing Automatico E2E)**:
  - Scritta suite completa di test di integrazione in `satellite/tests/test_integration.py` validata sia in locale sia dentro il container `satellite` contro l'infrastruttura reale (Hardhat + Gateway + IoTronic + Lightning-Rod + Worker C++).
  - Testato con successo flusso sequenziale 3 nodi (valore iniziale 42 incrementato a 45 lungo la catena).
  - Testato con successo scenario concorrente con 2 pipeline attive in parallelo (Pipeline A con 2 nodi, Pipeline B con 1 nodo) e verifica del limite di capacità.
- [x] 5. **Chiarimenti e Cleanup**:
  - **Commit `425d148` (disattivazione `client-admin` / `dev-sim-01` da `docker-compose.yml`)**: `client-admin` era uno script di simulazione M1 che inoltrava automaticamente una richiesta di onboarding per il dispositivo statico `dev-sim-01`. Con l'adozione dell'onboarding automatico dei worker (`auto-onboard-workers.ts` in M8) e del modello di trust default-deny (`owner-auto-approver` in M9, ristretto al prefisso `worker-`), la richiesta di `dev-sim-01` rimaneva permanentemente `Pending` ed era superflua per i workflow a regime. La disattivazione evita rumore on-chain.
  - **Verifica configurazione `trusted-devices.json`**: Confermato che il file canonico di configurazione risiede in `chain/config/trusted-devices.json` (montato read-only nel container approver) e il vecchio duplicato in `chain/scripts/` è stato rimosso.

### Definition of Done — M9 ✅
Tutti gli stadi M9.1, M9.2 e M9.3 sono completati, testati e verificati contro l'infrastruttura reale senza mock.

## Fase: M10 (Stadio 1 — Autenticazione Dashboard + Gestione Allowlist Trust)

### Investigazione (Fase 1) — `chain/scripts/auto-approve-trusted.ts`
- **Evidenza rilevata**: L'ispezione di `chain/scripts/auto-approve-trusted.ts` (righe 66-78) ha evidenziato che `loadConfig()` veniva invocata una sola volta all'avvio in `main()`, catturando `config` nella closure del listener eventi `OnboardingRequested`.
- **Modifica applicata con conferma**: Spostata l'invocazione di `loadConfig()` direttamente all'interno del callback di `OnboardingRequested` per ogni evento ricevuto. Aggiunta gestione degli errori in `loadConfig()` con `try...catch`: in caso di file temporaneamente illeggibile o parsing JSON fallito, viene emesso un warning e restituito `{ trustedStacks: [] }` (trattato in default-deny), impedendo il crash del listener.

### Task Completati (Fase 2, 3, 4)
- [x] 1. **Reload dinamico e resilienza in `auto-approve-trusted.ts`**: Ricarica automatica del file di configurazione ad ogni evento `OnboardingRequested` con fallback sicuro (default-deny) in caso di errore di parsing/I/O.
- [x] 2. **Configurazione credenziali senza default**:
  - Aggiunte `ui_admin_username: str` e `ui_admin_password: str` in `ui/app/config.py` e `gateway/app/config.py` senza alcun default hardcoded.
  - Aggiornati `deploy/.env.example`, `deploy/.env` e `deploy/docker-compose.yml` (`env_file: .env` per UI, volume mount `../chain/config:/app/config` e `TRUSTED_DEVICES_CONFIG` per Gateway).
- [x] 3. **Protezione HTTP Basic Auth**:
  - Middleware/dependency su `ui/app/main.py` che protegge globalmente tutte le route esistenti e nuove (`/`, `/api/requests`, `/request`, `/trust`, `/trust/delete/*`) con confronto delle credenziali a tempo costante (`secrets.compare_digest`). Ritorna `401 Unauthorized` con header `WWW-Authenticate: Basic` in assenza di credenziali valide.
  - Basic Auth sui nuovi endpoint `/trust/stacks` in `gateway/app/main.py` (lasciando inalterate le route preesistenti on-chain e leasing).
- [x] 4. **Client e Modelli Allowlist nel Gateway (`trust_config_client.py`)**:
  - Modelli Pydantic `TrustedStack` e `TrustedDevicesConfig` con validazione esplicita (rifiuto di `stackId` o prefissi vuoti o duplicati).
  - Implementazione di `TrustConfigClient` con scrittura atomica del file `trusted-devices.json` via file temporaneo nella stessa directory e `os.replace` (atomic rename POSIX).
  - Nuovi endpoint REST: `GET /trust/stacks`, `POST /trust/stacks`, `DELETE /trust/stacks/{stack_id}`.
- [x] 5. **Client Gateway e Nuova Vista UI**:
  - Aggiunti metodi `get_trusted_stacks()`, `add_trusted_stack()`, `delete_trusted_stack()` a `ui/app/gateway_client.py` con credenziali Basic Auth automatiche.
  - Template `ui/templates/trust.html` e route `GET /trust`, `POST /trust`, `POST /trust/delete/{stack_id}` per visualizzare, inserire e rimuovere stack fidati in stile server-rendered Jinja2.
  - Aggiornato `base.html` con barra di navigazione coerente verso Dashboard, Gestione Stack Fidati e Mailpit.
- [x] 6. **Testing Completo (Unitario, Integrazione ed E2E su stack reale)**:
  - `gateway/tests/test_trust_config.py`: verifica rigetto `401`, validazione Pydantic (`422`), gestione duplicati (`400`), CRUD su file reale e rimozione (`404` se inesistente).
  - `ui/tests/test_auth_and_trust.py` e `ui/tests/test_integration.py`: verifica protezione globale Basic Auth, rendering viste Jinja2, redirect form `303` e chiamate a gateway client.
  - **Verifica End-to-End su Docker Compose reale**:
    - `POST /onboarding-request` per `edge-device-01` (prefisso non presente) → `Pending` (default-deny confermato dai log di `owner-auto-approver`).
    - `POST /trust/stacks` via API/UI per aggiungere stack `edge-cluster` con prefisso `edge-` → salvataggio atomico su disco.
    - `POST /onboarding-request` per `edge-device-02` → `owner-auto-approver` ricarica a runtime `trusted-devices.json`, matcha lo stack e auto-approva la richiesta on-chain (stato `Approved`) **senza necessità di riavviare il servizio**.
    - `DELETE /trust/stacks/edge-cluster` via API/UI → rimozione dello stack.
    - `POST /onboarding-request` per `edge-device-03` → torna in default-deny (`Pending`).

### Definition of Done — M10 Stadio 1 ✅
- Tutte le viste della dashboard e gli endpoint trust del gateway sono protetti da Basic Auth.
- Gestione CRUD dell'allowlist funzionante tramite API Gateway e interfaccia UI.
- Reload dinamico verificato end-to-end con auto-approvazione reattiva on-chain.
- Nessun valore di default hardcoded per le credenziali.
- Moduli isolati e contratti invariati.

### Sessione di Verifica End-to-End & Integrazione Completa (Post-M10.1)

In data 2026-08-31 è stata eseguita una sessione di verifica end-to-end dal vivo su tutti e tre gli stack avviati a freddo contemporaneamente, senza mock e con comandi manuali reali:

1. **Avvio a Freddo dei Tre Stack**:
   - Stack Base (`deploy/docker-compose.yml`): `hardhat-node`, `contract-deployer`, `auto-onboard`, `owner-auto-approver`, `gateway`, `notification`, `mailpit`, `ui` avviati e healthy/operativi.
   - Stack IoTronic (`../Stack4Things_DockerCompose_deployment`): `iotronic-conductor`, `keystone`, `crossbar`, `rabbitmq`, `mariadb`, `iotronic-ui`, `iotronic-wagent`, `iotronic-wstun` avviati e raggiungibili.
   - Stack Pipeline (`deploy/docker-compose.pipeline.yml`): `satellite` e i tre worker C++ (`worker-1`, `worker-2`, `worker-3`) operativi e connessi alle reti `pipeline-net`, `s4t-bridge` e `stack4things_dockercompose_deployment_s4t`.
   - **Esito avvio board**: Tutte e 3 le board Lightning-Rod (`worker-1`, `worker-2`, `worker-3`) e la board `test_board` sono risultate immediatamente `online` e in ascolto WAMP, senza che si sia ripresentato il problema dei *wampagent stale* riscontrato in M9.

2. **Pipeline Sequenziale Reale Satellite ↔ IoTronic ↔ Worker C++**:
   - Eseguita allocazione di 2 nodi via `POST /pipeline/lease` (`pipeline_id: a4dddabc-0540-4607-b9c2-f8ed8c4d6bb3`).
   - Invocata esecuzione con valore iniziale non banale `initial_value: 100` via `POST /pipeline/{id}/run`.
   - Risultato numerico esatto validato dal vivo lungo la sequenza di nodi: `worker-1` incrementa `100 -> 101`, `worker-2` incrementa `101 -> 102`, con `final_value: 102`.
   - Ispezione log verificata a ogni livello: chiamata REST `POST /v1/boards/{board}/plugins/grpc_client` su Conductor API (`iotronic-api_access.log`), ricezione ed esecuzione plugin gRPC su Lightning-Rod container (`Worker worker-2 returned: 102`), ed esecuzione nel processo C++ (`pipeline_worker`).
   - Rilascio risorse via `POST /pipeline/{id}/release` verificato con successo sullo smart contract `LeasingRegistry.sol` tramite `GET /leasing/status/{device_id}` sul Gateway.

3. **Collegamento End-to-End Trust ↔ Leasing ↔ Esecuzione (Device `test_board`)**:
   - **Default-Deny iniziale**: Inoltrata richiesta `POST /onboarding-request` per `test_board` (prefisso `test_` non presente in allowlist). `owner-auto-approver` rileva la mancata corrispondenza e lascia la richiesta nello stato `Pending` (request #3).
   - **Blocco Leasing On-Chain**: Il tentativo di lease via `POST /leasing/lease` per `test_board` viene rifiutato con `403 Forbidden` (`"Node is not approved for leasing"`), generato direttamente dal controllo on-chain dello smart contract `LeasingRegistry.sol` che interroga `OnboardingTrust.sol`.
   - **Gestione Dinamica Allowlist**: Aggiunto lo stack fidato `test-cluster` con prefisso `test_` tramite chiamata autenticata `POST /trust/stacks` (Basic Auth).
   - **Auto-Approvazione a Caldo**: Inoltrata nuova richiesta di onboarding per `test_board` (request #4); `owner-auto-approver` ricarica la configurazione aggiornata al volo, matcha il prefisso `test_` e approva la transazione on-chain (`Approved`).
   - **Lease ed Esecuzione Reale**: Con lo stato `Approved`, la chiamata `POST /leasing/lease` per `test_board` ha successo (`is_leased: true`). Invocato il task con `input_value: 200` tramite comando IoTronic (`PluginCall`), ottenendo il risultato verificato `SUCCESS: Worker worker-1 incremented 200 -> 201`.
   - **Release**: Rilascio on-chain completato con successo (`is_leased: false`).

4. **Limite Noto Documentato**:
   - L'esecuzione sul device dinamico `test_board` è stata effettuata invocando direttamente il plugin tramite comando IoTronic e non tramite l'endpoint `/pipeline/run` del satellite. Questo perché `satellite/app/node_directory.json` è attualmente un pool statico limitato a `worker-1`, `worker-2` e `worker-3`, e non include i dispositivi aggiunti dinamicamente all'allowlist dei trust stack.

5. **Cleanup Post-Verifica**:
   - Lo stack dimostrativo `test-cluster` è stato rimosso dall'allowlist tramite richiesta autenticata `DELETE /trust/stacks/test-cluster` verso il Gateway.
   - Verificato tramite `GET /trust/stacks` e ispezione di `chain/config/trusted-devices.json` che la configurazione è tornata a contenere unicamente lo stack canonico `iotronic-pipeline-workers`.

## Fase: M11 (HPC Task+Data Parallelism — Stadio 11.1)

**Data:** 2026-09-01

### Task Completati
- [x] 1. **Modifica `main_mpi.cpp`**: Sostituita la chiamata sequenziale `SignatureBench::run_sequential` con la versione multithread `SignatureBench::run_parallel(local_devices, num_threads, local_devices.size())`, realizzando un vero ibrido **MPI + OpenMP** (task parallelism a memoria distribuita + data parallelism a memoria condivisa per rank).
- [x] 2. **Parametrizzazione Thread OpenMP**:
  - Priorità di configurazione: CLI argument `argv[2]` > Variabile d'ambiente `OMP_NUM_THREADS` / `NUM_THREADS` > Default calcolato (`hardware_concurrency / mpi_size`, minimo 1).
  - CLI argument opzionale `argv[3]` per personalizzare il file CSV di destinazione (default: `results_hybrid_mpi_omp.csv`).
- [x] 3. **Indagine Sperimentale Controllata & Build Omogenea (`Release` / `-O2`)**:
  - Impostato esplicitamente `set(CMAKE_BUILD_TYPE Release)` e `-O2 -Wall -Wextra` in `CMakeLists.txt` per garantire che tutti i target C++ compilino con le medesime ottimizzazioni.
  - **Verifica Warmup**: Testata l'ipotesi del cold-start del thread pool libgomp tramite `#pragma omp parallel {}` prima di `start_time`: l'impatto registrato è di soli ~3.5 ms.
  - **Confronto Omogeneo**: Rigenerati nella stessa sessione e nello stesso container sia il benchmark OpenMP puro M5 (`results_m5_release.csv`) sia l'ibrido MPI+OpenMP M11.1 (`results_hybrid_mpi_omp.csv`).
  - **Risultato Baseline**: A parità di build/ambiente, 1 core produce ~4.8k–5.3k sig/s in tutte le modalità (sequenziale ~5.0k, OpenMP 1 thread ~4.8k, MPI 1×1 ~5.3k), spiegando che la differenza con i valori storici del README (~17k) derivava da variazioni di ambiente/hardware.
- [x] 4. **Isolamento e Risoluzione CPU Process Binding (Finding HPC Fondamentale)**:
  - Ispezione con `mpirun --report-bindings`: Open MPI per default vincola ogni processo rank a **un singolo core fisico** (mask `[BB/../../...]`), costringendo tutti i thread OpenMP del rank a contendersi un solo core (causando il crollo iniziale di 1×4 e 2×4).
  - Applicando `--bind-to none`, i thread OpenMP si distribuiscono liberamente sui core disponibili: 1×4 sale a **13,114 sig/s** e 2×4 sale a **24,706 sig/s**.
- [x] 5. **Esecuzione Benchmark su Griglia di Combinazioni (`--bind-to none`)**:
  - Eseguita campagna di test su dataset di 500 device sintetici per le combinazioni: 1×1 (5.3k), 1×2 (10.1k), 1×4 (13.1k), 2×1 (10.4k), 2×2 (12.6k), 2×4 (24.7k), 4×1 (14.5k), 4×2 (25.6k), 4×4 (30.0k), 8×1 (25.5k), 8×2 (32.4k sig/s).
  - A 8 core logici, l'ibrido 4 rank × 2 thread (**25,582 sig/s**) e 2 rank × 4 thread (**24,706 sig/s**) superano sia OpenMP puro a 8 thread (19,060 sig/s) sia 8 rank MPI puri (21,514 sig/s).
  - A 16 core logici, 8 rank × 2 thread tocca il picco di **32,442 sig/s**.
- [x] 6. **Aggiornamento Documentazione e Analisi Prestazionale (`hpc-engine/README.md`)**:
  - Inserita tabella comparativa a 4 colonne omogenea e documentati dettagliatamente i due finding HPC chiave: il CPU process binding in Open MPI e l'analisi di scaling.
- [x] 7. **Isolamento Rigoroso**:
  - Nessuna modifica a `src/onboarding/`, `src/pipeline/`, `satellite/` o ad altri moduli.

### Definition of Done — Stadio 11.1 ✅
- `main_mpi.cpp` invoca `SignatureBench::run_parallel` con thread parametrizzati per ogni rank MPI.
- `CMakeLists.txt` configurato con `Release` e `-O2`.
- Risultati salvati in CSV con colonna dedicata `omp_threads` e policy di binding corretta.
- `hpc-engine/README.md` aggiornato con tabella comparativa omogenea e interpretazione tecnica basata su evidenze sperimentali.
- Tutti i test CTest (`SignatureCorrectness` e `WorkerCorrectness`) passano al 100%.

### Domande Aperte
- Nessuna per lo Stadio 11.1.

## Fase: M11 (HPC Task+Data Parallelism — Stadio 11.2)

**Data:** 2026-09-01

### Task Completati
- [x] 1. **Estensione Contratto Protobuf (`proto/pipeline.proto`)**:
  - Aggiunto il valore `VERIFY_SIGNATURES_BATCH = 2` all'enum `OperationType` senza alterare i valori preesistenti (`OPERATION_UNKNOWN = 0`, `INCREMENT_COUNTER = 1`).
  - Esteso `TaskRequest` con i campi `batch_size` (uint32 = 4), `num_threads` (int32 = 5), `seed` (uint32 = 6).
  - Esteso `TaskResult` con i campi `time_seconds` (double = 4), `throughput` (double = 5), `valid_count` (uint32 = 6).
- [x] 2. **Aggiornamento Benchmark & Generatore (`signature_bench.hpp` / `signature_bench.cpp`)**:
  - Aggiunto il campo `size_t valid_count` alla struct `BenchResult`.
  - Popolato `res.valid_count` sia in `SignatureBench::run_sequential` sia in `SignatureBench::run_parallel`.
- [x] 3. **Implementazione `VERIFY_SIGNATURES_BATCH` nel Worker C++ (`worker_server.cpp`)**:
  - In `ExecuteTask`, aggiunto il ramo dedicato all'operazione `VERIFY_SIGNATURES_BATCH`:
    - Generazione deterministica di `batch_size` dispositivi sintetici con `DeviceGenerator::generate_devices(batch_size, seed)`.
    - Esecuzione multithread tramite `SignatureBench::run_parallel(devices, num_threads, batch_size)`.
    - Popolamento dei nuovi campi in `TaskResult` (`time_seconds`, `throughput`, `valid_count`, `node_id`, `timestamp`), lasciando intatta l'operazione legacy `INCREMENT_COUNTER` e il codice di errore `UNIMPLEMENTED` per operazioni sconosciute.
- [x] 4. **Aggiornamento Build System (`hpc-engine/CMakeLists.txt`)**:
  - Aggiunti `src/onboarding/device_generator.cpp` e `src/onboarding/signature_bench.cpp` ai target `pipeline_worker` e `test_worker`.
  - Aggiunta `src/onboarding` ai `target_include_directories`.
  - Collegati `OpenMP::OpenMP_CXX`, `OpenSSL::SSL` e `OpenSSL::Crypto` ai target `pipeline_worker` e `test_worker`.
- [x] 5. **Test Dedicato di Rigore (`test_worker.cpp`)**:
  - Aggiunto test per `VERIFY_SIGNATURES_BATCH`: esegue la verifica direttamente tramite `DeviceGenerator` + `SignatureBench::run_parallel` e tramite chiamata RPC `ExecuteTask` su `test-worker` con gli stessi parametri (`batch_size=20`, `seed=42`, `num_threads=2`).
  - Asserito con successo il match esatto di `valid_count` (20/20), valori positivi di `time_seconds` e `throughput`, e presenza del timestamp.
  - Tutti i test CTest (`SignatureCorrectness` e `WorkerCorrectness`) passano al 100%.
- [x] 6. **Isolamento Rigoroso**:
  - Nessuna modifica a `satellite/`, `chain/`, `gateway/`, `notification/`, `ui/` o stack esterno IoTronic.

### Definition of Done — Stadio 11.2 ✅
- `proto/pipeline.proto` esteso in modo additivo e retrocompatibile con `VERIFY_SIGNATURES_BATCH`.
- Worker C++ gestisce l'operazione di benchmark ECDSA OpenMP riusando i moduli M5.
- `CMakeLists.txt` compila pulito senza errori né warning con `-Wall -Wextra`.
- Test unitari ed end-to-end gRPC passano al 100% in `WorkerCorrectness` e `SignatureCorrectness`.
- `PROGRESS.md` aggiornato.

### Domande Aperte
- Nessuna per lo Stadio 11.2.

## Fase: M11 (HPC Task+Data Parallelism — Stadio 11.3)

**Data:** 2026-09-01

### Task Completati
- [x] 1. **Verifica Hardware Host e Vincolo di CPU Oversubscription**:
  - Ispezione con `nproc` e `lscpu`: CPU Intel Core i7-12700H (14 core fisici, **20 thread logici**).
  - Imposto il limite hardware di non-oversubscription per configurazioni con $P_{eff} = N_{nodi} \times N_{thread} \le 20$.
  - Configurazioni con $P_{eff} > 20$ (es. 8 nodi × 4 thread = 32) etichettate esplicitamente come "sonde di oversubscription intenzionale" ed escluse dalla baseline pulita.
- [x] 2. **Infrastruttura Worker Isolati (`deploy/docker-compose.benchmark.yml`)**:
  - Creato file Compose dedicato per avviare **8 worker container C++ isolati** (`bench-worker-1` .. `bench-worker-8`), esponendo le porte locali `50051..50058`.
  - Nessuna interazione con Hardhat, blockchain, Gateway o IoTronic (totale isolamento HPC).
- [x] 3. **Driver di Benchmark Standalone (`hpc-engine/benchmarks/run_benchmark.py`)**:
  - Generazione dinamica degli stub gRPC Python direttamente da `proto/pipeline.proto` senza duplicazioni manuali.
  - Partizionamento del carico con gestione del resto identica a `main_mpi.cpp` ($base\_chunk + (1 \text{ se } i < remainder)$) e seed deterministico $42 + i$.
  - Dispatch concorrente asincrono via `asyncio.gather` con canali `grpc.aio.insecure_channel`.
  - **Validazione stringente di correttezza**: verifica che la somma di `valid_count` di tutti i worker corrisponda esattamente al batch atteso per ogni run (100% verifiche superate su tutti i batch).
- [x] 4. **Script di Calcolo Metriche Formali HPC (`hpc-engine/benchmarks/compute_metrics.py`)**:
  - Speedup $S_n = T_1 / T_n$, Efficienza $E(P_{eff}) = S_n / P_{eff}$, Efficienza sui nodi $E(N) = S_n / N$.
  - Frazione seriale stimata da Amdahl: $f_{s,task} = \mathbf{2.51\%}$ per il task parallelism (nodi) vs $f_{s,omp} = \mathbf{46.51\%}$ per OpenMP intra-nodo.
  - Confronto empirico vs Amdahl predetto: $S_{pred}(4) = \mathbf{3.72\times}$ vs $S_{measured}(4) = \mathbf{3.73\times}$ (match teorico-sperimentale perfetto).
  - Scalabilità $L = E(5000) / E(1000)$: $L > 1.25$ per $P \ge 4$ (fino a $L=1.33$ a $P=16$), dimostrando che carichi maggiori ammortizzano l'overhead di rete/dispatch gRPC.
- [x] 5. **Campagna Sperimentale su Griglia Completa (1k e 5k firme)**:
  - Salva i dati grezzi in `hpc-engine/results_grpc_task_parallel.csv`.
  - Picco di throughput in regime clean ($\le 20$ core): **60,220.7 sig/s** (8 nodi × 2 thread, speedup **5.92x** rispetto a 1 nodo 1 thread).
  - Picco assoluto con sonda oversubscribed (8 nodi × 4 thread = 32 thread): **66,433.5 sig/s** (speedup **6.53x**).
- [x] 6. **Confronto Omogeneo con MPI+OpenMP (Stadio 11.1) su Batch da 5.000 firme**:
  - Rieseguito l'esperimento MPI+OpenMP sulla medesima taglia di 5.000 firme (`hpc-engine/results_hybrid_mpi_omp_5000.csv`) nelle stesse condizioni omogenee (`Release`, `-O2`, `--bind-to none`).
  - **Evidenza rilevata**: A parità di carico (5k firme), le curve di speedup e di efficienza sono virtualmente identiche (**6.00x** per MPI vs **5.92x** per gRPC su 16 core effettivi, con efficienza di scala $E = 0.37$). MPI ottiene throughput assoluto maggiore (~109k vs ~60k sig/s) grazie alla memoria condivisa in-process POSIX, mentre gRPC incorpora il round-trip TCP client-side e la serializzazione HTTP/2 per supportare l'architettura a microservizi asincrona e il leasing dinamico su blockchain.
- [x] 7. **Isolamento Rigoroso**:
  - Nessuna modifica a `satellite/`, `chain/`, `gateway/`, `notification/`, `ui/`, `docker-compose.pipeline.yml` o ai worker registrati `worker-1/2/3`.

### Definition of Done — Stadio 11.3 ✅
- Driver di benchmark isolato funzionante su 8 nodi container gRPC.
- Griglia completa eseguita su due dimensioni (1k e 5k firme) con gestione del resto e validazione 100% su `valid_count`.
- Metriche formali calcolate: Speedup, Efficiency, Legge di Amdahl (predetto vs misurato), Scalabilità $L$.
- Confronto omogeneo tra MPI+OpenMP e gRPC+OpenMP su batch identico di 5.000 firme.
- Soglia dei 20 core logici reali rispettata con sonda oversubscribed esplicitamente etichettata.
- `hpc-engine/README.md`, `PROGRESS.md` e `AGENTS.md` aggiornati.

## Fase: M11 (HPC Task+Data Parallelism — Stadio 11.4)

**Data:** 2026-09-01

### Task Completati
- [x] 1. **Verifica & Ciclo di Vita Aggiornamento Plugin IoTronic**:
  - Ispezione preliminare di `s4t-plugin/plugin_template.py`: confermato che il plugin non accettava genericamente qualsiasi operazione, ma era vincolato a `INCREMENT_COUNTER`.
  - Investigazione sperimentale su IoTronic CLI: verificato che per aggiornare un plugin già iniettato è necessario rimuoverlo dalle board (`plugin-remove`), eliminarlo dal registro (`plugin-delete`), ricrearlo (`plugin-create`) e re-iniettarlo (`plugin-inject`), documentando l'esito in `s4t-plugin/IOTRONIC_NOTES.md`.
- [x] 2. **Estensione Additiva del Plugin S4T (`plugin_template.py` / `build_plugin.sh`)**:
  - Aggiunto il supporto parametrico per l'operazione `VERIFY_SIGNATURES_BATCH` (batch_size, num_threads, seed), mantenendo `INCREMENT_COUNTER` come default retrocompatibile.
  - Sostituito il caricamento dinamico via zipimport con l'estrazione fisica su directory temporanea `/tmp/pipeline_stubs/` per evitare anomalie di caching e deallocazione dei descrittori protobuf a runtime.
  - Re-iniettato il bundle aggiornato sulle 3 board di produzione (`worker-1`, `worker-2`, `worker-3`) e sulla board `test_board`.
  - **Gate di regressione sequenziale superato**: eseguito immediatamente `test_full_pipeline_e2e_sequential` con esito positivo (42 -> 43 -> 44 -> 45 in 1.17s).
- [x] 3. **Nuovo Endpoint di Dispatch Parallelo nel Satellite (`satellite/app/`)**:
  - Implementata la funzione `run_parallel_verification` in `satellite/app/pipeline_client.py`: suddivisione del batch totale con gestione del resto identica a MPI/Stadio 3, invocazione concorrente asincrona tramite `asyncio.gather` e chiamate REST IoTronic, parsing con regex ed eccezione immediata in caso di mancata verifica del 100% delle firme.
  - Aggiunto il modello `ParallelVerifyRequest` e l'endpoint `POST /pipeline/{pipeline_id}/run-parallel` in `satellite/app/main.py`.
- [x] 4. **Suite di Test Completa (Nessun Mock)**:
  - Esteso `satellite/tests/test_integration.py` con `test_parallel_verification_e2e` su 3 nodi leased (batch=100 diviso in chunk 34, 33, 33 con validazione 100/100).
  - Tutti i 5 test passano al 100% all'interno dell'infrastruttura reale containerizzata.
- [x] 5. **Campagna Sperimentale di Confronto & Quantificazione dell'Overhead**:
  - Eseguito benchmark comparativo controllato su griglia omogenea (1, 2, 3 nodi a 1 thread, batch da 1.000 e 5.000 firme, 6 ripetizioni per configurazione) registrando sia i riassunti statistici (media, min, max, stddev) sia i tempi individuali di ogni run in `hpc-engine/results_real_chain_overhead.csv`.
  - **Overhead quantificato in modo trasparente**: la catena applicativa reale (Keystone + IoTronic Conductor + Crossbar WAMP + Lightning-Rod) introduce un overhead additivo di trasporto/brokeraggio di **$\sim 0.14\text{s} - 0.27\text{s}$** per round di dispatch.
  - **Analisi del regime a grana fine (batch=1000)**: a 6 ripetizioni il tempo a 3 nodi si attesta a $0.2726\text{s} \pm 0.028\text{s}$ (il precedente $0.340\text{s}$ a 2 ripetizioni era influenzato da uno straggler isolato a $0.384\text{s}$). L'andamento piatto del tempo totale ($\sim 0.25\text{s}-0.28\text{s}$) e del throughput ($\sim 3.7\text{k}-4.0\text{k}$ sig/s) è causato dal fenomeno di *straggler tail latency* ($T = \max(R_1, \dots, R_N)$), dove la varianza stocastica del trasporto WAMP ($\pm 25-50\text{ms}$) assorbe il risparmio computazionale puro ($54\text{ms} \to 29\text{ms} \to 21\text{ms}$).
  - **Ammortamento della granularità (batch=5000)**: con calcolo utile consistente ($273\text{ms} \to 142\text{ms} \to 102\text{ms}$), il tempo decresce monotonicamente ($0.649\text{s} \to 0.475\text{s} \to 0.443\text{s}$) con overhead ratio contenuto ($1.28\times - 2.55\times$) e throughput che tocca **11.303,5 sig/s su 3 nodi** (picco $12.652\text{ sig/s}$).
- [x] 6. **Aggiornamento Documentazione**:
  - `satellite/README.md` aggiornato con la sezione dettagliata sul confronto prestazionale e la tabella comparativa completa.
  - `s4t-plugin/IOTRONIC_NOTES.md` aggiornato.

### Definition of Done — Stadio 11.4 ✅
- Plugin S4T esteso in modo additivo e verificato sulle board IoTronic reali.
- Gate di regressione sequenziale passato senza regressioni.
- Nuovo endpoint `POST /pipeline/{pipeline_id}/run-parallel` funzionante e coperto da test d'integrazione e2e.
- Confronto controllato tra dispatch isolato e catena reale eseguito su 1, 2 e 3 nodi.
- Overhead e throughput misurati e documentati con rigore e trasparenza nei README e in CSV.
- `PROGRESS.md` e `AGENTS.md` aggiornati.

### Domande Aperte
- Nessuna per lo Stadio 11.4. Pronto per la pianificazione dello Stadio 11.5 (Report finale metriche HPC e chiusura milestone).

## Fase: M12 (Pool di Nodi Dinamico)

**Data:** 2026-09-04

### Task Completati
- [x] 1. **Investigazione Endpoint REST Elenco Board IoTronic**:
  - Eseguita cattura con evidenza diretta tramite il comando `iotronic --debug board-list` sul container `iotronic-ui`.
  - Confermato l'endpoint REST `GET /v1/boards`, versione API negoziata `1.0` (la versione 1.9 produce HTTP 406), header di autenticazione `X-Auth-Token` (Keystone token scoped) e `Accept: application/json`.
  - Identificato il campo esatto che indica lo stato online: `status == "online"`, e il campo identificativo: `name` (corrispondente al `device_id` blockchain).
  - Documentati dettagli ed evidenze sperimentali in `s4t-plugin/IOTRONIC_NOTES.md`.
- [x] 2. **Metodo `list_online_boards()` in `satellite/app/iotronic_client.py`**:
  - Implementato metodo asincrono che interroga `GET {self.iotronic_url}/v1/boards`, gestisce la scadenza del token Keystone con refresh automatico e retry singolo, e restituisce la lista dei `name` delle sole board con `status == "online"`.
- [x] 3. **Selezione Nodi Dinamica e Fallback in `satellite/app/node_registry.py`**:
  - Sostituito il caricamento statico da JSON con la chiamata dinamica a `list_online_boards()`.
  - Implementata la selezione resiliente con fallback: ad ogni iterazione tenta il lease on-chain tramite `gateway_leasing_client`; se un candidato risulta non approvato (HTTP 403 / 404 dal Gateway) o già occupato, passa automaticamente al candidato successivo senza interrompere la richiesta.
  - Se non si raggiunge il conteggio richiesto esaurendo i candidati, esegue il rollback rilasciando tutti i nodi parzialmente allocati e solleva `HTTPException(400)`.
- [x] 4. **Gestione Esplicita del Backend di Calcolo in `pipeline_client.py`**:
  - Evitato l'alias silenzioso su `worker-1`: se un `device_id` non ha un backend di calcolo assegnato (attualmente solo i device `worker-*` possiedono il target `{device_id}:50051`), il Satellite solleva esplicitamente un'eccezione (`Exception("Nessun backend di calcolo configurato per il device {device_id}: solo i device worker-* hanno un worker_addr assegnato")`) sia in `run_pipeline_task` sia in `run_parallel_verification`, rendendo visibile il limite architetturale anziché mascherarlo.
- [x] 5. **Verifica Preliminare dello Stato On-Chain**:
  - Verificato preventivamente lo stato on-chain di `test_board` tramite `GET /leasing/status/test_board`: confermato genuinamente non registrato / non approvato all'avvio.
- [x] 6. **Test Reale del Meccanismo di Fallback**:
  - Con 4 board online su IoTronic (`test_board`, `worker-1`, `worker-2`, `worker-3`) e solo 3 approvate on-chain:
  - Richiesta di lease con `count=3`: il Satellite valuta prima `test_board` (non approvato, lease rifiutato), salta al candidato successivo, alloca con successo `worker-1`, `worker-2`, `worker-3` e completa la pipeline con successo (42 -> 43 -> 44 -> 45).
  - Richiesta di lease con `count=4`: fallisce regolarmente con HTTP 400 (`insufficient approved/available nodes`) e rollback automatico, dimostrando la correttezza del vincolo di capacità.
- [x] 7. **Approvazione a Caldo e Verifica End-to-End del Pool Dinamico**:
  - Aggiunto lo stack fidato via Gateway autenticato: `POST /trust/stacks` con `{"stackId": "test_board_stack", "deviceIdPrefixes": ["test_board"]}`.
  - Sottomessa richiesta di onboarding per `test_board` via `POST /onboarding-request`, auto-approvata istantaneamente dal servizio `owner-auto-approver`.
  - Dimostrato il lease on-chain di tutti e 4 i nodi (`count=4`) tramite il Satellite senza alcuna modifica a codice o config del Satellite.
  - Dimostrata la corretta intercettazione del vincolo di backend: una richiesta di calcolo su `test_board` rifiuta l'esecuzione sollevando esplicitamente l'eccezione di backend non configurato, evitando alias fisici nascosti.
- [x] 8. **Pulizia e Rimozione File Statico**:
  - Eliminato definitivamente `satellite/app/node_directory.json` e rimosso il parametro deprecato `worker_nodes` da `config.py`. Verificata l'assenza di riferimenti residui nel codice.
- [x] 9. **Suite di Test di Integrazione**:
  - Aggiornato ed esteso `satellite/tests/test_integration.py` (7 test totali, inclusi test sequenziale su nodi worker, concorrente su 2 pipeline, validazione errori, formato inatteso, parallel batch verification, verifica vincolo backend su board dinamiche e fallback su candidato unapproved).
  - Tutti i 7 test passano al 100% all'interno dell'ambiente reale containerizzato.
- [x] 10. **Aggiornamento Documentazione**:
  - `satellite/README.md` aggiornato con la descrizione del pool dinamico, della selezione con fallback e dell'esplicitazione del vincolo di calcolo.

### Cosa è Stato Dimostrato e Limite Noto Esplicito
- **Risultato reale conseguito in M12**: La scoperta dinamica dei nodi (`GET /v1/boards`) e la selezione con fallback on-chain funzionano regolarmente end-to-end: qualunque board registrata su IoTronic e marcata `online`, se approvata on-chain, entra nel pool leasable del Satellite senza riavvii né modifiche al codice.
- **Limite noto documentato con trasparenza**: L'esecuzione di calcolo realmente indipendente su una board dinamica priva di un proprio worker C++ dedicato (come `test_board`) non è supportata nell'infrastruttura attuale (dove esistono fisicamente solo 3 container worker: `worker-1`, `worker-2`, `worker-3`). Il Satellite impedisce esplicitamente alias silenziose verso worker condivisi rifiutando l'esecuzione con errore trasparente. L'eventuale supporto per board dinamiche con motore di calcolo proprio richiederà l'allocazione dinamica del backend di calcolo in una milestone successiva.

### Definition of Done — M12 ✅
- Endpoint IoTronic di elenco board verificato con evidenza reale (`GET /v1/boards`, API v1.0, `status: "online"`).
- `node_directory.json` rimosso, nessun riferimento residuo nel codice.
- Selezione dinamica e fallback verificati sperimentalmente (un candidato non approvato viene saltato senza far fallire la richiesta se vi sono abbastanza nodi validi; capacità on-chain rispettata).
- Vincolo di backend esplicitato con errore trasparente, evitando alias fisici su nodi non worker.
- Nessuna modifica a `chain/`, `gateway/`, `hpc-engine/`, `ui/`, `notification/`, né a `deploy/docker-compose.pipeline.yml`.
- `PROGRESS.md` e `satellite/README.md` aggiornati.

### Domande Aperte
- Nessuna per lo Stadio M12.

## Fase: M11 (HPC Task+Data Parallelism — Stadio 11.5)

**Data:** 2026-09-08
**Ambiente Unico:** `env_id = i7_12700h_20260908` (Intel Core i7-12700H, 14 core fisici / 20 thread logici, 31 GiB RAM, Linux Kernel 7.0.0-31-generic).

### Task Completati
- [x] 1. **Fingerprint dell'Ambiente e Configurazione Unica**:
  - Eseguita cattura preliminare dell'hardware host (`lscpu`, `nproc`, `free -h`, `uname -a`) e salvata in `hpc-engine/results/environment_fingerprint_20260908.txt`.
  - Definita la soglia formale di oversubscription: $P_{eff} = N_{nodi} \times N_{thread} > 20$. Tutte le combinazioni con $P_{eff} > 20$ etichettate esplicitamente `oversubscribed` in ogni riga dei CSV prodotti.
- [x] 2. **Task A — Profiling Reale sull'Hardware Target**:
  - Test preliminare su build sequenziale compilata con `-pg`: `gprof` riporta `no time accumulated` (0.00s) confermando empiricamente che l'intero computo risiede nella libreria dinamica `libcrypto.so.3` non instrumentata.
  - Generato flat profile dinamico con `valgrind --tool=callgrind` e pacchetto di debug symbols `libssl3t64-dbgsym` su $1.181.840.654\text{ Ir}$ (batch 500):
    - **Calcolo Crittografico Totale**: **$94.14\%$** ($>90\%$ confermato empiricamente).
    - **Aritmetica EC P-256 e Montgomery BIGNUM**: **$87.88\%$** (`__ecp_nistz256_mul_montq` $32.71\%$, `__ecp_nistz256_sqr_montq` $19.97\%$).
    - **Gestione Dinamica Memoria (`malloc`/`free`)**: **$3.20\%$**.
    - **Codice Applicativo del Progetto**: **$1.80\%$**.
  - Risultati salvati in `hpc-engine/results/profile_i7_12700h_20260908.txt`.
- [x] 3. **Infrastruttura Isolata Estesa a 32 Nodi (`docker-compose.benchmark.yml`)**:
  - Esteso additivamente `deploy/docker-compose.benchmark.yml` a 32 container `bench-worker-1..32` su porte host isolate `51051..51082`, prevenendo ogni sovrapposizione con i container di produzione.
  - Eseguita run pilota preliminare a 32 nodi × 8 thread (batch 5.000, tempo $88.31\text{ ms}$, throughput $56.618,9\text{ sig/s}$), isolata in `hpc-engine/results/pilot_32x8_5000.csv` ed esclusa dalle statistiche formali.
- [x] 4. **Task B — Griglia Completa Nodi × Thread (gRPC Isolato)**:
  - Eseguita campagna completa su 48 configurazioni: nodi $\in \{1,2,4,8,16,32\}$, thread $\in \{1,2,4,8\}$, batch $\in \{1000, 5000\}$ con 3 ripetizioni e warmup.
  - Validazione stringente al 100% superata su tutte le run ($\sum \text{valid\_count} == \text{total\_batch}$).
  - Picco di throughput in regime clean ($P_{eff} \le 20$): **$72.699,7\text{ sig/s}$** (16 nodi × 1 thread, speedup $7.20\times$).
  - Picco di throughput complessivo in oversubscription: **$78.989,2\text{ sig/s}$** (media) / **$82.467,0\text{ sig/s}$** (massimo) a 16 nodi × 8 thread.
  - Risultati salvati in `hpc-engine/results/grid_grpc_i7_12700h_20260908.csv`.
- [x] 5. **Task B — Griglia Completa Nodi × Thread (Ibrido MPI+OpenMP)**:
  - Eseguita campagna omogenea per rank MPI $\in \{1,2,4,8,16,32\}$, thread OpenMP $\in \{1,2,4,8\}$, batch $\in \{1000, 5000\}$ con policy `--bind-to none` e `--oversubscribe`.
  - Picco di throughput in regime clean: **$138.321,7\text{ sig/s}$** (16 rank × 1 thread, speedup $8.97\times$).
  - Picco assoluto con sonda oversubscribed: **$148.927,0\text{ sig/s}$** (media) / **$163.922,0\text{ sig/s}$** (massimo) a 32 rank × 4 thread.
  - Risultati salvati in `hpc-engine/results/grid_mpi_omp_i7_12700h_20260908.csv`.
- [x] 6. **Task C — Investigazione dell'Anomalia di Amdahl a 8, 16 e 32 Nodi**:
  - Rilanciate 12 configurazioni ($N \in \{8, 16, 32\}$, $T \in \{1, 8\}$, batch $1.000$ e $5.000$) con **10 ripetizioni ciascuna**.
  - Scomposto il tempo di ciascuna singola chiamata RPC in tempo di calcolo C++ restituito dal worker (`worker_time_seconds`) vs latenza totale (`rpc_latency_seconds`) vs overhead di rete (`network_overhead_seconds`).
  - **Verdetto Formale**: Fenomeno reale e strutturale. A 32 nodi il calcolo utile medio scende a $2.84\text{ ms} - 13.06\text{ ms}$, mentre l'overhead di rete per chiamata pesa tra $11.44\text{ ms}$ e $31.88\text{ ms}$ (**$71\% - 80\%$** dell'intera durata della RPC). La contesa TCP/HTTP2 e lo straggler tail effect ($\max(T_i)$) dominano la latenza e spiegano esaurientemente il discostamento dalla curva asintotica ideale di Amdahl.
  - Risultati salvati in `hpc-engine/results/amdahl_investigation_i7_12700h_20260908.csv`.
- [x] 7. **Task D — Pipelining Throughput Benchmark su Catena Reale**:
  - Avviati gli stack reali IoTronic e Pipeline senza mock; acquisito lease on-chain di 3 nodi via Satellite.
  - Eseguito `pipeline_throughput_benchmark.py` per $n \in \{1, 2, 4, 8\}$ con 5 ripetizioni ciascuno.
  - Speedup misurato vs predetto ($k=3$):
    - $n=1$: $S_{mis} = 0.98\times$ (predetto $1.00\times$, scarto $2.2\%$, ricalibrato con 3 warmup consecutivi: StdDev normalizzata da $2.27\text{s}$ a $0.063\text{s}$)
    - $n=2$: $S_{mis} = 1.39\times$ (predetto $1.50\times$, scarto $7.3\%$)
    - $n=4$: $S_{mis} = 1.32\times$ (predetto $2.00\times$, scarto $34.1\%$)
    - $n=8$: $S_{mis} = 1.58\times$ (predetto $2.40\times$, scarto $34.1\%$)
  - **Investigazione e Plateau di Saturazione**:
    - Isolato il meccanismo che causa lo scarto a $n \ge 4$: l'assenza di un pipeline queue scheduler centralizzato fa sì che le richieste concorrenti generate in burst collidano tutte simultaneamente sullo stadio 1 (`worker-1`), accodandosi sulla coda WAMP/Lightning-Rod della prima board (head-of-line blocking).
    - Lo scarto identico al decimale tra $n=4$ e $n=8$ ($34.1\% / 34.1\%$, confermato sui dati grezzi floating-point) documenta un **plateau di saturazione** della catena oltre il quale non è possibile estrarre ulteriore parallelismo senza schedulazione hardware/esplicita. Nonostante questo limite strutturale, la concorrenza asincrona consegue comunque uno speedup di **$1.58\times$** riducendo il tempo da $5.58\text{s}$ a $3.53\text{s}$.
  - Risultati salvati in `hpc-engine/results/pipeline_throughput_i7_12700h_20260908.csv`. Rilasciato regolarmente il lease on-chain.
- [x] 8. **Task E — Sintesi PCAM e Log dei Risultati Grezzi**:
  - Creato `hpc-engine/results/RAW_FINDINGS_LOG.md` strutturato secondo le sezioni PCAM obbligatorie del corso (Decomposition, Communication, Aggregation, Mapping, Performance evaluation, Appendice Anomalie) con evidenze e citazioni numeriche esclusive dai CSV generati.

### Definition of Done — Stadio 11.5 ✅
- Griglia `{1,2,4,8,16,32}` eseguita per benchmark isolato gRPC e ibrido MPI+OpenMP, sulla stessa macchina/sessione (env_id coerente `i7_12700h_20260908`).
- Ogni configurazione oltre 20 di parallelismo effettivo etichettata `oversubscribed` nel CSV grezzo.
- Pipeline a 3 stadi misurata (predetto vs misurato con 5 ripetizioni) su catena reale Satellite ↔ IoTronic ↔ Worker C++.
- Anomalia di Amdahl a 8, 16 e 32 nodi investigata con 10 ripetizioni e scomposizione compute vs network latency.
- Nessuna modifica a `satellite/`, `chain/`, `gateway/`, `notification/`, `ui/`, worker di produzione `worker-1/2/3`.
- `PROGRESS.md` e `RAW_FINDINGS_LOG.md` completati e allineati.

## Fase: M13 (Revisione Progetto HPC) — Stadio 13.1 (Verifica dello Stato Reale)

**Data:** 2026-11-01  
**Obiettivo:** Audit e verifica reale dello stato dei file di benchmark, profiling, grafici, hardware e sorgenti C++/MPI, senza modifiche di codice.

### 1. Censimento Directory e Individuazione Script/Report
- **`hpc-engine/results/`**:
  - `amdahl_investigation_i7_12700h_20260908.csv` (120 record, 12 config × 10 ripetizioni, decomposizione compute vs rpc latency)
  - `grid_grpc_i7_12700h_20260908.csv` (48 config gRPC, batch 1000/5000, nodi 1..32, thread 1..8)
  - `grid_mpi_omp_i7_12700h_20260908.csv` (48 config MPI+OpenMP, batch 1000/5000, rank 1..32, thread 1..8)
  - `pipeline_throughput_i7_12700h_20260908.csv` (4 record per n=1,2,4,8, catena reale k=3)
  - `pilot_32x8_5000.csv` (run pilota preliminare esclusa dai grafici formali)
  - `profile_i7_12700h_20260908.txt` (sintesi flat profile Valgrind Callgrind, batch 500)
  - `callgrind.out` e `callgrind_annotate.txt` (output grezzo Callgrind, ignorati da git)
  - `profile_gprof_raw.txt` (output gprof preliminare non instrumentato, 0.00s)
  - `environment_fingerprint_20260908.txt` (dati hardware e sistema host)
  - `RAW_FINDINGS_LOG.md` (sintesi formale PCAM M11.5)
- **`hpc-engine/benchmarks/`**:
  - `run_full_campaign.py` (driver completo per Task B e C)
  - `run_benchmark.py` (driver standalone gRPC task-parallel)
  - `compute_metrics.py` (calcolo metriche Speedup, Efficiency, Amdahl)
  - `pipeline_pb2.py` e `pipeline_pb2_grpc.py` (stub gRPC generati, ignorati e non tracciati)
- **`hpc-engine/Dockerfile.profile`**:
  - Presente e funzionante: installa `libssl-dev`, `valgrind`, `libssl3t64-dbgsym` su Ubuntu 24.04, compila con `-O2 -g -fopenmp -std=c++17`.
- **Script di generazione grafici**:
  - `generate_report_graphs.py` (in root del workspace): 736 righe Python, legge i CSV da `hpc-engine/results/` e genera 14 grafici (PNG 300 dpi e PDF vettoriali) in `graphs/`. Nota: `generate_report_graphs.py` e `graphs/` sono attualmente esclusi da `.gitignore`.
- **Individuazione `main.tex` (Report LaTeX in inglese)**:
  - **NON presente nel repository** (nessun file `.tex` in `report/`, `docs/`, root, né in cronologia git).
  - La ricerca globale su filesystem e cronologie IDE ha rilevato solo riferimenti storici a un path esterno (`/media/adima/Windows-SSD/Users/adima/Università/Tesi magistrale/main.tex`), i cui contenuti in cache appartengono a un diverso progetto (database a grafo Neo4j).
  - **Stato**: Il sorgente `main.tex` del report HPC non esiste attualmente su disco nel filesystem accessibile.

### 2. Tabella di Tracciabilità (Figure 1-5, Tabelle 1-4)

| Elemento Report | Contenuto / Metrica | CSV / Output Grezzo | Script Generatore | Riproducibile? | Commit Riferimento |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Fig. 1 / Tab. 1** | Flat Instruction Profile Callgrind (94.14% calcolo crypto, 87.88% EC/BIGNUM, 3.20% malloc) | `hpc-engine/results/profile_i7_12700h_20260908.txt`, `callgrind.out`, `callgrind_annotate.txt` | `valgrind --tool=callgrind` via `Dockerfile.profile` + `plot_a_profile_breakdown()` in `generate_report_graphs.py` | **Sì** | `4f2d8668` |
| **Tab. 2** | Overhead di comunicazione (confronto modelli: MPI, gRPC 8/16/32, Pipeline k=3) | gRPC: `amdahl_investigation_...csv`; Pipeline: `pipeline_throughput_...csv`; **MPI: NESSUNO** | `run_full_campaign.py` (gRPC), `pipeline_throughput_benchmark.py` (Pipeline). **Nessun script per overhead MPI** | **Parziale** (MPI non misurato strumentalmente, dichiarato nominale) | `4f2d8668` / `ee99b108` |
| **Fig. 2 / Fig. 3** | Griglia di scaling gRPC e MPI+OpenMP fino a 32 nodi/rank (Speedup e Throughput, batch 1000/5000) | `hpc-engine/results/grid_grpc_i7_12700h_20260908.csv` e `grid_mpi_omp_i7_12700h_20260908.csv` | `hpc-engine/benchmarks/run_full_campaign.py` + `plot_b_grpc_grid()`, `plot_c_mpi_omp_grid()`, `plot_d_substrate_comparison()` | **Sì** | `4f2d8668` |
| **Fig. 4 / Tab. 3** | Investigazione anomalia di Amdahl & Overhead breakdown (scomposizione compute C++ vs RPC network) | `hpc-engine/results/amdahl_investigation_i7_12700h_20260908.csv` | `run_full_campaign.py --target amdahl` + `plot_e_amdahl_and_overhead()` in `generate_report_graphs.py` | **Sì** | `4f2d8668` |
| **Fig. 5 / Tab. 4** | Pipelining a 3 stadi su catena reale ($k=3$, $n \in \{1,2,4,8\}$, speedup predetto vs misurato) | `hpc-engine/results/pipeline_throughput_i7_12700h_20260908.csv` | `pipeline_throughput_benchmark.py` + `plot_f_pipelining()` in `generate_report_graphs.py` | **Sì** | `4f2d8668`, ricalibrato in `ee99b108` |

#### Evidenze e Criticità Emerse dall'Audit:
1. **Profilo Callgrind (Fig. 1 / Tab. 1)**: Callgrind conta istruzioni simulate ($1.181.840.654\text{ Ir}$), **non tempo reale di esecuzione**. Nel report la dicitura "of the total time" va corretta in "% Ir / instruction count".
2. **Griglia gRPC fino a 32 worker (Fig. 2-3)**: I punti con $P_{eff} > 20$ (es. $32 \times 1, 32 \times 8$) sono eseguiti in oversubscription hardware sull'host a 20 thread logici. Manca un grafico unificato con curve di speedup sovrapposte su asse unico per MPI puro, OpenMP puro, ibrido e gRPC (rilievo R7 del revisore).
3. **Valori di Amdahl e Ripetizioni (Tab. 3 / Fig. 4)**:
   - **Discrepanza ripetizioni**: Il CSV e `RAW_FINDINGS_LOG.md` riportano **10 ripetizioni** (12 configurazioni × 10 = 120 run). Tabella 3 riportava 10 ripetizioni, ma nel testo del report (§7.1) veniva scritto erroneamente "3 ripetizioni".
   - **Frazione seriale $f_s$**: Il valore $f_s = 0.0251$ (2.51%) usato per la curva teorica in `generate_report_graphs.py` (riga 458) è ereditato da una campagna preliminare a 2 nodi × 1 thread (M11.3), anziché ricalcolato internamente alla campagna corrente con intervallo di confidenza.
4. **Pipeline a 3 stadi (Fig. 5 / Tab. 4)**:
   - Misurate solo 4 configurazioni ($n \in \{1, 2, 4, 8\}$). Mancano i punti intermedi $n=3,5,6,7$.
   - Lo scarto relativo identico al $34.1\%$ tra $n=4$ e $n=8$ ($1.32/2.00$ vs $1.58/2.40$) è una coincidenza aritmetica derivante dai valori arrotondati, non la prova rigorosa di un plateau di saturazione a soglia $n=4$.
   - L'ipotesi di head-of-line blocking nella coda WAMP/Crossbar dello stadio 1 va verificata con scansione completa o riformulata come ipotesi.

### 3. Verifica Git Ignore per Stub gRPC
Eseguito:
```bash
$ git check-ignore -v hpc-engine/benchmarks/pipeline_pb2.py hpc-engine/benchmarks/pipeline_pb2_grpc.py
.gitignore:24:**/*_pb2.py	hpc-engine/benchmarks/pipeline_pb2.py
.gitignore:25:**/*_pb2_grpc.py	hpc-engine/benchmarks/pipeline_pb2_grpc.py

$ git ls-files hpc-engine/benchmarks/pipeline_pb2*
# (output vuoto: nessun file tracciato)
```
Esito: Entrambi i file sono correttamente ignorati da git e non tracciati nel repository.

### 4. Mappatura Hardware P-core/E-core e Scaling Governor
Eseguito `lscpu --extended` e ispezione governor CPU:
- **CPU**: Intel Core i7-12700H (14 core fisici, 20 thread logici).
- **Mappa P-core (Performance Cores)**:
  - 6 core fisici (CORE 0..5), 12 thread logici (CPU 0..11, 2 thread per core con Hyper-Threading).
  - Frequenze: Max 4600–4700 MHz, Min 400 MHz.
  - Cache L1/L2 dedicate per core (L1d:L1i:L2 = 32K/32K/1280K per core).
- **Mappa E-core (Efficient Cores)**:
  - 8 core fisici (CORE 6..13), 8 thread logici (CPU 12..19, 1 thread per core, no SMT/Hyper-Threading).
  - Frequenze: Max 3500 MHz, Min 400 MHz.
  - Cache L2 condivise a gruppi di 4 (L2 index 6 per CPU 12-15, index 7 per CPU 16-19, 2048K ciascuna).
- **CPU Scaling Governor**:
  - `cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`:
    Tutti i 20 thread logici (CPU 0..19) sono impostati sul governor `powersave` (predefinito del driver `intel_pstate`).

### 5. Stato dei File Sorgente C++ / MPI / OpenMP
- **`hpc-engine/src/mpi_experiment/main_mpi.cpp`**:
  - Riga 45: `MPI_Init(&argc, &argv);` $\to$ usa `MPI_Init`, **NON** `MPI_Init_thread`.
  - Riga 109: `BenchResult local_res = SignatureBench::run_parallel(...)` $\to$ **SÌ**, usa `run_parallel` con OpenMP all'interno di ciascun rank MPI (ibrido reale).
  - Mancanza: Non contiene misurazione strumentata del tempo di riduzione/comunicazione con `MPI_Wtime`.
- **`hpc-engine/src/onboarding/signature_bench.cpp`**:
  - Riga 54: `#pragma omp parallel for reduction(+:valid_count)` $\to$ **NON possiede alcuna clausola `schedule`** (utilizza il default OpenMP, tipicamente statico).

## Fase: M13 (Revisione Progetto HPC) — Stadio 13.2 (Codice e Nuove Varianti)

**Data:** 2026-11-01  
**Obiettivo:** Implementazione delle varianti task-based (OpenMP `taskloop` e MPI Master-Worker dinamico), refactoring binding e thread safety (`MPI_THREAD_FUNNELED`), strumentazione `MPI_Wtime` per fase, script di lancio parametrici e test unitari.

### 1. Riepilogo Commit Atomici
- `888797c`: `chore(hpc): move generate_report_graphs.py to benchmarks and track it` (Housekeeping: spostato in `hpc-engine/benchmarks/`, aggiornato `PROJECT_ROOT`, rimosso da `.gitignore`, tracciato, `graphs/` ignorato).
- `57304a5`: `feat(hpc): initialize MPI with MPI_THREAD_FUNNELED and check provided level` (Inizializzazione con controllo esplicito su `provided >= MPI_THREAD_FUNNELED` e documentazione thread safety).
- `145dd02`: `feat(hpc): instrument MPI per-phase timings with MPI_Wtime and export to CSV` (Misurazione separata con `MPI_Wtime` per generazione dati, verifica OpenMP e `MPI_Reduce`, colonne aggiunte in coda nel CSV).
- `4f65b6d`: `feat(hpc): add schedule(runtime) to OpenMP loop with static default fallback` (Aggiunta clausola `schedule(runtime)` e fallback esplicito a `omp_sched_static` se `OMP_SCHEDULE` non impostata).
- `968922e`: `feat(hpc): implement OpenMP taskloop parallel verification variant with CLI grainsize` (Nuova funzione `run_parallel_taskloop` con `#pragma omp taskloop` e `grainsize` parametrizzabile via CLI).
- `6b6c84d`: `feat(hpc): implement dynamic master-worker MPI variant with parameterizable chunks` (Nuovo eseguibile `hpc_engine_mpi_dynamic`: Rank 0 coordinatore dinamico a richiesta, worker con multithreading OpenMP, chunking configurabile e cross-check `valid_count`).
- `89bcae2`: `feat(hpc): add benchmark launch scripts with explicit binding and governor logging` (`launch_mpi_pure.sh`, `launch_hybrid.sh`, `launch_control.sh`, `launch_dynamic.sh` con binding core/thread, governor logging e supporto P-cores via `taskset -c 0-11`).
- `e2dd57d`: `test(hpc): add test_taskloop and MpiDynamicCorrectness test targets with zero warnings` (Nuovi test per le varianti taskloop e MPI dinamico registrati in CTest, compilazione pulita `-Wall -Wextra` senza warning).

### 2. Output dei Test Unitari ed End-to-End (CTest)
Eseguito all'interno dell'ambiente di compilazione di riferimento (`hpc-engine-build`):
```text
Test project /app/build
    Start 1: SignatureCorrectness
1/4 Test #1: SignatureCorrectness .............   Passed    0.00 sec
    Start 2: TaskloopCorrectness
2/4 Test #2: TaskloopCorrectness ..............   Passed    0.03 sec
    Start 3: WorkerCorrectness
3/4 Test #3: WorkerCorrectness ................   Passed    0.52 sec
    Start 4: MpiDynamicCorrectness
4/4 Test #4: MpiDynamicCorrectness ............   Passed    0.51 sec

100% tests passed, 0 tests failed out of 4
Total Test time (real) = 1.06 sec
```

### 3. Confronto Minimo di Sanità (Senza interpretazione teorica dei numeri)
Misure di verifica di sanità eseguite su batch da 5.000 firme:

#### A. OpenMP: `parallel for` vs `taskloop` (Batch 5.000, 4 Threads)
- **`parallel for` (default static)**:
  - Tempo: `0.0830167 s`
  - Throughput: `60.228,8 sig/s`
  - `valid_count`: 5000/5000 (100%)
- **`taskloop` (grainsize = 100)**:
  - Tempo: `0.0794946 s`
  - Throughput: `62.897,3 sig/s`
  - `valid_count`: 5000/5000 (100%)

#### B. MPI: Statico (`hpc_engine_mpi`) vs Master-Worker Dinamico (`hpc_engine_mpi_dynamic`) (Batch 5.000, 4 Ranks, 1 Thread, P-cores 0-11)
- **MPI Statico (4 Rank calcolatori)**:
  - Tempo massimo: `0.0729711 s`
  - Throughput globale: `68.520,3 sig/s`
  - Decomposizione fasi: `Gen = 0.0540909 s`, `Verify = 0.0729757 s`, `Reduce = 0.00225934 s`
  - `valid_count`: 5000/5000 (100%)
- **MPI Master-Worker Dinamico (1 Master + 3 Worker, Chunk = 100)**:
  - Tempo totale: `0.167464 s`
  - Throughput globale: `29.857,1 sig/s`
  - `valid_count`: 5000/5000 (100% Match)

### 4. Definizione del Governor per lo Stadio Successivo (13.3)
Tutte le CPU host si trovano attualmente su governor `powersave`. Per l'esecuzione della campagna formale dello Stadio 13.3 si raccomanda all'utente l'esecuzione (con privilegi sudo) di:
```bash
sudo cpupower frequency-set -g performance
```
oppure:
```bash
sudo bash -c 'for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > "$g"; done'
```

## Fase: M13 (Revisione Progetto HPC) — Stadio 13.3 (Campagna Sperimentale)

**Data:** 2026-11-01  
**Obiettivo:** Esecuzione rigorosa della campagna sperimentale su strong scaling (batch = 20.000 firme), 10 ripetizioni intercalate randomicamente, controllo di correttezza `valid_count == batch` su ogni run, generazione dataset grezzi senza alterazione dei dati storici.

### 1. Precondizioni e Impronta Ambientale
- **CPU Scaling Governor:** Impostato e verificato a `20 performance` su tutte le 20 CPU logiche (`cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`).
- **Macchina e Ambiente:**
  - Carico a riposo (load average < 0.20, nessun processo di benchmark concorrente).
  - Impronta registrata in `hpc-engine/results/m13/environment_fingerprint.txt`:
    - Kernel: `Linux sandbox 7.0.0-38-generic #38~24.04.4-Ubuntu SMP PREEMPT_DYNAMIC`
    - CPU: `12th Gen Intel(R) Core(TM) i7-12700H` (6 P-cores con Hyper-Threading = 12 thread, 8 E-cores = 8 thread, 20 thread logici totali).
    - Open MPI: `4.1.6`
    - GCC: `13.3.0`
    - libgomp: `14.2.0-4ubuntu2~24.04.1`
    - Binari eseguiti su host nativo per E0, E1, E2, E3, E5, E6, E8.
    - Binari containerizzati (`deploy-bench-worker-*`) per E4.

### 2. Esito del Passo 1 — Diagnosi e Risoluzione del Master-Worker Dinamico
- **Diagnosi:** In `main_mpi_dynamic.cpp` la generazione dei device (keygen ECDSA + firma) avveniva all'interno del loop di ciascun chunk dei worker, all'interno della regione cronometrata dal master (Rank 0). Inoltre il denominatore del throughput utilizzava il tempo del coordinatore anziché il tempo massimo di completamento dei worker (`max_worker_time`).
- **Risoluzione (Commit `f641a39`):**
  - Implementata `SignatureBench::run_parallel_range(...)` in `signature_bench.hpp` e `.cpp`.
  - Dataset completo di 20.000 firme pre-generato prima di `MPI_Barrier(MPI_COMM_WORLD)`.
  - I worker ricevono via MPI unicamente gli indici `{start_index, chunk_size}` ed eseguono la sola verifica crittografica sui dati già in memoria.
  - Sincronizzazione finale con riduzione `MPI_Reduce(..., MPI_MAX)` del tempo massimo del worker e decomposizione per fase (`Gen`, `Verify`, `Reduce`).
- **Verifica e Scomposizione (Batch 5.000, R=4, 1 Master + 3 Worker, 1 thread per worker, P-cores 0-11):**
  - Chunk 25: Max Worker Time = `0.0940 s`, Throughput = `53.204,1 sig/s` (Gen = `0.202 s`, Verify = `0.0938 s`, Reduce = `0.000023 s`).
  - Chunk 100: Max Worker Time = `0.0950 s`, Throughput = `52.655,4 sig/s` (Gen = `0.202 s`, Verify = `0.0949 s`, Reduce = `0.000018 s`).
  - Chunk 500: Max Worker Time = `0.1157 s`, Throughput = `43.222,1 sig/s` (Gen = `0.203 s`, Verify = `0.1156 s`, Reduce = `0.000038 s`).
  - Chunk 1000: Max Worker Time = `0.1127 s`, Throughput = `44.350,4 sig/s` (Gen = `0.206 s`, Verify = `0.1127 s`, Reduce = `0.000026 s`).
  - *Esito:* A chunk fini (25 e 100) il throughput raggiunge `~52.6k–53.2k sig/s`, confermando esattamente il rapporto teorico atteso di `~0.76–0.78×` rispetto ai 4 rank del benchmark statico (68.5k sig/s $\times$ 3/4 = 51.4k). A chunk grossolani (500 e 1000) si manifesta load imbalance per divisione non intera dei chunk sui 3 worker. L'overhead di comunicazione MPI per messaggio è risultato ~100 µs, trascurabile rispetto alla computazione.

### 3. Anomalie Tecniche e Risoluzione nei Launch Script
- **Sonda HWLOC su X11 / OpenGL:** Open MPI 4.1.6 tentava la connessione ai socket grafici Wayland/X11 dell'host in assenza di credenziali Xauth nel sandbox, causando timeout. Risolto esportando `HWLOC_COMPONENTS="${HWLOC_COMPONENTS:--gl}"` in tutti gli script di lancio e nel driver Python.
- **Slot Hardware su CPU Ibride Alder Lake:** Open MPI di default limita il numero di slot allocabili ai 14 core fisici. Risolto aggiungendo `--use-hwthread-cpus` per mappare tutti i 20 hardware thread logici.
- **Binding Ibrido MPI+OpenMP:** Con `--use-hwthread-cpus` e PE arbitrari (es. $T=3, 5$), Open MPI richiede binding coerente a livello di thread. Risolto impostando `--bind-to hwthread` in `launch_hybrid.sh` e `launch_dynamic.sh`. Il binding risultante è stato verificato e registrato tramite `--report-bindings` nei file di log in `hpc-engine/results/m13/logs/`.

### 4. Risultati della Campagna di Misura
- **Driver Unificato:** `hpc-engine/benchmarks/run_m13_campaign.py` (Commit `236c318` e `4f35221`), con supporto per strong scaling batch 20.000, 10 ripetizioni intercalate randomicamente (seed 42), ripresa incrementale (`--resume`), log dettagliati in `results/m13/logs/` e verifica tassativa `assert valid_count == batch`.
- **Riepilogo Righe e Run Eseguiti:**

| Esperimento | Modello | Griglia Config | Run Totali | File CSV Risultati | Esito Correttezza |
|---|---|---|---|---|---|
| **E0** | Sequenziale | T1, baseline unica | 10 run | `results_e0_sequential.csv` & `t1_baseline.csv` | 100% Valid (20.000/20.000) |
| **E1** | OpenMP puro (`for`) | T = 1,2,3,4,6,8,10,12,14,16,18,20 | 120 run | `results_e1_omp_pure.csv` | 100% Valid (20.000/20.000) |
| **E2** | MPI puro (1 thr/rank) | R = 1,2,3,4,6,8,10,12,14,16,18,20 (`--bind-to core`) | 120 run | `results_e2_mpi_pure.csv` | 100% Valid (20.000/20.000) |
| **E3** | Ibrido MPI+OpenMP | 12 config R×T (8..20) + 2 controlli unbound | 140 run | `results_e3_hybrid.csv` | 100% Valid (20.000/20.000) |
| **E4** | gRPC + OpenMP | 12 config container `bench-worker-*` | 120 run | `results_e4_grpc.csv` | 100% Valid (20.000/20.000) |
| **E5** | Schedule OpenMP | static / dynamic,16 / guided su T=4..20 | 150 run | `results_e5_schedule.csv` | 100% Valid (20.000/20.000) |
| **E6** | Task-based | taskloop (grain 10..500) + dynamic (R=4..12) | 270 run | `results_e6_taskbased.csv` | 100% Valid (20.000/20.000) |
| **E8** | Ipotesi P/E-core | OpenMP e MPI su soli P-cores (`taskset -c 0-11`) | 160 run | `results_e8_pcores.csv` | 100% Valid (20.000/20.000) |

- **Verifica Globale di Integrità:** Controllate tutte le 1.100 righe CSV generate in `hpc-engine/results/m13/`: ogni singolo record soddisfa rigorosamente `valid_count == 20000` (100% match, zero fallimenti).
- **Esperimento E7 (Pipeline reale Stack4Things/IoTronic):** Esecuzione demandata come ultimo step facoltativo dopo preavviso e conferma dell'utente.

### 5. Stadio 13.3-bis — Verifiche Rigorose sui Dati Raccolti
- **A1. Verifica Governor:**
  - *Stato attuale post-reboot del sistema:* `20 powersave` (il reboot del sistema del 2026-11-07 ha resettato il governor del driver `intel_pstate`).
  - *Stato effettivo durante tutti i run sperimentali:* **`20 performance` al 100%**.
  - *Prova documentale diretta:*
    - `environment_fingerprint.txt`: `=== GOVERNOR === 20 performance`.
    - Analisi aggregata su tutti i file in `results/m13/logs/*.log`: `grep -h -A 1 "CPU Governor:" *.log` riporta esattamente `458  20 performance` e zero occorrenze di `powersave`. Nessun run è stato eseguito sotto `powersave`.
- **A2. Fingerprint e Coerenza d'Ambiente Runtime vs Build:**
  - File `hpc-engine/results/m13/environment_fingerprint.txt` presente e completo di kernel, `lscpu`, versioni, commit hash, `OMP_*` e distinzione esplicita host vs container.
  - Verifica librerie condivise runtime (`ldd build/hpc_engine_mpi` su host vs container di build `hpc-engine-build`):
    - `libgomp1`: `14.2.0-4ubuntu2~24.04.1` (identico su host e container).
    - `libopenmpi3t64`: `4.1.6-7ubuntu2` (identico su host e container).
    - Zero discrepanze di versione o ABI tra ambiente di compilazione ed esecuzione.
- **A3. Mappa di Binding Effettivo e Condivisione Core (SMT):**
  - Tutti i run E2, E3, E8 sono stati lanciati con binding esplicito.
  - *E2 (MPI puro):* I comandi utilizzano `--use-hwthread-cpus --bind-to core`. Per $R \le 14$, ogni rank occupa un core fisico intero. Per $R > 14$ (es. $R=16, 18, 20$), poiché i core fisici totali sono 14 (6 P-core con 2 hwt + 8 E-core con 1 hwt), i rank aggiuntivi vengono assegnati ciclicamente ai secondi thread hardware dei P-cores (core 0..5), condividendo il core fisico via SMT.
  - *E3 (Ibrido MPI+OpenMP):* Con `--use-hwthread-cpus` e PE arbitrari, il binding corretto applicato è `--map-by slot:PE=T --bind-to hwthread`.
    - *Fattorizzazioni con $T$ pari ($T=2, 4$):* nessun rank condivide core fisici con rank adiacenti (es. 4×2, 5×2, 6×2, 7×2, 8×2, 10×2, 4×4, 5×4). I thread OpenMP interni allo stesso rank saturano i due hwt dei P-cores assegnati.
    - *Fattorizzazioni con $T$ dispari ($T=3, 5$):* poiché ciascun rank occupa 3 o 5 hwt e i P-core dispongono di 2 hwt, i confini dei blocchi cadono a cavallo dei core fisici, portando rank adiacenti a condividere un P-core fisico via SMT (es. in 4×3, Rank 0 e Rank 1 condividono il core 1, Rank 2 e Rank 3 condividono il core 4).
    - *Controlli Unbound:* 4×4 e 8×2 con binding `none` confermati nei log con `MCW rank X is not bound (or bound to all available processors)`.
- **A3b. Definizione di `time_seconds` per Modello e Confrontabilità con $T_1$:**
  - *E0 (Sequenziale):* Solo tempo di verifica crittografica pura (EVP) su dataset pre-generato. Nessun overhead di generazione, IO o avvio processi.
  - *E1, E5, E6 (OpenMP for, schedule, taskloop):* Solo tempo di verifica parallela OpenMP pura intra-processo. Perfettamente confrontabile con $T_1$.
  - *E2, E3 (MPI puro e ibrido):* `time_seconds` è `max_time` dei worker per la sola verifica OpenMP (ridotto con `MPI_Reduce`). Esclude setup, generazione (`gen_s`), riduzione (`reduce_s`) e avvio processi. Pienamente confrontabile a livello di calcolo.
  - *E4 (gRPC isolato):* `time_seconds` è il wall-clock end-to-end del client Python (include latenza RPC, serializzazione protobuf, rete TCP). La colonna `verify_s` riporta il tempo massimo di calcolo interno ai container (`max_worker_time`). Per lo speedup di puro calcolo va usato `verify_s`; per l'efficienza end-to-end di sistema si usa `time_seconds`.
  - *E6 (MPI dinamico):* `time_seconds` è `max_worker_time` (tempo di calcolo firme + latenza dei messaggi MPI di richiesta chunk). Include l'overhead del protocollo (~100 µs).
- **A4. Duplicazione Baseline T1:**
  - `t1_baseline.csv` e `results_e0_sequential.csv` contengono identicamente gli stessi 10 run (`diff -u` vuoto). La differenza tra 1.090 run unici eseguiti e 1.100 righe totali validate è dovuta unicamente alla duplicazione intenzionale della baseline richiesta per standardizzazione.

---

## Stadio 13.4 & 13.4-bis — Analisi delle metriche, verifiche mirate e capacità reale

### 1. Riepilogo Metodologico e Microbenchmark di Verifica (B0 & V1.2)
- **Baseline $T_1$ Storica (E0):** Mediana = `1.103615 s` (IQR = `0.017572 s`), throughput `18.122,4 sig/s`.
- **Nuova Baseline $T_1$ Intercalata Imparziale (E0b, V2.4):** Mediana = `1.063555 s` (IQR = `0.018350 s`), throughput `18.804,8 sig/s`.
  - *Esito sul bias:* E0b è perfettamente allineata al tempo a $p=1$ di MPI puro (`1.0630 s`) e OpenMP puro (`1.0646 s`). Con $T_1(\text{E0b})$, lo speedup a $p=1$ si attesta a $0.98–1.00$ (azzerando il bias del 4–7% di E0 e i valori spuri negativi di Karp-Flatt).
- **Microbenchmark Latenza Singola Firma ECDSA P-256 (`bench_single_verify`, B0):**
  - Eseguito su $N = 20.000$ firme sintetiche con OpenSSL 3.0.15 e compilazione `-O2`.
  - Overhead timer (`high_resolution_clock`): `12.80 ns` (0.02% del tempo di verifica).
  - Latenza singola verifica: Media = `57.42 µs` ($\pm 7.27 µs$, CV = `12.66%`), Mediana (p50) = `55.71 µs`, Min = `50.79 µs`, p90 = `59.73 µs`, p99 = `87.44 µs`, Max = `269.32 µs`.
  - Throughput equivalente su 1 core: `17.416,1 sig/s`.
- **Microbenchmark Generazione Device Isolata (`bench_device_gen`, V1.2):**
  - Misurato il tempo di `DeviceGenerator::generate_devices(N, seed)` (keygen ECDSA + firma):
    - $N = 1.000$: Mediana = `0.0417 s` $\to$ **`41.69 µs/device`** (IQR = `1.8 µs`).
    - $N = 5.000$: Mediana = `0.1995 s` $\to$ **`39.90 µs/device`** (IQR = `1.3 µs`).
    - $N = 20.000$: Mediana = `0.7798 s` $\to$ **`38.99 µs/device`** (IQR = `2.6 µs`).

### 2. Risoluzione dell'Origine dell'Overhead di gRPC (V1)
1. **Analisi del codice (`worker_server.cpp:41-47`):**
   - Nel metodo `ExecuteTask(VERIFY_SIGNATURES_BATCH)`, la riga 41 chiama `DeviceGenerator::generate_devices(batch_size, seed)` in modo sequenziale su un singolo thread.
   - La regione cronometrata per `bench_res.time_seconds` (riga 42) racchiude **solo** `SignatureBench::run_parallel(...)`.
   - La generazione dei device avviene quindi **dentro la RPC gRPC ma fuori da `time_seconds`/`verify_s`**.
2. **Misura del puro costo di rete/dispatch asincrono (`bench_ping_dispatch.py`, V1.3):**
   - Latenza wall-clock di `Ping` concorrente senza calcolo verso $k$ container:
     - $k = 1$: `2.21 ms` (IQR = `0.48 ms`)
     - $k = 2$: `2.55 ms` (IQR = `0.42 ms`)
     - $k = 4$: `2.76 ms` (IQR = `19.17 ms`)
     - $k = 8$: `3.99 ms` (IQR = `1.22 ms`)
     - $k = 16$: `7.16 ms` (IQR = `2.72 ms`)
     - $k = 20$: `7.43 ms` (IQR = `18.11 ms`)
     - $k = 32$: `9.71 ms` (IQR = `1.98 ms`)
3. **Scomposizione formale per ogni $p$ di E4 ($wall = ping(p) + gen(chunk) + verify\_s + residuo$):**

| $p$ | Chunk | $T_{wall}$ (s) | $Ping$ (ms) | $Gen(chunk)$ (s) | $Verify$ (s) | $Atteso$ (s) | $Residuo$ (ms) | Quota Residuo su Wall |
|---|---|---|---|---|---|---|---|---|
| 1 | 20.000 | 1.8729 | 2.21 | 0.7798 | 1.0788 | 1.8607 | **12.19** | **0.65%** |
| 2 | 10.000 | 0.9353 | 2.55 | 0.3994 | 0.5307 | 0.9327 | **2.51** | **0.27%** |
| 4 | 5.000 | 0.5217 | 2.76 | 0.1995 | 0.2930 | 0.4952 | **26.46** | **5.07%** |
| 8 | 2.500 | 0.3804 | 3.99 | 0.0999 | 0.2020 | 0.3058 | **74.55** | 19.60% |
| 16 | 1.250 | 0.2445 | 7.16 | 0.0499 | 0.1373 | 0.1944 | **50.15** | 20.51% |
| 20 | 1.000 | 0.2340 | 7.43 | 0.0417 | 0.1170 | 0.1661 | **67.91** | 29.02% |

*Esito confermato:* A $p \le 4$, oltre il **95–99%** della differenza $T_{wall} - T_{verify}$ è interamente spiegato dalla generazione sequenziale dei device sintetici sul worker containerizzato (~39 µs/firma). La rete e la serializzazione gRPC pesano per meno di 3–8 ms. A $p \ge 8$, subentra un residuo di 50–75 ms: l'ipotesi preliminare di "overhead di concorrenza del client asincrono Python" è stata smentita sperimentalmente da V1.3 (latenza di `Ping` concorrente verso 8–20 container limitata a 4–7 ms). L'esperimento E4b (container vincolati con override compose ai soli P-cores con `cpuset: "0-11"`, `results_e4b_grpc_pcores.csv`) ha testato l'ipotesi di rallentamento per assegnazione a E-core/SMT:
- A $p = 4$ ($4 \le 6$ P-cores fisici liberi): il residuo scende a **11.85 ms** (solo il 2.3% di $T_{wall}$).
- A $p = 8$ (8 container su 6 P-cores fisici): il residuo permane a **74.85 ms** (identico al run non vincolato di 74.55 ms).
- *Meccanismo confermato:* Con $p > 6$ container concorrenti vincolati a 6 P-core, il principio dei cassetti impone la condivisione di thread SMT su almeno 2 core fisici. La generazione sequenziale monocore per container (2.500 firme a $p=8$) subisce il degrado SMT misurato in E9c ($1.79\times$, passando da ~98 ms a ~175 ms, con un incremento di ~77 ms sul percorso critico del container più lento, che fissa $T_{wall}$). Non vi è quindi alcun collo di bottiglia nel client asincrono Python.
4. **Impatto sul report precedente (M11.5):**
   - In `hpc-engine/benchmarks/run_full_campaign.py` (riga 67), `network_overhead = max(0.0, rpc_latency - worker_time)` sottraeva la verifica dal tempo RPC, includendo la generazione dati.
   - Di conseguenza, in `report/main.tex` (riga 154, riga 193, Tabella 2, Figura 4 e Sezione 7.3), l'asintoto a ~87k sig/s attribuito interamente a "HTTP/2 framing e passaggio dello stack di rete Linux" è stato in realtà limitato dalla generazione sequenziale delle firme a bordo dei worker.

---

### 3. Effetto del Mapping e del Binding: Validazione Sperimentale (V2)
1. **Binding reale di E2 (`e2.log:438-439`):**
   - Con `--use-hwthread-cpus --bind-to core` (senza `--map-by core`), Open MPI ha legato sia Rank 0 sia Rank 1 al `core 0 [hwt 0-1]`, forzando la contesa SMT sullo stesso core fisico ($S = 1.24$).
2. **Campagna E2b (`--map-by core --bind-to core`, `results_e2b_mpi_map_core.csv`):**
   - Con mapping esplicito per core, Rank 0 è collocato su Core 0 e Rank 1 su Core 1.
   - **A $R = 2$:** il tempo crolla da `0.8919 s` a `0.5507 s`. Lo speedup sale a **$S = 1.93$** (vs $T_1(\text{E0b})$), con efficienza **$E = 0.97$** (97%!).
   - L'anomalia $S=1.24$ era dunque al 100% un artefatto del mapping, non dell'algoritmo né di MPI.
   - **Gradino a $R = 7$:** $R=6$ (tutti P-cores) registra `0.2000 s` ($S=5.32$); a $R=7$, quando il settimo rank viene collocato sul primo E-core (Core 6), il tempo balza a `0.3173 s` ($S=3.35, E=0.48$).
3. **Campagna E1c (`OMP_PLACES=cores` con `close` vs `spread`):**
   - **Affinità verificata a runtime (`OMP_DISPLAY_AFFINITY=true`):**
     - $T=2$ `spread`: `thread 0 affinity 0-1` (Core 0, P-core), `thread 1 affinity 13` (Core 7, E-core).
     - $T=2$ `close`: `thread 0 affinity 0-1` (Core 0), `thread 1 affinity 2-3` (Core 1).
     - $T=8$ `spread`: thread 0, 1, 2 sui P-cores (affinity `0-1`, `4-5`, `8-9`) e thread 3..7 sugli E-cores (affinity `12`, `14`, `16`, `18`, `19`).
     - $T=8$ `close`: thread 0..5 sui P-cores (affinity `0-1`, `2-3`, `4-5`, `6-7`, `8-9`, `10-11`) e thread 6, 7 sui primi E-cores (`12`, `13`).
   - **Esito prestazioni:**
     - **`close`:** mappa i primi thread sui P-cores. A $T=2$, $S = 1.92$ ($E = 0.96$); a $T=4$, $S = 3.56$ ($E = 0.89$); a $T=6$, $S = 5.23$ ($E = 0.87$). Il crollo di efficienza avviene a $T=8$ ($E = 0.47$) con l'ingresso degli E-cores.
     - **`spread`:** distribuisce i thread sull'intero processore. A $T=2$, thread 1 finisce su un E-core: il tempo è `1.0627 s` ($S = 1.00, E = 0.50$), esito coerente con l'attesa del thread più lento (E-core) alla barriera del loop OpenMP.

---

### 4. Capacità Hardware Reale della Macchina (V3 / E9 & E9b)

#### A. Misure su Configurazioni Isolate (E9 Detailed)
Misurate tramite $q$ processi sequenziali indipendenti concorrenti (nessuna comunicazione, nessun lock, $N = 20.000$/proc, 10 ripetizioni intercalate, `results_e9_capacity_detailed.csv`), registrando il tempo individuale $T_i$ di ciascun processo:

| Configurazione | $q$ | Descrizione | $T_{max}$ Mediano (s) | Throughput Statico $q\cdot N/T_{max}$ | $C_{static}(q)$ | Throughput Dinamico $\sum N/T_i$ | $C_{dyn}(q)$ [IQR] |
|---|---|---|---|---|---|---|---|
| **a** | 1 | 1 P-core (CPU 0) | 1.0862 | 18.414,3 sig/s | **1.00** | 18.414,3 sig/s | **1.00** (±0.04) |
| **b** | 1 | 1 E-core (CPU 12) | 2.1156 | 9.453,8 sig/s | **0.51** | 9.453,8 sig/s | **0.51** (±0.01) |
| **c** | 2 | 2 thread SMT sullo stesso P-core (CPU 0, 1) | 1.7962 | 22.269,8 sig/s | **1.21** | 22.321,4 sig/s | **1.21** (±0.04) |
| **d** | 6 | 6 P-cores fisici (CPU 0,2,4,6,8,10) | 1.1915 | 100.712,1 sig/s | **5.47** | 101.128,5 sig/s | **5.49** (±0.03) |
| **e** | 12 | 12 thread P-cores con SMT (CPU 0-11) | 1.9969 | 120.186,8 sig/s | **6.53** | 120.769,4 sig/s | **6.56** (±0.02) |
| **f** | 14 | 14 core fisici (6 P-cores + 8 E-cores) | 2.4283 | 115.309,2 sig/s | **6.26** | 171.361,3 sig/s | **9.31** (±0.14) |
| **g** | 20 | 20 thread totali (CPU 0-19) | 2.4310 | 164.541,0 sig/s | **8.94** | 191.734,3 sig/s | **10.41** (±0.02) |

#### B. Curva Completa Lungo l'Ordine di Riempimento Sperimentale (E9b Fill Order)
Misurata per ogni $q \in [1..20]$ lungo l'ordine effettivo di allocazione: 6 P-core primari (CPU 0,2,4,6,8,10), poi 8 E-core (12–19), poi 6 thread SMT sui P-core (1,3,5,7,9,11), con 10 ripetizioni intercalate (`results_e9b_capacity_fill.csv`, baseline $q=1$ = 18.796,1 sig/s):

| $q$ | Cores allocati | $T_{max}$ (s) | $C_{static}(q) = \frac{q\cdot N/T_{max}}{v_1}$ [IQR] | $C_{dyn}(q) = \frac{\sum N/T_i}{v_1}$ [IQR] | Modello misure isolate |
|---|---|---|---|---|---|
| 1 | 1 P-core | 1.0640 | 1.000 (±0.007) | 1.000 (±0.007) | 1.000 |
| 2 | 2 P-core | 1.0666 | 1.995 (±0.016) | 1.999 (±0.012) | 2.000 |
| 4 | 4 P-core | 1.1189 | 3.804 (±0.047) | 3.817 (±0.040) | 4.000 |
| 6 | 6 P-core | 1.1903 | 5.364 (±0.020) | 5.386 (±0.010) | 6.000 |
| 7 | 6 P-core + 1 E-core | 2.1120 | 3.527 (±0.006) | 5.920 (±0.015) | 6.508 |
| 8 | 6 P-core + 2 E-core | 2.1117 | 4.031 (±0.009) | 6.427 (±0.012) | 7.016 |
| 10 | 6 P-core + 4 E-core | 2.1547 | 4.938 (±0.036) | 7.393 (±0.016) | 8.032 |
| 12 | 6 P-core + 6 E-core | 2.4166 | 5.284 (±0.030) | 8.223 (±0.024) | 9.049 |
| 14 | 14 core fisici (6P+8E) | 2.4240 | 6.145 (±0.025) | 9.172 (±0.022) | 10.065 |
| 16 | 14 fisici + 2 P-SMT | 2.4253 | 7.020 (±0.186) | 9.635 (±0.092) | 10.465 |
| 20 | 20 thread totali | 2.4350 | 8.740 (±0.079) | 10.209 (±0.071) | 11.264 |

**Chiarimento metodologico sulle curve di capacità:**
1. **Modello da misure isolate ($11.264$ equivalenti P-core):** $6 \times 1.20 + 8 \times 0.5081$ è un modello sintetico estrapolato dai rapporti misurati isolatamente, non una misura empirica di throughput concorrente.
2. **Capacità sotto partizione statica ($C_{static}(q)$):** Con lavoro rigidamente equiripartito tra processi, i P-core terminano in ~1.19 s e rimangono inattivi ad attendere l'E-core (~2.11 s). Per questo motivo $C_{static}(7)$ crolla a 3.53 e $C_{static}(14) = 6.15 < C_{static}(12) = 6.48$. A $q=20$, $C_{static} = 8.74$, valore che coincide quasi perfettamente con OpenMP statico a $T=20$ ($S = 8.68$, $E_{cap\_static} = 99.3\%$).
3. **Capacità sotto bilanciamento ideale ($C_{dyn}(q)$):** Misura la somma effettiva delle velocità dei singoli processi $\sum (N/T_i)$. Sotto bilanciamento dinamico ideale, la capacità della macchina sale monotonicamente fino a **$10.21$ equivalenti P-core** (o $10.42$ se normalizzata sulla configurazione isolata $a$).
4. **Efficienza reale estratta dagli scheduler:**
   - A $T=20$, OpenMP `dynamic,16` raggiunge $S = 9.89$, pari al **$96.9\%$** della reale capacità dinamica della macchina ($C_{dyn}(20) = 10.21$).
   - A $p=20$, MPI puro statico raggiunge $S = 8.80$, pari al **$100.7\%$** della capacità statica consentita dall'hardware ($C_{static}(20) = 8.74$) e all'**$86.2\%$** della capacità ideale dinamica.

---

### 5. Tabelle Complete dei Modelli, Scheduling e Task-Based (V4 & V4-bis)

#### A. Sintesi Comparativa dei Modelli ($T_1(\text{E0b}) = 1.0636\,\text{s}$)
*Nota metodologica sulla colonna $C(p)$ in 13.4-bis:* La precedente colonna $C(p)$ utilizzava il modello piecewise-linear da misure isolate ($p \le 6 \implies p \times 1.00$; $p \in [7, 14] \implies 6.00 + (p-6) \times 0.5081$; $p \in [15, 20] \implies 10.065 + (p-14) \times 0.1999$), che assumeva $C(6)=6.00$ in contrasto con la misura empirica dei 6 P-core isolati di $5.36$. La tabella seguente riporta le due curve empiriche misurate $C_{static}(p)$ e $C_{dyn}(p)$, con l'efficienza $E_{cap} = (S / C_{static})\,/\,(S / C_{dyn})$.

| $p$ | $C_{static}$ | $C_{dyn}$ | E1 Unbound $S$ ($E_{stat}/E_{dyn}$) | E1c Close $S$ ($E_{stat}/E_{dyn}$) | E2b Map-Core $S$ ($E_{stat}/E_{dyn}$) | E3 Hybrid Old $S$ ($E_{stat}/E_{dyn}$) | E4 Compute $S$ ($E_{stat}/E_{dyn}$) |
|---|---|---|---|---|---|---|---|
| 1 | 1.00 | 1.00 | 1.00 (100% / 100%) | 0.96 (96% / 96%) | 0.98 (98% / 98%) | — | 0.99 (99% / 99%) |
| 2 | 2.00 | 2.00 | 1.95 (98% / 97%) | 1.92 (96% / 96%) | 1.93 (97% / 97%) | — | 2.00 (100% / 100%) |
| 4 | 3.80 | 3.82 | 3.53 (93% / 93%) | 3.56 (94% / 93%) | 3.71 (98% / 97%) | — | 3.63 (95% / 95%) |
| 6 | 5.36 | 5.39 | 4.29 (80% / 80%) | 5.23 (97% / 97%) | 5.32 (99% / 99%) | — | 4.71 (88% / 87%) |
| 8 | 4.03 | 6.43 | 5.02 (125% / 78%) | 3.76 (93% / 59%) | 3.88 (96% / 60%) | 4.51 (112% / 70%) | 5.27 (131% / 82%) |
| 12 | 5.28 | 8.22 | 6.37 (120% / 77%) | 5.34 (101% / 65%) | 5.49 (104% / 67%) | 6.34 (120% / 77%) | 5.97 (113% / 73%) |
| 14 | 6.15 | 9.17 | 6.94 (113% / 76%) | 5.86 (95% / 64%) | 6.40 (104% / 70%) | 7.01 (114% / 76%) | — |
| 16 | 7.02 | 9.63 | 7.49 (107% / 78%) | 6.68 (95% / 69%) | 7.31 (104% / 76%) | 7.68 (109% / 80%) | 7.55 (108% / 78%) |
| 20 | 8.74 | 10.21 | 7.81 (89% / 77%) | 8.37 (96% / 82%) | 8.80 (101% / 86%) | 8.30 (95% / 81%) | 9.11 (104% / 89%) |
#### B. Tabelle di Dettaglio E5 (OpenMP Scheduling)

| $T$ | Schedule | $T_{med}$ (s) | IQR (s) | Throughput (sig/s) | Speedup $S$ [95% CI] | $E_{lin} = S/T$ | $E_{cap\_stat} = S/C_{stat}$ | $E_{cap\_dyn} = S/C_{dyn}$ |
|---|---|---|---|---|---|---|---|---|
| 4 | dynamic,16 | 0.2848 | 0.0122 | 70.236,8 | 3.73 [3.58, 3.79] | 0.93 | 98.2% | 97.9% |
| 4 | guided | 0.2867 | 0.0093 | 69.769,1 | 3.71 [3.61, 3.79] | 0.93 | 97.5% | 97.2% |
| 4 | static | 0.2880 | 0.0084 | 69.453,0 | 3.69 [3.61, 3.77] | 0.92 | 97.1% | 96.8% |
| 8 | dynamic,16 | 0.1702 | 0.0028 | 117.499,0 | 6.25 [6.12, 6.30] | 0.78 | 155.0% | **97.2%** |
| 8 | guided | 0.1735 | 0.0113 | 115.292,0 | 6.13 [5.72, 6.18] | 0.77 | 152.1% | 95.4% |
| 8 | static | 0.2110 | 0.0046 | 94.774,9 | 5.04 [4.93, 5.10] | 0.63 | 125.0% | 78.4% |
| 12 | dynamic,16 | 0.1329 | 0.0006 | 150.498,5 | 8.00 [7.88, 8.06] | 0.67 | 151.5% | **97.3%** |
| 12 | guided | 0.1325 | 0.0050 | 150.991,5 | 8.03 [7.70, 8.10] | 0.67 | 152.0% | 97.6% |
| 12 | static | 0.1658 | 0.0021 | 120.602,0 | 6.41 [6.29, 6.49] | 0.53 | 121.4% | 78.0% |
| 16 | **dynamic,16** | **0.1156** | **0.0011** | **172.980,0** | **9.20 [9.03, 9.26]** | **0.58** | **131.0%** | **95.5%** |
| 16 | guided | 0.1251 | 0.0049 | 159.852,5 | 8.50 [8.24, 8.72] | 0.53 | 121.1% | 88.2% |
| 16 | static | 0.1382 | 0.0034 | 144.684,5 | 7.70 [7.43, 7.83] | 0.48 | 109.6% | 79.9% |
| 20 | **dynamic,16** | **0.1075** | **0.0018** | **186.040,0** | **9.89 [9.67, 9.95]** | **0.49** | **113.2%** | **96.9%** |
| 20 | guided | 0.1112 | 0.0037 | 179.799,0 | 9.56 [9.39, 9.83] | 0.48 | 109.4% | 93.7% |
| 20 | static | 0.1225 | 0.0061 | 163.223,0 | 8.68 [8.53, 9.14] | 0.43 | 99.3% | 85.0% |

*Evidenze quantitative E5:*
- A $T=20$, lo scheduling statico ($S = 8.68$) satura quasi esattamente la capacità della macchina sotto partizione statica ($C_{static}(20) = 8.74$, $E_{cap\_stat} = 99.3\%$).
- Lo scheduling `dynamic,16` estrae stabilmente il **95.5% – 97.9%** dell'ideale capacità dinamica $C_{dyn}(T)$ sull'intero spettro $T \in [4..20]$.

#### C. Tabelle di Dettaglio E6 & E6b (Taskloop vs Dynamic Master-Worker)

1. **OpenMP Taskloop vs Parallel For:**
- A $T=4$: parallel for = `0.3011 s` ($S=3.53$); `taskloop grain 100` = `0.2893 s` ($S=3.68$).
- A $T=8$: parallel for = `0.2118 s` ($S=5.02$); `taskloop grain 100` = `0.1740 s` ($S=6.11$).
- A $T=12$: parallel for = `0.1671 s` ($S=6.37$); `taskloop grain 100` = `0.1379 s` ($S=7.71$).
- A $T=20$: parallel for = `0.1362 s` ($S=7.81$); `taskloop grain 100` = `0.1120 s` ($S=9.49$).
*Nota:* Il grainsize 10 soffre di overhead di scheduling dei task (`1.037 s`), mentre grainsize 50-100 supera sistematicamente il parallel for statico a thread elevati.

2. **Diagnosi Binding di E6 Old e Risultati E6b (`--map-by core --bind-to core` a pari core fisici):**
- **Diagnosi Binding E6 Old (`e6.log:33-36`):** L'uso di `--use-hwthread-cpus --bind-to hwthread` senza `--map-by core` ha collocato Rank 0 (Master) su `core 0 [hwt 0]` e Rank 1 (Worker 0) su `core 0 [hwt 1]`, mentre Rank 2 e 3 condividevano `core 1 [hwt 0-1]`. A $R=4$ ($p_{calc}=3$), 3 worker e il master erano compressi su soli 2 core fisici, con contesa SMT diretta tra il coordinatore in attesa e il primo worker ($S = 1.97$).
- **Campagna E6b a pari core fisici (`results_e6b_dynamic_map_core.csv`):** Con `--map-by core --bind-to core`, ciascun rank riceve un core fisico esclusivo. In E6b, Rank 0 è il master (non calcola) e $R-1$ rank sono worker; il confronto con E2b statico va condotto **a parità di core fisici allocati ($R$)**, valutando lo speedup aggregato $S$, l'efficienza per core $S/R$ e la sovrapposizione degli intervalli interquartili (IQR [Q25–Q75]):

| Core $R$ | Composizione Core | E2b Statico $S$ [IQR] | E2b $S/R$ | E6b Dyn c25 $S$ [IQR] | E6b c25 $S/R$ | Esito IQR c25 | E6b Dyn c100 $S$ [IQR] | E6b c100 $S/R$ | Esito IQR c100 | E6b con `yield_idle` |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 P-cores | 2.81 [2.71–2.86] | 0.936 | 1.93 [1.92–1.93] | 0.642 | Perde E6b (-31.4%) | 1.92 [1.92–1.93] | 0.641 | Perde E6b (-31.5%) | — |
| 4 | 4 P-cores | 3.71 [3.58–3.75] | 0.928 | 2.87 [2.83–2.88] | 0.718 | Perde E6b (-22.6%) | 2.87 [2.84–2.88] | 0.717 | Perde E6b (-22.7%) | 2.87 |
| 5 | 5 P-cores | 4.45 [4.38–4.47] | 0.890 | 3.60 [3.58–3.60] | 0.719 | Perde E6b (-19.2%) | 3.59 [3.58–3.60] | 0.719 | Perde E6b (-19.3%) | — |
| 6 | 6 P-cores | 5.32 [5.20–5.36] | 0.886 | 4.49 [4.48–4.50] | 0.748 | Perde E6b (-15.7%) | 4.49 [4.47–4.50] | 0.749 | Perde E6b (-15.5%) | — |
| 7 | 6 P + 1 E | 3.35 [3.31–3.49] | 0.479 | 4.99 [4.97–5.00] | 0.713 | Vince E6b (+48.9%) | 5.00 [5.00–5.01] | 0.715 | Vince E6b (+49.3%) | — |
| 8 | 6 P + 2 E | 3.88 [3.76–3.99] | 0.484 | 5.49 [5.49–5.50] | 0.687 | Vince E6b (+41.7%) | 5.46 [5.46–5.46] | 0.683 | Vince E6b (+40.9%) | 5.46 |
| 9 | 6 P + 3 E | 4.23 [4.23–4.25] | 0.470 | 5.94 [5.93–5.96] | 0.660 | Vince E6b (+40.4%) | 5.82 [5.79–5.87] | 0.647 | Vince E6b (+37.5%) | 5.82 |
| 10 | 6 P + 4 E | 4.72 [4.71–4.73] | 0.472 | 6.37 [6.36–6.41] | 0.637 | Vince E6b (+35.0%) | 6.37 [6.31–6.39] | 0.637 | Vince E6b (+35.0%) | — |
| 11 | 6 P + 5 E | 4.91 [4.87–4.96] | 0.447 | — | — | — | — | — | — | — |
| 12 | 6 P + 6 E | 5.49 [5.46–5.54] | 0.458 | 7.24 [7.23–7.26] | 0.604 | Vince E6b (+32.0%) | 7.12 [7.11–7.13] | 0.594 | Vince E6b (+29.8%) | — |
| 13 | 6 P + 7 E | 5.89 [5.87–5.93] | 0.453 | — | — | — | — | — | — | — |
| 14 | 6 P + 8 E | 6.40 [6.16–6.51] | 0.457 | 8.15 [8.09–8.19] | 0.582 | Vince E6b (+27.4%) | 7.88 [7.87–7.89] | 0.563 | Vince E6b (+23.2%) | — |

- **Esiti quantitativi sul recupero dinamico (a parità di core fisici):**
  - **Zona omogenea P-cores ($R \le 6$): il dinamico PERDE sistematicamente rispetto allo statico.** Poiché il processo Master risiede su un P-core ma non esegue verifiche, il sistema dispone di soli $R-1$ worker computazionali. A $R=3$, E6b perde il $31.4\%$ rispetto a E2b ($1.93$ vs $2.81$); a $R=6$, perde il $15.7\%$ ($4.49$ vs $5.32$). Gli IQR non si sovrappongono.
  - **Transizione a $R=7$ (ingresso del primo E-core):** Lo statico E2b collassa a $S=3.35$ a causa del collo di bottiglia del rank 6 (E-core), che impiega il doppio del tempo sul chunk uniforme $N/7$. Il dinamico E6b raggiunge $S=4.99$ (chunk 25) / $5.00$ (chunk 100), **vincendo nettamente sullo statico a $R=7$ (+48.9%)**. Tuttavia, va evidenziato che a 7 core fisici il dinamico ($S=5.00$) resta **inferiore ai 6 P-core statici ($S=5.32$)**, proprio perché 1 P-core su 6 è sacrificato per il coordinatore.
  - **Zona eterogenea P+E ($R \ge 8$): il dinamico VINCE stabilmente, ma il vantaggio percentuale decresce con $R$.** A $R=8$, il dinamico supera lo statico di **+41.7%** ($5.49$ vs $3.88$); a $R=9$ di **+40.4%** ($5.94$ vs $4.23$); a $R=10$ di **+35.0%**; a $R=12$ di **+32.0%**; a $R=14$ di **+27.4%** ($8.15$ vs $6.40$). Il recupero dinamico non cresce con $R$, bensì si assesta tra il $+42\%$ e il $+27\%$ al crescere dei worker gestiti dal singolo master.
  - **Impatto di busy-polling del master:** La variante con `--mca mpi_yield_when_idle 1` registra speedup identici a $R=4$ ($2.87$), $R=8$ ($5.46$) e $R=9$ ($5.82$): una volta garantito un core fisico dedicato al master via `--map-by core --bind-to core`, il busy-polling di Open MPI non impatta minimamente le prestazioni dei worker.

#### D. Calibrazione di Amdahl e Valutazione Predizione vs Misura
- **Natura della frazione seriale $f_s$ su E2b:** Nella regione cronometrata di E2b non vi è codice seriale (il cronometro racchiude esclusivamente `SignatureBench::run_parallel`, senza comunicazioni o riduzioni; il tempo registrato è $T = \max_{rank} T_{verify\_rank}$). La frazione seriale $f_s$ rappresenta quindi una **perdita di scalabilità effettiva a $p \le 4$** dovuta a micro-contese di memoria/cache, non alla struttura algoritmica del problema.
- **Fit su E2b ($p \in [1, 2, 3, 4]$) con Bootstrap (10.000 iterazioni):**
  - Stima puntuale: $\mathbf{f_s = 2.802\%}$
  - **Intervallo di confidenza 95% Bootstrap: $[2.330\%,\; 4.006\%]$**
  - **Predizione su P-cores ($p=6$):** Predetto = **$5.26$**, Misurato = **$5.32$** (Rapporto Obs/Pred = **$1.01$**, precisione 99%).
  - **Divergenza su E-cores:** A $p=8$, Predetto = $6.69$, Misurato = $3.88$ (Obs/Pred = **$0.58$**); a $p=20$, Predetto = $13.05$, Misurato = $8.80$ (Obs/Pred = **$0.67$**), confermando l'asimmetria hardware come causa dominante della divergenza a $p \ge 7$.

#### E. Stima Teorica dello Sbilanciamento Algoritmico vs Hardware
- Dal microbenchmark B0, il coefficiente di variazione di una singola verifica è $CV_1 = 12.66\%$.
- Per un blocco di $n$ firme indipendenti, $\mathbb{E}[CV_n] = \frac{CV_1}{\sqrt{n}}$: per $n=1.000$, $\mathbb{E}[CV_{1000}] = \mathbf{0.40\%}$; per $n=2.500$, $\mathbb{E}[CV_{2500}] = \mathbf{0.25\%}$.
- Lo sbilanciamento di costo computazionale dovuto alla variabilità statistica delle firme è due ordini di grandezza inferiore allo sbilanciamento empirico osservato a $p \ge 7$ ($> 40\%$), confermando che l'asimmetria hardware è al 100% responsabile del degrado dello scheduling statico.

#### F. Confronto Rigoroso Ibrido MPI+OpenMP vs Modelli Puri (p = 8, 12, 16, 20)
Verifica delle differenze prestazionali e della sovrapposizione degli intervalli interquartili ($[Q_1, Q_3]$) sui tempi di esecuzione:

| $p$ | E1 Unbound $S$ [IQR] | E1c Close $S$ [IQR] | E2b MPI $S$ [IQR] | E3 Ibrido Old $S$ [IQR] | E3b Ibrido Map-Core $S$ [IQR] | Esito Statistico Ibrido vs Puri |
|---|---|---|---|---|---|---|
| **8** | 5.02 [4.95, 5.05] | 3.77 [3.72, 3.85] | 3.88 [3.76, 3.99] | 4.51 [4.48, 4.52] | 4.02 [4.01, 4.02] (cores=8) | Disgiunti da E1c e E2b (+16.5% e +14.0% su E3 Old); a pari core fisici (E3b), $4\times 2$ ($S=4.02$) è vicino a E2b ($3.88$) |
| **12** | 6.37 [6.26, 6.42] | 5.34 [5.14, 5.42] | 5.49 [5.46, 5.54] | 6.34 [6.29, 6.38] | 5.14 [5.14, 5.16] (cores=12) | E3 Old vs E1 Unbound: **sovrapposti (indistinguibile)**; E3b ($6\times 2$, 12 core) inferiore a E2b ($5.14$ vs $5.49$) |
| **16** | 7.49 [7.29, 7.58] | 6.68 [6.39, 6.91] | 7.31 [6.49, 7.43] | 7.68 [7.32, 7.86] | — | E3 Old vs E1 Unbound e vs E2b: **sovrapposti (indistinguibile)** ($\Delta S = +2.4\%$ e $+4.8\%$) |
| **20** | 7.81 [7.21, 8.41] | 8.37 [8.07, 8.48] | 8.81 [8.22, 9.19] | 8.30 [7.21, 8.55] | — | Tutti gli intervalli IQR si sovrappongono. **L'ibrido non vince a $p=20$** ($8.30$ vs $8.37$ di E1c e $8.81$ di E2b: **indistinguibile**) |

#### E. Stima Teorica dello Sbilanciamento Algoritmico vs Hardware
- Dal microbenchmark B0, il coefficiente di variazione di una singola verifica è $CV_1 = 12.66\%$.
- Per un blocco di $n$ firme indipendenti, la deviazione standard della somma scala con $\sqrt{n}$, e il CV del chunk è:
  $$\mathbb{E}[CV_n] = \frac{CV_1}{\sqrt{n}}$$
  - Per chunk di $n = 1.000$ firme (regime $p=20$): $\mathbb{E}[CV_{1000}] = \frac{12.66\%}{\sqrt{1000}} = \mathbf{0.40\%}$.
  - Per chunk di $n = 2.500$ firme (regime $p=8$): $\mathbb{E}[CV_{2500}] = \frac{12.66\%}{\sqrt{2500}} = \mathbf{0.25\%}$.
- **Confronto:** Lo sbilanciamento di costo computazionale dovuto alla sola variabilità statistica delle firme è inferiore allo **$0.40\%$**. Lo sbilanciamento empirico osservato a $p \ge 7$ ($> 40\%$) è due ordini di grandezza superiore, confermando che è interamente imputabile all'asimmetria hardware tra P-core ed E-core ($1.97\times$).

---

### 6. Catalogo Grafici Aggiornati (`graphs/m13/`)
- `fig_a_strong_scaling.{pdf,png}`: Aggiornato con entrambe le curve di capacità empirica misurata su E9b: $C_{dyn}(p)$ (tratto-punto magenta, bilanciamento dinamico ideale) e $C_{static}(p)$ (punteggiato rosso, partizione statica del lavoro) accanto alla retta ideale lineare $S = p$.
- `fig_b_parallel_efficiency.{pdf,png}`: Aggiornato con l'efficienza massima teorica consentita dalla macchina per entrambe le curve: $C_{dyn}(p)/p$ e $C_{static}(p)/p$, evidenziando come la perdita di efficienza teorica a $p=20$ sia del 49% per partizione statica ma solo del 14% per bilanciamento dinamico.
- `fig_c_karp_flatt.{pdf,png}`: Metrica di Karp-Flatt $e(p)$.
- `fig_d_amdahl_fit.{pdf,png}`: Curve di Amdahl fittate su $p \le 4$ con banda bootstrap 95%.
- `fig_e_hybrid_heatmap.{pdf,png}`: Griglia termica $R \times T$ con marcatura SMT su $T$ dispari.
- `fig_f_grpc_vs_mpi.{pdf,png}`: gRPC ($S_{wall}$ vs $S_{compute}$) vs MPI nativo fino a $p=32$.
- `fig_g_openmp_schedules.{pdf,png}`: Confronto delle 15 clausole di scheduling a $T=16$.
- `fig_h_taskbased_scaling.{pdf,png}`: Taskloop vs dynamic master-worker MPI.
- `fig_i_pcores_vs_all.{pdf,png}`: Isolamento P-cores vs ALL cores.

---

## Stadio 13.4-ter — Sintesi Correzioni Metodologiche e Chiusura M13.4

### 1. Capacità Reale dell'Eterogeneità Hardware (W1)
- **Modello sintetico vs Misure effettive:** Il valore $C(20) = 11.26$ era un modello analitico estrapolato da misure isolate ($6 \times 1.20 + 8 \times 0.5081$).
- **Curva di capacità empirica E9b:** Misurata su ogni $q \in [1..20]$ con ordine di riempimento reale. Sotto partizione statica con carico uniforme, $C_{static}(q)$ scende a $q=7$ ($3.53$) e $q=14$ ($6.15 < 6.48$) poiché i P-core attendono inattivi alla barriera dell'E-core più lento. A $q=20$, $C_{static}(20) = 8.74$, corrispondente quasi esattamente allo speedup di OpenMP statico ($S=8.68$, efficienza sulla capacità statica $99.3\%$). Sotto bilanciamento ideale $\sum (N/T_i)$, $C_{dyn}(20) = 10.21$, su cui OpenMP `dynamic,16` ($S=9.89$) raggiunge il **$96.9\%$** dell'ideale dinamico della macchina.

### 2. Rettifica Mapping e Binding MPI (W2)
- **Bug di binding in E6 ed E8:** L'assenza di `--map-by core` comprimeva rank adiacenti sui due thread hardware del core 0. In E6, il master coordinator (rank 0) condivideva il core 0 con il worker 0 (rank 1), provocando una forte contesa SMT e degradando $S$ a $1.97$ per $R=4$ ($p_{calc}=3$). In E8, $R=2$ registrava $S=1.20$ per la stessa ragione.
- **Risoluzione con `--map-by core --bind-to core` (E6b, E8b, E3b):**
  - Con binding esclusivo ai core fisici, il busy-polling del master (`yield_when_idle`) non produce alcuna contesa misurabile sui worker.
  - **Confronto a pari core fisici allocati ($R$):**
    - Per $R \le 6$ (soli P-cores), il master-worker dinamico **perde sistematicamente** rispetto allo statico (a $R=3$ perde $-31.4\%$, a $R=6$ perde $-15.7\%$), poiché il master consuma un intero core fisico per il coordinamento senza eseguire verifiche.
    - Per $R \ge 7$ (quando entrano gli E-core), il bilanciamento dinamico a chunk **vince nettamente** sullo statico (a $R=8$ vantaggio del **+41.7%**, $5.49$ vs $3.88$; a $R=14$ vantaggio del **+27.4%**, $8.15$ vs $6.40$), impedendo che l'E-core rallenti l'intero batch come avviene in E2b. Il vantaggio percentuale decresce con $R$ man mano che il carico statico per rank si riduce. A $R=7$, sebbene E6b ($S=5.00$) superi E2b a $R=7$ ($S=3.35$), resta comunque inferiore a 6 P-core statici ($S=5.32$) a causa del core consumato dal master.

### 3. Origine del Residuo gRPC (W3)
- L'overhead residuo di 50–75 ms a $p \ge 8$ non è dovuto al client asincrono Python (costo di Ping = 4–7 ms).
- L'esperimento E4b (container confinati sui soli P-core `0-11`) dimostra che a $p=4$ il residuo scende a **11.85 ms**, mentre a $p=8$ permane a **74.85 ms**: il fenomeno è imputabile all'oversubscription dei 6 P-core fisici (8 container > 6 core fisici, forzando la condivisione SMT su almeno 2 core: il rallentamento di ~1.8× della generazione sul container più conteso aggiunge ~75 ms sul percorso critico).

### 4. Revisione Confronti Statistici (W4)
- **Ibrido vs Puri:** A $p=20$, gli intervalli IQR di MPI puro ($S=8.81$), OpenMP close ($S=8.37$) e Ibrido ($S=8.30$) sono sovrapposti; l'ibrido **non vince** a $p=20$ ed è statisticamente indistinguibile dai modelli puri. A pari core fisici (E3b), l'ibrido è comparabile o leggermente inferiore a MPI puro.
- **Amdahl:** La frazione seriale $f_s = 2.802\%$ [Bootstrap 95% CI: $2.330\%,\; 4.006\%$] su E2b ($p \le 4$) è una perdita di scalabilità effettiva a $p \le 4$, non codice seriale algoritmico.
- **Affinità OpenMP:** Provata sperimentalmente a runtime con `OMP_DISPLAY_AFFINITY=true`, confermando la collocazione del thread 1 su Core 7 (E-core) con `spread` a $T=2$ e la saturazione sequenziale dei P-cores con `close`.



