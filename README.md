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
