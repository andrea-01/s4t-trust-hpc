# Satellite - HPC & IoT Orchestrator

Questo modulo agisce come orchestratore per il livello di calcolo distribuito (HPC Pipeline). Sviluppato in Python (FastAPI), si occupa di ricevere le richieste di allocazione dei task, coordinare il leasing dei nodi on-chain e orchestrare l'esecuzione remota delegandola alle board IoTronic (Stack4Things) tramite REST, le quali invocano localmente i worker C++ via gRPC.

## Funzionalità Principali
- **Pool di Nodi Dinamico (M12)**: Elimina l'elenco statico di nodi. Ad ogni richiesta di lease (`POST /pipeline/lease`), interroga dinamicamente IoTronic (`GET /v1/boards`) per ottenere l'elenco delle board attualmente `online`.
- **Selezione con Fallback On-Chain**: Itera sui candidati online tentando il lease on-chain tramite il `gateway` (`POST /leasing/lease`). Se un candidato risulta non approvato on-chain (o già occupato), il satellite passa automaticamente al candidato successivo senza far fallire la richiesta, garantendo tolleranza verso nodi non registrati o non approvati. La richiesta fallisce (HTTP 400 con rollback) solo se i nodi validi disponibili sono inferiori al conteggio richiesto.
- **Supporto Trasparente a Nuovi Dispositivi**: Qualunque board registrata su IoTronic e marcata `online`, una volta approvata on-chain (es. tramite allowlist o approvazione dinamica), diventa immediatamente leasable ed eseguibile dal satellite senza alcun riavvio o riconfigurazione.
- **Client IoTronic REST (`iotronic_client.py`)**: Interagisce con Keystone (autenticazione token `POST /v3/auth/tokens`) e IoTronic Conductor (`GET /v1/boards`, `POST /v1/boards/{board}/plugins/{plugin}` con azione `PluginCall`) per gestire la scoperta dei nodi e l'invio dei task di calcolo in modo sincrono e sicuro.
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

### Tabella Comparativa Multi-Run (Campagna a 6 Ripetizioni con Deviazione Standard)

| Batch Size | Nodi | $T_{\text{isolato}}$ (avg) | $T_{\text{reale}}$ (avg $\pm$ std) | $T_{\text{worker}}$ puro | Overhead $\Delta T$ | Overhead Ratio | Throughput Isolato | Throughput Reale |
|:----------:|:----:|:--------------------------:|:----------------------------------:|:------------------------:|:-------------------:|:--------------:|:------------------:|:----------------:|
| 1.000      | 1    | 0.1024 s                   | 0.2791 s $\pm$ 0.055 s             | 0.0542 s                 | +0.1766 s           | **2.72x**      | 9.787,6 sig/s      | 3.681,1 sig/s    |
| 1.000      | 2    | 0.0602 s                   | 0.2540 s $\pm$ 0.024 s             | 0.0286 s                 | +0.1938 s           | **4.22x**      | 16.633,8 sig/s     | 3.968,1 sig/s    |
| 1.000      | 3    | 0.0480 s                   | 0.2726 s $\pm$ 0.028 s             | 0.0207 s                 | +0.2246 s           | **5.68x**      | 21.287,1 sig/s     | 3.702,1 sig/s    |
| 5.000      | 1    | 0.5064 s                   | 0.6494 s $\pm$ 0.038 s             | 0.2729 s                 | +0.1431 s           | **1.28x**      | 10.023,0 sig/s     | 7.720,5 sig/s    |
| 5.000      | 2    | 0.2481 s                   | 0.4748 s $\pm$ 0.030 s             | 0.1420 s                 | +0.2267 s           | **1.91x**      | 20.156,9 sig/s     | 10.565,0 sig/s   |
| 5.000      | 3    | 0.1739 s                   | 0.4427 s $\pm$ 0.013 s             | 0.1023 s                 | +0.2688 s           | **2.55x**      | 28.780,3 sig/s     | **11.303,5 sig/s** |

### Analisi Tecnica dell'Overhead & Interpretazione dei Dati

1. **Decomposizione dell'Overhead Fisso ($\Delta T \approx 0.14\text{s} - 0.27\text{s}$)**:
   L'overhead additivo introdotto dalla catena di orchestrazione distribuita è quantificabile in circa **140–270 ms** per operazione di dispatch concorrente. Questa latenza riflette:
   - Validazione token Keystone e gestione richiesta HTTP REST sincrona su IoTronic Conductor (~40–70 ms);
   - Routing WAMP RPC bidirezionale Conductor $\leftrightarrow$ Crossbar Router $\leftrightarrow$ Agente Lightning-Rod (~90–190 ms);
   - Chiamata locale gRPC di loopback Plugin Python $\to$ Worker C++ su `s4t-bridge` (~1 ms).

2. **Dinamica a Grana Fine (Batch = 1.000) e Straggler Tail Effect**:
   - Sul batch da 1.000 firme, il calcolo puro sul worker C++ si riduce regolarmente all'aumentare dei nodi ($54.2\text{ ms} \to 28.6\text{ ms} \to 20.7\text{ ms}$, con speedup interno di $1.90\times$ e $2.62\times$).
   - Tuttavia, il tempo end-to-end reale rimane piatto attorno a **~0.25s–0.28s** (throughput oscillante tra 3.681 e 3.968 sig/s). Poiché il tempo totale del dispatch parallelo è $T = \max(R_1, \dots, R_N)$ sui roundtrip dei singoli nodi, e ciascun canale WAMP/REST ha una variabilità fisiologica ($\sigma \approx 25-50\text{ ms}$), il modesto risparmio computazionale di 8 ms tra 2 e 3 nodi viene statisticamente assorbito dalla latenza di coda (*straggler tail latency*) del nodo più lento nel pool.

3. **Ammortamento a Grana Grossa (Batch = 5.000) e Scalabilità Reale**:
   - Sul batch da 5.000 firme, il carico di calcolo utile per nodo ($272.9\text{ ms} \to 142.0\text{ ms} \to 102.3\text{ ms}$) supera ampiamente la varianza stocastica del trasporto WAMP.
   - Il tempo end-to-end decresce in modo strettamente monotono ($0.649\text{s} \to 0.475\text{s} \to 0.443\text{s}$), con deviazione standard contenuta (da $\pm 38\text{ms}$ a soli $\pm 13\text{ms}$ a 3 nodi).
   - L'overhead ratio scende a **1.28x–2.55x** rispetto al dispatch gRPC diretto, e la catena reale raggiunge il suo massimo throughput aggregato di **11.303,5 sig/s (picco di 12.652,4 sig/s su singola run)**.

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
