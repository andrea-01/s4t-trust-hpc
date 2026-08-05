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

## Fase M3: Notifiche Email

Il modulo `notification/` implementa un demone indipendente in background (con Python, FastAPI, web3.py e smtplib) che si occupa dell'invio delle email di notifica all'owner del device quando viene creato un `OnboardingRequested`.
Questo servizio disaccoppia la gestione delle notifiche dal Gateway e dalla catena dei blocchi, permettendo l'idempotenza (nessuna email inviata due volte) e il monitoraggio stateless degli eventi.

### Caratteristiche
- Ascolto diretto degli eventi on-chain, con tracking tramite file di checkpoint montato tramite volume.
- Autorilevamento e reset del checkpoint in caso di interruzione o hard-reset della blockchain locale (`hardhat-node`).
- Invio di email in formato plain-text per via SMTP senza dipendenze cloud o esterne.
- Identificazione mock degli account verso email fittizie tramite file di registro.

### Avvio tramite Docker Compose

Il servizio di notifica e il server SMTP catcher `mailpit` sono integrati e operano insieme.
Mailpit intercetta e visualizza tutte le email inviate internamente all'indirizzo http://localhost:8025 (API/Interfaccia Web).

Per testare le notifiche:
1. Avvia l'infrastruttura di base (se non lo è già):
   ```bash
   cd deploy
   docker compose up -d
   ```
2. Invia una richiesta come admin, lanciando il container (assicurati di usare `--no-deps` in modo da non riavviare il contratto, per conservare lo stato della chain):
   ```bash
   docker compose run --rm --no-deps client-admin
   ```
3. Visita [http://localhost:8025](http://localhost:8025) per visualizzare l'email nella mailbox simulata di Mailpit!

## Fase M4: Dashboard (UI)

Il modulo `ui/` implementa un'interfaccia web minimale sviluppata in Python (FastAPI + Jinja2) per interagire con il gateway.
Questa UI permette di visionare in tempo reale le richieste di onboarding e di crearne di nuove, disaccoppiando l'utente finale dalle chiamate API.

### Caratteristiche
- Rendering HTML server-side tramite template Jinja2.
- Tabella per visualizzare le richieste e il loro stato, auto-aggiornata via polling asincrono in background dal client (JavaScript + fetch) senza ricaricare la pagina.
- Form per inserire facilmente nuove richieste di onboarding (inserendo `device_id` e l'indirizzo `owner`).
- Interfacciamento esclusivo e sicuro via REST API verso il servizio `gateway` (che fa da proxy ed espone a sua volta le interazioni blockchain).

### Avvio tramite Docker Compose

La Dashboard è integrata e si avvia con il resto dello stack:

```bash
cd deploy
docker compose up -d
```
Una volta avviato, la Dashboard è visitabile all'indirizzo [http://localhost:8080](http://localhost:8080).
Potrai visionare la notifica generata tramite il link diretto a Mailpit o visitando [http://localhost:8025](http://localhost:8025).
