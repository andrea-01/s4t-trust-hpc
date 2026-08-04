# s4t-trust-hpc

Framework modulare per onboarding automatizzato e gestione trust decentralizzata (blockchain) di dispositivi IoT, con livello di calcolo distribuito (HPC).
Primo caso d'uso: Stack4Things/IoTronic.

## Fase M1: Onboarding Trust Smart Contract

Questo repository contiene lo scaffolding iniziale e il modulo `chain/`, che implementa la prima fase del progetto: lo smart contract per l'onboarding decentralizzato e l'autorizzazione all'accesso tramite Node.js client di simulazione.

### Struttura attuale
- `chain/`: Progetto Hardhat (TypeScript) contenente lo smart contract `OnboardingTrust.sol`, test e client di simulazione.
- `deploy/`: Configurazione Docker Compose per avviare una testnet locale a 3 container (nodo RPC + 2 client).
- Placeholder vuoti (`gateway/`, `ui/`, `hpc-engine/`, etc.) per i moduli futuri.

### Avvio della Testnet (Docker Compose)

Per dimostrare l'interazione tra ruoli (Admin e Owner) sulla blockchain senza necessità di configurazioni locali, puoi usare Docker Compose:

1. Vai nella cartella di deploy:
   ```bash
   cd deploy
   ```
2. Crea il file `.env` copiando l'example:
   ```bash
   cp .env.example .env
   ```
3. Avvia la rete:
   ```bash
   docker compose up --build
   ```

Vedrai il nodo Hardhat avviarsi. Non appena la porta RPC `8545` sarà pronta, i due client (`client-admin` e `client-owner`) si collegheranno in automatico.
L'admin deployerà il contratto ed effettuerà la richiesta. L'owner rimarrà in ascolto, rileverà la richiesta e l'approverà inviando una transazione.

**Nota Tecnica su Healthcheck**: I due container client nel file `docker-compose.yml` usano la dipendenza `depends_on: { hardhat-node: { condition: service_healthy } }`. Questa strategia tramite healthcheck nativo di Docker (che fa un piccolo fetch HTTP sulla porta RPC) è stata preferita rispetto all'implementazione di backoff nei client per mantenere gli script TypeScript puri focalizzati sulla logica blockchain senza inquinarli con cicli di wait per l'infrastruttura sottostante. (Nel codice client `simulate-owner.ts` è comunque presente un piccolo loop in quanto deve attendere *specificamente* il deploy del contratto da parte dell'admin, ma non per attendere l'avvio del demone RPC).

### Esecuzione Test Hardhat

Per testare logicamente lo smart contract:

1. Entra nella cartella `chain/`:
   ```bash
   cd chain
   ```
2. Installa le dipendenze locali (richiesto Node >= 22 o TypeScript < 5):
   ```bash
   npm install
   ```
3. Lancia la suite di test:
   ```bash
   npx hardhat test
   ```

## Fase M2: Gateway Python

Il modulo `gateway/` implementa un proxy REST stateless in Python (FastAPI + web3.py) per interagire con lo smart contract. 
Questo servizio facilita l'integrazione di sistemi esterni permettendo loro di non dover gestire le connessioni RPC direttamente.

### Endpoint Disponibili

- `POST /onboarding-request`: Crea una richiesta di onboarding. Richiede un JSON con `device_id` e `owner_address`. La chiave privata dell'admin (necessaria per firmare la transazione) è gestita internamente dal server e non va mai esposta o fornita nella richiesta.
- `GET /status/{request_id}`: Legge lo stato corrente (Pending, Approved, Rejected, Revoked) di una richiesta direttamente dalla chain.
- `GET /events/recent`: Espone gli ultimi eventi emessi dallo smart contract, prelevati tramite un task di polling in background.

### Avvio tramite Docker Compose

Il gateway è integrato nell'ambiente `deploy/docker-compose.yml`. Avviando la rete, il gateway sarà esposto sulla porta 8000:

```bash
cd deploy
docker compose up --build
```
Una volta avviato, la documentazione Swagger interattiva sarà disponibile all'indirizzo [http://localhost:8000/docs](http://localhost:8000/docs).
