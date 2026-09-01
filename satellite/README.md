# Satellite - HPC & IoT Orchestrator

Questo modulo agisce come orchestratore per il livello di calcolo distribuito (HPC Pipeline). Sviluppato in Python (FastAPI), si occupa di ricevere le richieste di allocazione dei task, coordinare il leasing dei nodi on-chain e orchestrare l'esecuzione remota delegandola alle board IoTronic (Stack4Things) tramite REST, le quali invocano localmente i worker C++ via gRPC.

## Funzionalità Principali
- **Gestione Leasing On-Chain**: Coordina l'occupazione e il rilascio dei nodi comunicando con il `gateway` (`POST /leasing/lease`, `POST /leasing/release`) per validare lo stato `Approved` on-chain in modo sicuro, senza maneggiare chiavi private.
- **Client IoTronic REST (`iotronic_client.py`)**: Interagisce con Keystone (autenticazione token `POST /v3/auth/tokens`) e IoTronic Conductor (`POST /v1/boards/{board}/plugins/{plugin}` con azione `PluginCall`) per inviare i task di calcolo in modo sincrono e sicuro.
- **Esecuzione Sequenziale Multi-Nodo (`pipeline_client.py`)**: Coordina l'esecuzione del task in cascata sui nodi leased (l'output del nodo $i$ diventa l'input del nodo $i+1$).
- **Dispatch Parallelo Task+Data HPC (`pipeline_client.py` - M11.4)**: Partiziona un batch totale di firme crittografiche (ECDSA P-256) con schema di resto deterministico, dispatchando il calcolo in parallelo su tutti i nodi leased contemporaneamente via IoTronic REST / WAMP e aggregando i risultati con validazione stringente di correttezza (100% valid count).
- **API REST Stateless**: Fornisce un'interfaccia HTTP semplice per richiedere, avviare e rilasciare pipeline di calcolo.

## Prerequisiti
- Lo stack base (`deploy/docker-compose.yml`) deve essere attivo con Hardhat e Gateway.
- Lo stack IoTronic (`Stack4Things_DockerCompose_deployment`) deve essere attivo con Conductor, Keystone e le board Lightning-Rod registrate e connesse a `s4t-bridge`.

## Endpoint Disponibili

- `POST /pipeline/lease`: Richiede il lease di $N$ nodi (`{"count": 2}`). Interroga il Gateway per il lease on-chain. Restituisce l'ID della pipeline (UUID).
- `POST /pipeline/{pipeline_id}/run`: Avvia l'esecuzione sequenziale incrementale sui nodi allocati alla pipeline (es. `{"initial_value": 10}`).
- `POST /pipeline/{pipeline_id}/run-parallel`: Avvia il dispatch parallelo di verifica firme sui nodi allocati (`{"total_batch": 1000, "num_threads": 1, "base_seed": 42}`).
- `POST /pipeline/{pipeline_id}/release`: Rilascia i nodi associati alla pipeline on-chain (via Gateway).

## Confronto Prestazionale: Dispatch Isolato vs Catena Reale S4T (M11.4)

Nello Stadio 11.4 è stato condotto un confronto controllato a parità di carico (batch totale, numero di nodi, 1 thread OpenMP per nodo) per quantificare l'overhead introdotto dalla catena applicativa completa:
$$\text{Satellite (FastAPI)} \xrightarrow{\text{REST}} \text{Keystone/IoTronic Conductor} \xrightarrow{\text{WAMP}} \text{Lightning-Rod (Plugin)} \xrightarrow{\text{gRPC}} \text{Worker C++}$$
rispetto al dispatch gRPC diretto driver $\to$ worker misurato nel benchmark isolato (M11.3).

### Tabella Comparativa (Dati Sperimentali su 3 Nodi Reali)

| Batch Size | Nodi | $T_{\text{isolato}}$ (avg) | $T_{\text{reale}}$ (avg) | $T_{\text{worker}}$ puro | Overhead $\Delta T$ | Overhead Ratio | Throughput Isolato | Throughput Reale |
|:----------:|:----:|:--------------------------:|:------------------------:|:------------------------:|:-------------------:|:--------------:|:------------------:|:----------------:|
| 1.000      | 1    | 0.1135 s                   | 0.3301 s                 | 0.0535 s                 | +0.2166 s           | **2.91x**      | 8.823,8 sig/s      | 3.080,2 sig/s    |
| 1.000      | 2    | 0.0604 s                   | 0.2442 s                 | 0.0290 s                 | +0.1838 s           | **4.04x**      | 16.568,9 sig/s     | 4.114,6 sig/s    |
| 1.000      | 3    | 0.0449 s                   | 0.3395 s                 | 0.0291 s                 | +0.2946 s           | **7.56x**      | 22.364,8 sig/s     | 2.997,2 sig/s    |
| 5.000      | 1    | 0.4699 s                   | 0.6298 s                 | 0.2852 s                 | +0.1599 s           | **1.34x**      | 10.642,4 sig/s     | 7.942,8 sig/s    |
| 5.000      | 2    | 0.2577 s                   | 0.5059 s                 | 0.1567 s                 | +0.2482 s           | **1.96x**      | 19.420,3 sig/s     | 9.882,7 sig/s    |
| 5.000      | 3    | 0.1957 s                   | 0.4811 s                 | 0.1252 s                 | +0.2855 s           | **2.46x**      | 25.663,6 sig/s     | **10.393,2 sig/s** |

### Analisi Tecnica dell'Overhead

1. **Stabilità dell'Overhead di Trasporto ($\Delta T$)**: L'overhead additivo della catena reale oscilla tra **~0.16s e ~0.29s** per dispatch parallelo. Questo tempo riflette il costo combinato di:
   - Risoluzione token Keystone e parsing HTTP REST in IoTronic Conductor (~50–80 ms);
   - Inoltro WAMP RPC bidirezionale Conductor $\leftrightarrow$ Crossbar $\leftrightarrow$ Lightning-Rod (~100–180 ms);
   - Chiamata locale gRPC di loopback Plugin Python $\to$ Worker C++ (~1 ms).
2. **Ammortamento della Granularità (HPC Rule)**:
   - Su task a grana fine (batch=1000), il tempo di calcolo puro sul worker C++ è brevissimo (~29–54 ms); di conseguenza, l'overhead WAMP/REST domina la latenza totale, moltiplicando il tempo di esecuzione di 2.9x–7.5x e limitando il throughput a ~3k–4k sig/s.
   - Su task a grana più grossa (batch=5000), il tempo di calcolo puro (~125–285 ms) ammortizza significativamente l'overhead di coordinamento: l'overhead ratio scende a **1.34x–2.46x** e il throughput effettivo della catena reale scala positivamente da 7.942 sig/s (1 nodo) a 9.882 sig/s (2 nodi) fino al picco di **10.393 sig/s (3 nodi)**.

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
