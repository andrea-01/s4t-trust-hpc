# Satellite - HPC Orchestrator

Questo modulo agisce come orchestratore per il livello di calcolo distribuito (HPC Pipeline). Sviluppato in Python (FastAPI), si occupa di ricevere le richieste di allocazione dei task, gestire il leasing dei nodi e orchestrare l'esecuzione remota sui worker tramite gRPC.

## Funzionalità Principali
- **Gestione Leasing (In-memory e Blockchain)**: Il satellite mantiene uno stato in memoria per coordinare l'occupazione dei nodi HPC locali. Comunica inoltre con il `gateway` per registrare e validare il lease on-chain in modo sicuro, senza maneggiare direttamente le chiavi private.
- **Client gRPC (`pipeline_client.py`)**: Implementa le chiamate gRPC verso i nodi Worker (`hpc-engine`) per smistare i task (ad es. esecuzione in catena su nodi multipli).
- **API REST Stateless**: Fornisce un'interfaccia HTTP semplice per richiedere, avviare e rilasciare pipeline di calcolo.

## Prerequisiti
Il modulo dipende dal file protobuf `../proto/pipeline.proto` per generare i client gRPC (i file Python vengono generati durante la build Docker o via script locale). Inoltre, richiede che il `gateway` sia accessibile per la convalida blockchain del leasing.

## Endpoint Disponibili

- `POST /pipeline/lease`: Richiede il lease di $N$ nodi (`{"count": 2}`). Interroga il Gateway per il lease on-chain. Restituisce l'ID della pipeline (UUID).
- `POST /pipeline/{pipeline_id}/run`: Avvia l'esecuzione del task sui nodi allocati alla pipeline (es. `{"initial_value": 10}`).
- `POST /pipeline/{pipeline_id}/release`: Rilascia i nodi associati alla pipeline, sia localmente che on-chain (via Gateway).

## Avvio
Il Satellite viene avviato tramite Docker Compose come parte dello Stack Pipeline:

```bash
cd ../deploy
docker compose -f docker-compose.pipeline.yml up -d --build
```
L'API sarà disponibile all'indirizzo http://localhost:8001 (la porta è sfasata rispetto al Gateway per evitare conflitti di porta).

## Sviluppo e Test Locali
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Genera i file gRPC
python -m grpc_tools.protoc -I../proto --python_out=app/ --grpc_python_out=app/ ../proto/pipeline.proto
# Avvia il server
uvicorn app.main:app --reload --port 8001
```
