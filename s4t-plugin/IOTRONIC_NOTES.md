# Appunti di Integrazione: IoTronic e Lightning-Rod (M9.1)

Questo documento raccoglie le scoperte fatte durante il deploy dello stack Stack4Things (IoTronic) e l'analisi del meccanismo dei plugin, come richiesto dalla fase M9.1 del progetto.

## Deploy dello Stack IoTronic

Lo stack è stato deployato clonando il repository `Stack4Things_DockerCompose_deployment` come cartella sibling (allo stesso livello) rispetto alla root del mono-repo `s4t-trust-hpc`, secondo la convenzione stabilita (path relativo `../Stack4Things_DockerCompose_deployment`).

**Modifiche richieste al deploy:**
- Per rispettare la regola di **non patchare il codice upstream** (`docker-compose.yml`), il container `lightning-rod` falliva il pull dell'immagine a causa di un placeholder `docker.io/mdslab/lrod:compose@sha256:<resolved-image-digest>`.
- È stato creato un file `docker-compose.override.yml` locale che corregge l'immagine in `docker.io/mdslab/lrod:compose` permettendo allo stack di avviarsi correttamente.
- Il conflitto locale sulla porta `50094` (usata da `iotronic-wstun` che tenta di esporre `50001-50100` sull'host) è stato mitigato semplicemente riprovando il deploy una volta che la porta effimera dell'host si è liberata (essendo in uso dinamico per chiamate outbound). Nessun patching è stato necessario per le porte.

## Meccanismo dei Plugin (Lightning-Rod)

Dal codice analizzato (`iotronic-lightning-rod` repo, file `modules/plugin_manager.py` e gli esempi), il meccanismo di esecuzione remota del codice non è uno script bash/python grezzo, ma segue un preciso scaffold orientato agli oggetti:

- **Linguaggio Atteso**: Python 3.
- **Entrypoint**: Il plugin deve definire una classe `Worker` che eredita da `iotronic_lightningrod.modules.plugins.Plugin.Plugin`.
- **Esecuzione Sincrona vs Asincrona**:
  - **Sincrona (`PluginCall`)**: Il metodo `run()` viene eseguito e restituisce il risultato al chiamante inserendolo nella coda interna (`self.q_result.put(risultato)`).
  - **Asincrona (`PluginStart`)**: La classe lavora come un Thread (il manager fa `worker.start()`). Il plugin viene mantenuto attivo (anche al reboot se la flag `onboot` è attiva) fino a che non riceve un segnale di stop.
- **Parametri (Input)**: Passati come dizionario JSON tramite l'argomento `params` del costruttore.

## Analisi Comparativa: Scostamenti rispetto all'Outline

Come richiesto, ecco un confronto esplicito tra quanto rilevato ora e le ipotesi riportate in `docs/outline_progetto_s4t_hpc_blockchain.md` (§0 e §4.2):

### Rispetto al §0 (Grounding architettura S4T)
- **Ipotesi Outline**: "Lightning-Rod: agente Python lato dispositivo [...], esegue i plugin (codice Python) ricevuti dal Conductor".
- **Realtà (Confermata)**: L'architettura è esattamente quella descritta. I plugin vengono prima "iniettati" (salvati in `/var/lib/iotronic/plugins/`) e poi chiamati o avviati. L'onboarding manuale via UI → board-code → Crossbar si è dimostrato essere il flusso di default documentato nel README dello stack.

### Rispetto al §4.2 (Connessione HPC engine ↔ Stack4Things)
- **Ipotesi Outline (Opzione C)**: "Il plugin Lightning-Rod è un modulo Python installato sul device (secondo il meccanismo nativo IoTronic dei plugin), che funge da client gRPC verso l'HPC engine: riceve porzioni di codice/task dal satellite e li esegue localmente, restituendo risultati".
- **Realtà (Da tenere in considerazione)**: L'ipotesi architetturale è confermata ed è fattibile senza ostacoli. Il plugin *dovrà* essere una classe `Worker` che nel metodo `run()` implementa un client gRPC python (tramite le librerie standard `grpcio`) e apre una connessione verso il container del Worker C++.
- **Scostamenti identificati**: Nessun scostamento bloccante, ma l'implementazione pratica del plugin sarà strutturata come una classe Python estesa, non come uno script autonomo. Bisogna inoltre prestare attenzione alla dipendenza di `grpcio` sul device emulato: essendo l'emulatore Docker `lrod:compose` basato su un ambiente specifico, se la libreria gRPC non è pre-installata nell'immagine Docker nativa di Lightning-Rod, il plugin potrebbe fallire l'import. Nel caso, sarà necessario installarla dinamicamente al runtime (es. `subprocess.call(['pip', 'install', 'grpcio'])`) o creare un'immagine custom per M9.2.

## Esempio Plugin "Hello World"
È stato redatto un plugin minimale (in `/s4t-plugin/hello_world_test/plugin.py`) pronto all'iniezione non appena la board sarà confermata online (via onboarding manuale utente). Il plugin semplicemente legge eventuali parametri e restituisce una stringa di conferma, dimostrando l'operatività del `q_result`.

## Integrazione gRPC e completamento Stadio 9.2

Durante lo Stadio 9.2 l'integrazione è stata concretizzata trasformando il plugin "hello world" (presente in `hello_world_test/`, che ora funge solo da scaffold di riferimento storico della fase 9.1) in un vero client gRPC verso il worker HPC in C++.

### Flusso di Build e Iniezione
- È stato sviluppato un template (`plugin_template.py`) e uno script di build (`build_plugin.sh`).
- Poiché IoTronic accetta un singolo file Python come plugin, lo script di build compila i file protobuf (utilizzando il container `satellite`), li comprime in uno `.zip`, codifica lo zip in Base64 e lo inietta direttamente nel file sorgente del plugin.
- A runtime, il plugin decodifica il Base64, salva lo `.zip` nel container di Lightning-Rod e lo aggiunge al `sys.path` per l'importazione.
- È stato necessario applicare un patch automatico (`sed`) nel flusso di build per retro-compatibilità, eliminando l'argomento `_registered_method=True` dai file gRPC generati, in quanto incompatibile con le versioni di `grpcio` (1.62.x) disponibili per Python 3.7 nell'emulatore.

### Gestione delle Dipendenze a Runtime
Come ipotizzato, la libreria `grpcio` (e `protobuf`) non era presente nell'immagine di base di Lightning-Rod. Il problema è stato aggirato inserendo nel plugin un blocco `try/except ImportError` che, in caso di libreria mancante, effettua una installazione dinamica e idempotente tramite `subprocess.check_call(["pip", "install", "grpcio", "protobuf"])`.

### Risultato Test End-to-End
Il test si è concluso con successo. Utilizzando l'azione `PluginCall`, il comando `iotronic plugin-action test_board grpc_client PluginCall --params input_value=42` ha inviato correttamente la richiesta al worker remoto gRPC (`deploy-worker-1-1:50051`). Il worker ha risposto processando l'operazione (`INCREMENT_COUNTER`), e il plugin ha restituito correttamente l'output `SUCCESS: Worker worker-1 incremented 42 -> 43` tramite l'infrastruttura di ritorno asincrona IoTronic/WAMP.

## Fase M9.3 - Fase 1 Investigazione

1. **Analisi chiamata REST (PluginCall)**: L'esecuzione tramite CLI di `iotronic plugin-action` effettua internamente una chiamata **REST HTTP POST** sincrona:
   - **URL**: `POST /v1/boards/{board_name}/plugins/{plugin_name}`
   - **Headers**: Richiede autenticazione Keystone via `X-Auth-Token` e header standard come `X-OpenStack-Iotronic-API-Version: 1.0`.
   - **Payload JSON**: `{"action": "PluginCall", "parameters": {"<key>": "<value>"}}`
   - **Comportamento sincrono**: L'endpoint blocca l'HTTP request in attesa che la board, via WAMP/crossbar, completi l'esecuzione e restituisca il risultato. In caso di errore (es. plugin assente o board offline), la connessione HTTP va in timeout. Non è necessario alcun meccanismo di polling o read differita; il risultato è contenuto nel body della risposta HTTP una volta risolta.

2. **Compatibilità nomi Board**: Le board possono essere registrate con lo stesso identificativo del `device_id` dell'HPC-Engine (es. `worker-1`, `worker-2`, `worker-3`). Non ci sono conflitti con namespace IoTronic. L'inserimento ha avuto successo sebbene la CLI openstack-iotronicclient sollevi un warning apparente alla fine del processo di creazione, i record persistono correttamente nel database con stato `registered`.


### Problema Noto: Wampagent Stale (Crash-Loop di Lightning-Rod)
- **Sintomo**: I container `lightning-rod` vanno in crash-loop all'avvio con l'errore `no callee registered for procedure <e56fea1fa400.stack4things.connection>`. Il log indica che la board crede di essere `operative` ma tenta di connettersi a un agent inesistente (`e56fea1fa400`).
- **Causa**: Il container `iotronic-wagent` aveva registrato il suo hostname (`e56fea1fa400`) nel database giorni prima. Alla sua ricreazione (con un nuovo container ID/hostname), il vecchio record è rimasto in tabella `wampagents` con `online=1`. Il Conductor, usando `get_best_agent()`, ha continuato ad assegnare l'agent "fantasma" obsoleto alle nuove board che effettuavano la registrazione (`stack4things.register`). Il Conductor memorizza la configurazione iniziale in DB (colonna `config` della tabella `boards`), quindi ai successivi riavvii le board ricevevano sempre la configurazione "velenata".
- **Soluzione**:
  1. Rimuovere il record obsoleto: `DELETE FROM wampagents WHERE hostname='<vecchio_hostname>';` e riavviare il container `iotronic-wagent`.
  2. Forzare la rigenerazione della configurazione per le board: `UPDATE boards SET status='registered', agent=NULL, config=NULL WHERE name LIKE 'worker-%';`.
  3. Pulire il file `/etc/iotronic/settings.json` sui `lightning-rod` container inietando una configurazione pulita per forzare il first-boot.

## Completamento Fase M9.3 (Refactor Satellite & E2E Testing)

Nella fase finale di M9.3 (sotto-fasi 9.3.c e 9.3.d), il modulo `satellite/` è stato completamente rifattorizzato per eliminare qualsiasi chiamata gRPC diretta ai worker C++, sostituendola interamente con l'orchestrazione remota delegata a Stack4Things / IoTronic via REST HTTP.

### 1. Architettura di Invocazione e Autenticazione
- **Client IoTronic Stateless (`satellite/app/iotronic_client.py`)**:
  - Autenticazione con Keystone via `POST {os_auth_url}/auth/tokens` ottenendo un token scoped (`X-Subject-Token`).
  - Chiamata sincrona a IoTronic Conductor via `POST {iotronic_url}/v1/boards/{board_name}/plugins/{plugin_name}` con payload `{"action": "PluginCall", "parameters": {"worker_addr": ..., "input_value": ...}}`.
  - Gestione automatica di token expiration (401 -> refresh token e retry una volta), errori HTTP e timeout.
- **Flusso Sequenziale Multi-Nodo (`satellite/app/pipeline_client.py`)**:
  - Riceve la lista di nodi allocati via lease blockchain (`worker-1`, `worker-2`, `worker-3`).
  - Per ciascun nodo, effettua la chiamata REST a IoTronic indirizzandola alla corrispondente board; la board Lightning-Rod esegue il plugin gRPC locale comunicando con il proprio worker C++ su `s4t-bridge`.
  - L'output di ciascun nodo viene estratto e iniettato come input per il nodo successivo della catena.
- **Semplificazione Node Registry**:
  - `node_directory.json` e `node_registry.py` non contengono più indirizzi gRPC hardcoded (`grpc_url`), poiché il routing è gestito nativamente dal Conductor IoTronic tramite il nome della board (coincidente con il `device_id`).

### 2. Risultati del Testing Automatico E2E (Nessun Mock)
I test automatici implementati in `satellite/tests/test_integration.py` sono stati eseguiti con successo sia dall'ambiente locale sia all'interno del container `deploy-satellite-1`:
- `test_full_pipeline_e2e_sequential`: Esegue il ciclo completo lease (3 nodi on-chain via Gateway) -> run (valore iniziale 42 -> 43 -> 44 -> 45 con trace di 3 worker) -> release (on-chain).
- `test_concurrent_leasing_two_pipelines`: Verifica la tenuta del modello di concorrenza con 2 pipeline attive contemporaneamente (Pipeline A con 2 nodi, Pipeline B con 1 nodo), fallimento atteso su richieste eccedenti la capacità, esecuzione concorrente e rilascio corretto di tutte le risorse.
- `test_error_handling_and_validation`: Verifica la gestione degli errori per parametri non validi e pipeline inesistenti.

## Stadio M11.4: Investigazione Plugin & Ciclo di Vita Aggiornamento

### 1. Ispezione del Plugin Esistente (`plugin_template.py`)
- **Verifica condotta**: Ispezione diretta del sorgente versionato `s4t-plugin/plugin_template.py`.
- **Esito**: Il plugin non inoltrava genericamente qualunque operazione supportata dal worker C++, ma era hardcoded per la sola operazione `INCREMENT_COUNTER` (`req = pipeline_pb2.TaskRequest(operation=pipeline_pb2.OperationType.INCREMENT_COUNTER, input_value=...)`) e per i soli parametri `input_value` e `worker_addr`.
- **Decisione**: È necessaria una modifica additiva al plugin per supportare `VERIFY_SIGNATURES_BATCH` preservando al 100% la compatibilità con `INCREMENT_COUNTER`.

### 2. Investigazione Sperimentale: Ciclo di Vita Aggiornamento Plugin in IoTronic
Verificato sperimentalmente tramite CLI `iotronic` e ispezione dei comandi (`plugin-create`, `plugin-update`, `plugin-remove`, `plugin-inject`, `plugin-delete`):
- `plugin-create` consente la creazione di plugin con lo stesso nome generando un nuovo UUID, causando ambiguità di risoluzione.
- `plugin-update <plugin> code=<file>` tratta il valore come stringa letterale senza caricare il file né propagarlo alle board.
- `plugin-delete <plugin>` fallisce con vincolo di foreign key (`DBReferenceError / injection_plugins_ibfk_2`) se il plugin è attualmente iniettato su una o più board.
- **Flusso corretto e verificato per l'aggiornamento**:
  1. Rimuovere il plugin da tutte le board su cui è presente: `iotronic plugin-remove <board> <plugin_name>`
  2. Eliminare la vecchia definizione del plugin dal registro IoTronic: `iotronic plugin-delete <plugin_name>`
  3. Registrare il nuovo bundle compilato: `iotronic plugin-create --callable <plugin_name> <path_bundle.py>`
  4. Re-iniettare il plugin aggiornato sulle board: `iotronic plugin-inject <board> <plugin_name>`


