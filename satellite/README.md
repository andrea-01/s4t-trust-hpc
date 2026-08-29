# Satellite - HPC & IoT Orchestrator

Questo modulo agisce come orchestratore per il livello di calcolo distribuito (HPC Pipeline). Sviluppato in Python (FastAPI), si occupa di ricevere le richieste di allocazione dei task, coordinare il leasing dei nodi on-chain e orchestrare l'esecuzione remota delegandola alle board IoTronic (Stack4Things) tramite REST, le quali invocano localmente i worker C++ via gRPC.

## Funzionalità Principali
- **Gestione Leasing On-Chain**: Coordina l'occupazione e il rilascio dei nodi comunicando con il `gateway` (`POST /leasing/lease`, `POST /leasing/release`) per validare lo stato `Approved` on-chain in modo sicuro, senza maneggiare chiavi private.
- **Client IoTronic REST (`iotronic_client.py`)**: Interagisce con Keystone (autenticazione token `POST /v3/auth/tokens`) e IoTronic Conductor (`POST /v1/boards/{board}/plugins/{plugin}` con azione `PluginCall`) per inviare i task di calcolo in modo sincrono e sicuro.
- **Esecuzione Sequenziale Multi-Nodo (`pipeline_client.py`)**: Coordina l'esecuzione del task in cascata sui nodi leased (l'output del nodo $i$ diventa l'input del nodo $i+1$).
- **API REST Stateless**: Fornisce un'interfaccia HTTP semplice per richiedere, avviare e rilasciare pipeline di calcolo.

## Prerequisiti
- Lo stack base (`deploy/docker-compose.yml`) deve essere attivo con Hardhat e Gateway.
- Lo stack IoTronic (`Stack4Things_DockerCompose_deployment`) deve essere attivo con Conductor, Keystone e le board Lightning-Rod registrate e connesse a `s4t-bridge`.

## Endpoint Disponibili

- `POST /pipeline/lease`: Richiede il lease di $N$ nodi (`{"count": 2}`). Interroga il Gateway per il lease on-chain. Restituisce l'ID della pipeline (UUID).
- `POST /pipeline/{pipeline_id}/run`: Avvia l'esecuzione del task sui nodi allocati alla pipeline (es. `{"initial_value": 10}`).
- `POST /pipeline/{pipeline_id}/release`: Rilascia i nodi associati alla pipeline on-chain (via Gateway).

## Avvio
Il Satellite viene avviato tramite Docker Compose come parte dello Stack Pipeline:

```bash
cd ../deploy
docker compose -f docker-compose.pipeline.yml up -d --build
```
L'API sarà disponibile all'indirizzo http://localhost:8001 (porta sfasata rispetto al Gateway per evitare conflitti).

## Sviluppo e Test Locali
```bash
cd satellite
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```
