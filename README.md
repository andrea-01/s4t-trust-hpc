# s4t-trust-hpc

Framework modulare per l'onboarding automatizzato e la gestione del trust decentralizzata (blockchain) di dispositivi IoT, con un livello di calcolo distribuito (HPC). Questo progetto si propone di fornire una soluzione integrata e scalabile per IoTronic / Stack4Things.

Questo repository è organizzato come un mono-repo in cui ogni modulo ha la propria responsabilità, connettendosi agli altri per formare due macro-sistemi: lo **Stack Base** (blockchain, gateway, notifiche, UI) e lo **Stack Pipeline** (satellite e worker HPC).

## Componenti del Sistema

Il progetto è suddiviso nelle seguenti cartelle/moduli principali. Per dettagli tecnici e istruzioni specifiche, fare riferimento al `README.md` di ogni modulo:

### Stack Base (Trust & Onboarding)
- **[`chain/`](chain/README.md)**: Progetto Hardhat contenente gli smart contract `OnboardingTrust.sol` e `LeasingRegistry.sol` per la gestione del trust e il leasing dei worker.
- **[`gateway/`](gateway/README.md)**: Proxy REST in Python (FastAPI) che espone in modo sicuro le funzionalità della blockchain (richiesta onboarding, approvazione, leasing).
- **[`notification/`](notification/README.md)**: Demone Python indipendente che intercetta gli eventi della blockchain e invia notifiche email (tramite Mailpit) ai proprietari dei device.
- **[`ui/`](ui/README.md)**: Dashboard web minimale (FastAPI + Jinja2) per visualizzare in tempo reale lo stato delle richieste e avviare nuove procedure di onboarding.

### Stack Pipeline (HPC & Esecuzione Distribuita)
- **[`satellite/`](satellite/README.md)**: Orchestratore Python (FastAPI) che gestisce il leasing dei nodi (via gateway) e invia i task di calcolo alle board IoTronic (Stack4Things).
- **[`hpc-engine/`](hpc-engine/README.md)**: Worker in C++ / gRPC che esegue i task di calcolo ad alte prestazioni (verifica firme ECDSA P-256 e test MPI).
- **[`s4t-plugin/`](s4t-plugin/README.md)**: Plugin Python per Stack4Things / IoTronic (Lightning-Rod) che agisce da client gRPC verso i worker C++ per l'esecuzione delegata dei task.
- **[`deploy/`](deploy/README.md)**: Configurazioni Docker Compose per orchestrare l'ecosistema (stack base, pipeline e benchmark distribuito).

## Guida all'Utilizzo (End-to-End)

Il sistema è interamente containerizzato e può essere avviato tramite Docker Compose senza installare le dipendenze in locale.

### 1. Inizializzazione della Rete Condivisa
Poiché lo stack base, lo stack pipeline e lo stack IoTronic sono gestiti da compose file separati, devono comunicare tramite una rete Docker esterna (da creare solo la prima volta):
```bash
docker network create s4t-bridge
```

### 2. Avvio dello Stack Base
Lo stack base include il nodo blockchain, il deployer dei contratti, il gestore approvazioni (`owner-auto-approver`), il gateway REST, il servizio di notifica e la dashboard UI.
```bash
cd deploy
cp .env.example .env
docker compose up -d --build
```
Una volta avviato, potrai accedere a:
- **Dashboard UI**: [http://localhost:8080](http://localhost:8080) (protetta da Basic Auth, credenziali configurabili in `.env`: default `admin` / `adminpassword`)
- **Gateway Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Mailbox Notifiche (Mailpit)**: [http://localhost:8025](http://localhost:8025)

### 3. Avvio dello Stack IoTronic Esterno (Prerequisito per la Pipeline)
A partire da M9.3, l'orchestratore Satellite delega l'esecuzione dei task ai nodi worker passando attraverso l'infrastruttura IoTronic / Stack4Things. È necessario avere lo stack IoTronic attivo sulla rete Docker `stack4things_dockercompose_deployment_s4t` (con Conductor, Keystone, Crossbar e i container Lightning-Rod corrispondenti ai worker registrati con il plugin gRPC):
```bash
# Esempio nella directory sibling dello stack IoTronic
cd ../Stack4Things_DockerCompose_deployment
docker compose up -d
```

### 4. Avvio dello Stack Pipeline (HPC)
Questo stack comprende l'orchestratore Satellite e i nodi Worker C++.
```bash
cd deploy
docker compose -f docker-compose.pipeline.yml up -d --build
```
Il Satellite esporrà le sue API su:
- **Satellite Swagger**: [http://localhost:8001/docs](http://localhost:8001/docs)

### 5. Flusso di Test Integrato (Leasing ed Esecuzione)
Una volta avviati gli stack, puoi testare il ciclo completo:

1. Richiedi l'allocazione (lease) di un certo numero di worker dal Satellite:
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"count": 2}' http://localhost:8001/pipeline/lease
   ```
   *Risposta:* `{"pipeline_id": "<UUID>", "nodes": ["worker-1", "worker-2"]}`

2. **Opzione A — Esecuzione Sequenziale (Incremento contatore):**
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"initial_value": 10}' http://localhost:8001/pipeline/<UUID>/run
   ```

3. **Opzione B — Esecuzione Parallela Distribuita (Verifica Firme ECDSA batch):**
   ```bash
   curl -X POST -H "Content-Type: application/json" \
     -d '{"total_batch": 1000, "num_threads": 1, "base_seed": 42}' \
     http://localhost:8001/pipeline/<UUID>/run-parallel
   ```
   *Il Satellite suddivide il carico di firme in chunk bilanciati e li distribuisce concorrentemente sui nodi allocati via IoTronic.*

4. Rilascia i worker:
   ```bash
   curl -X POST http://localhost:8001/pipeline/<UUID>/release
   ```

Per informazioni dettagliate sul testing e lo sviluppo dei singoli moduli, consulta i rispettivi `README.md` elencati nella sezione Componenti.
