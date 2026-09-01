# Stack4Things / IoTronic gRPC Plugin

Questo modulo contiene il plugin per l'agente di bordo **Lightning-Rod** di Stack4Things (IoTronic). Il plugin agisce come **client gRPC leggero** in esecuzione all'interno della board IoTronic, facendo da ponte tra le invocazioni del cloud (inviate dall'orchestratore `satellite` tramite IoTronic Conductor) e i nodi worker C++ ad alte prestazioni (`hpc-engine`).

---

## Architettura e File del Modulo

Poiché il framework IoTronic richiede che ogni plugin registrato sia distribuito come **singolo file Python monolitico**, il modulo adotta un processo di bundling:

- **`plugin_template.py`** *(sorgente versionato)*:
  - Definisce la classe `Worker(Plugin)` che estende la classe base di Lightning-Rod.
  - `_ensure_grpc_installed()`: Verifica la presenza di `grpcio` e `protobuf` nell'ambiente Python della board e, se assenti, ne effettua l'installazione dinamica a runtime in modo idempotente.
  - `_mount_stubs()`: Decodifica gli stub gRPC compressi in Base64 (iniettati dallo script di build), li estrae in `/tmp/pipeline_stubs` e li include in `sys.path`.
  - `run()`: Esegue la chiamata gRPC sincrona verso l'indirizzo del worker specificato nei parametri (`worker_addr`) e deposita il risultato formattato nella coda `self.q_result` (gestita dal WAMP agent di IoTronic).

- **`build_plugin.sh`** *(script di compilazione e bundling)*:
  - Genera gli stub Python (`pipeline_pb2.py` e `pipeline_pb2_grpc.py`) a partire dal file di definizione Protobuf `proto/pipeline.proto`, sfruttando il container `satellite`.
  - Applica una patch di compatibilità via `sed` per rimuovere il parametro `_registered_method=True` (non supportato dalle versioni di `grpcio` compatibili con Python 3.7 dell'immagine Lightning-Rod).
  - Comprime gli stub generati in un archivio zip e lo codifica in Base64.
  - Sostituisce il placeholder `###STUBS_ZIP_BASE64###` all'interno di `plugin_template.py`, generando l'artifact finale `plugin_bundle.py`.

- **`plugin_bundle.py`** *(artifact generato, escluso da git)*:
  - Singolo script Python autocontenuto pronto per essere registrato ed iniettato sulle board IoTronic.

- **`hello_world_test/`** *(riferimento storico M9.1)*:
  - Contiene lo script `plugin.py` minimale utilizzato durante la milestone M9.1 per verificare l'infrastruttura iniziale di iniezione ed esecuzione via WAMP/Crossbar prima dell'integrazione con gRPC.

- **`IOTRONIC_NOTES.md`**:
  - Raccolta di appunti tecnici, comandi CLI, dettagli sul protocollo WAMP e risoluzione di problemi noti (es. pulizia record stale in `wampagents`).

---

## Operazioni Supportate

Il plugin inoltra le richieste al server gRPC del worker C++, supportando le seguenti operazioni:

### 1. `INCREMENT_COUNTER`
- **Scopo**: Calcolo scalare sequenziale per la verifica dell'integrità della pipeline.
- **Parametri**:
  - `worker_addr`: Indirizzo di rete del worker C++ (es. `worker-1:50051`).
  - `input_value`: Intero da incrementare (default `10`).
- **Risposta**: `SUCCESS: Worker <node_id> incremented <input> -> <output>`

### 2. `VERIFY_SIGNATURES_BATCH`
- **Scopo**: Verifica crittografica distribuita ad alte prestazioni (firme ECDSA su curva NIST P-256) parallelizzata tramite OpenMP sul worker.
- **Parametri**:
  - `worker_addr`: Indirizzo di rete del worker C++ (es. `worker-1:50051`).
  - `batch_size`: Numero di firme da generare e verificare nel batch.
  - `num_threads`: Numero di thread OpenMP da utilizzare sul worker.
  - `seed`: Seme pseudo-casuale per la riproducibilità del dataset.
- **Risposta**: `SUCCESS: Worker <node_id> verified <valid>/<batch> signatures in <sec>s throughput=<ops/sec>`

---

## Compilazione e Registrazione su IoTronic

1. **Generare il bundle:**
   ```bash
   ./build_plugin.sh
   ```

2. **Creare il plugin su IoTronic Conductor:**
   ```bash
   iotronic plugin-create --callable grpc_client plugin_bundle.py
   ```

3. **Iniettare il plugin sulla board di destinazione:**
   ```bash
   iotronic plugin-inject <board_name> grpc_client
   ```

4. **Invocazione di test manuale (CLI):**
   ```bash
   iotronic plugin-action <board_name> grpc_client PluginCall \
     --params worker_addr=worker-1:50051,input_value=42
   ```
