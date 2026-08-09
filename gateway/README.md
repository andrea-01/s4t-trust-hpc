# Gateway - Blockchain REST Proxy

Questo modulo agisce come livello di astrazione (stateless REST proxy) tra il mondo applicativo e la blockchain. Implementato in Python con FastAPI e `web3.py`, consente ai componenti del sistema di interagire con gli smart contract senza implementare logiche blockchain native.

## Funzionalità Principali

- **Proxy Smart Contract**: Inoltra e firma le transazioni per le operazioni principali sugli smart contract `OnboardingTrust.sol` e `LeasingRegistry.sol` (richieste, approvazioni, leasing).
- **Gestione Esclusiva Chiavi (Sicurezza)**: Il Gateway è l'unico componente a possedere e gestire l'accesso alla chiave privata (`ADMIN_PRIVATE_KEY`), garantendo che nessun altro servizio (come UI, Notification o Satellite) abbia privilegi transazionali diretti. Nessun endpoint riceve chiavi private nei payload.
- **Event Poller in Memoria**: Include un task di polling in background che interroga il nodo Hardhat (RPC) per gli ultimi eventi emessi sulla chain, mantenendo una cache *stateless* e ad accesso rapido in memoria, usata per popolare la UI. Nessun database persistente viene utilizzato.

## Endpoint Disponibili

La documentazione interattiva (Swagger) con l'elenco completo degli endpoint è accessibile su `/docs` dopo l'avvio.

### Onboarding (`/onboarding-request` e `/status`)
- `POST /onboarding-request`: Crea una nuova richiesta di trust per un device fornendo `device_id` e `owner_address`. Firma la transazione e invoca il contratto.
- `GET /status/{request_id}`: Legge on-demand lo stato di trust direttamente dalla blockchain.
- `GET /events/recent`: Ritorna gli eventi recenti prelevati dal poller in memoria.

### Leasing (`/leasing/lease` e `/leasing/release`)
- `POST /leasing/lease`: Avvia la transazione on-chain per locare uno o più nodi worker. Verifica internamente che i nodi abbiano lo stato `Approved` nel contratto di Onboarding.
- `POST /leasing/release`: Libera e rilascia l'allocazione on-chain di un lease esistente.
- `GET /leasing/status/{device_id}`: Restituisce lo stato corrente di leasing per uno specifico worker.

## Avvio
Il Gateway è una colonna portante dello Stack Base e si avvia insieme al nodo RPC e agli altri componenti:

```bash
cd ../deploy
docker compose up -d
```

Una volta avviato, le API sono disponibili all'indirizzo [http://localhost:8000](http://localhost:8000).

## Sviluppo Locale e Test
I test di integrazione del gateway richiedono l'esecuzione del nodo Hardhat sulla porta RPC `8545`. 

1. Avviare il nodo in background (nella root `deploy/`):
   ```bash
   docker compose up -d hardhat-node
   ```
2. (Dentro `gateway/`) Installare le dipendenze:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Avviare la suite test:
   ```bash
   pytest tests/
   ```
