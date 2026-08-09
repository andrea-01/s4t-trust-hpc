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
- **[`satellite/`](satellite/README.md)**: Orchestratore Python (FastAPI) che gestisce il leasing dei nodi (via gateway) e invia i task ai worker tramite gRPC.
- **[`hpc-engine/`](hpc-engine/README.md)**: Worker in C++ / gRPC che esegue i task di calcolo (es. benchmark di verifica firme ECDSA e test MPI).
- **[`deploy/`](deploy/README.md)**: Configurazione Docker Compose che definisce le reti e i container di tutti i moduli, separando logicamente lo stack base e lo stack pipeline.
- **`s4t-plugin/`**: Placeholder (non implementato) per la futura integrazione finale con Stack4Things.

## Guida all'Utilizzo (End-to-End)

Il sistema è interamente containerizzato e può essere avviato tramite Docker Compose senza installare le dipendenze in locale.

### 1. Inizializzazione della Rete Condivisa
Poiché lo stack base e lo stack pipeline sono gestiti da compose file separati, devono comunicare tramite una rete Docker esterna (da creare solo la prima volta):
```bash
docker network create s4t-bridge
```

### 2. Avvio dello Stack Base
Lo stack base include il nodo blockchain, il gateway REST, il servizio di notifica e la dashboard UI.
```bash
cd deploy
cp .env.example .env
docker compose up -d --build
```
Una volta avviato, potrai accedere a:
- **Dashboard UI**: [http://localhost:8080](http://localhost:8080)
- **Gateway Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Mailbox Notifiche (Mailpit)**: [http://localhost:8025](http://localhost:8025)

### 3. Avvio dello Stack Pipeline (HPC)
Questo stack comprende l'orchestratore Satellite e un pool di Worker C++. All'avvio, i worker si auto-registrano sulla blockchain (onboarding) chiamando il gateway.
```bash
cd deploy
docker compose -f docker-compose.pipeline.yml up -d --build
```
Il Satellite esporrà le sue API su:
- **Satellite Swagger**: [http://localhost:8001/docs](http://localhost:8001/docs)

### 4. Flusso di Test Integrato (Leasing)
Una volta avviati entrambi gli stack, puoi simulare il ciclo completo:
1. Richiedi l'allocazione (lease) di un certo numero di worker dal Satellite:
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"count": 2}' http://localhost:8001/pipeline/lease
   ```
   *Il Satellite invoca il Gateway, che a sua volta registra il lease nello smart contract.*
2. Esegui il calcolo distribuito sui nodi allocati usando l'UUID restituito al passo 1:
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"initial_value": 10}' http://localhost:8001/pipeline/<UUID>/run
   ```
3. Rilascia i worker:
   ```bash
   curl -X POST http://localhost:8001/pipeline/<UUID>/release
   ```

Per informazioni dettagliate sul testing e lo sviluppo dei singoli moduli, consulta i rispettivi `README.md` elencati nella sezione Componenti.
