# Onboarding automatizzato e HPC distribuito per Stack4Things — Outline & Piano implementativo

## 0. Grounding: come si inserisce il progetto nell'architettura reale di Stack4Things

Prima di strutturare l'outline, ho verificato l'architettura effettiva di Stack4Things/IoTronic (dal repo `Stack4Things_DockerCompose_deployment` e dai repo ufficiali IoTronic/Lightning-Rod), per evitare di proporre componenti incompatibili con lo stack reale:

- **IoTronic Conductor**: servizio cloud-side (stile OpenStack), espone API, gestisce DB (MariaDB), auth (Keystone), coda (RabbitMQ).
- **Crossbar**: router WAMP, canale di comunicazione realtime cloud↔device.
- **Lightning-Rod**: agente **Python** lato dispositivo (nelle versioni recenti; le vecchie erano Node.js), si connette a Crossbar via WSTUN/WAMP, esegue i **plugin** (codice Python) ricevuti dal Conductor.
- **IoTronic UI**: dashboard Horizon-like, oggi usata per creare/registrare le board manualmente (da qui il "code" da incollare sul Lightning-Rod).
- **Onboarding attuale**: creazione board da UI → copia board-code → incollato manualmente nell'interfaccia locale del Lightning-Rod → connessione a Crossbar.

Questo conferma due cose importanti per il tuo progetto:
1. Il punto di iniezione naturale per il livello HPC/parallelo è il **meccanismo dei plugin** di IoTronic (codice eseguito sul Lightning-Rod), oppure un **servizio satellite** che parla con Conductor/Lightning-Rod fuori banda (via gRPC) — sono due strade diverse, vedi §4.
2. L'onboarding "automatizzato" che vuoi realizzare sostituisce il passaggio manuale UI→board-code→incolla-su-device con un flusso **smart-contract-driven** (richiesta admin → notifica owner → consenso on-chain → provisioning automatico delle credenziali verso Crossbar).

---

## 0.bis Decisioni prese

| Bivio | Scelta |
|---|---|
| Topologia testnet (§4.1) | **Hardhat single-node** (spike veloce). Vedi nota di adattamento in §4.1 per restare comunque coerenti con "2-3 nodi containerizzati". |
| Integrazione HPC↔S4T (§4.2) | **Ibrida**: livello pipeline/leasing come servizio satellite, esecuzione come plugin Lightning-Rod |
| Struttura repo | **Mono-repo** con cartelle per modulo (struttura in §5.bis) |
| Interfaccia (Step 2) | **GUI web leggera** con Flask/FastAPI |

Le sezioni sottostanti sono aggiornate di conseguenza; le opzioni scartate restano visibili per riferimento/motivazione, marcate come tali.

---

## 1. Principi guida del progetto

- **Bottom-up e modulare**: ogni pezzo (smart contract, bridge gRPC, engine HPC, notifica) deve essere testabile e riusabile **indipendentemente** da Stack4Things.
- **Stack4Things come consumer, non come core**: il core del progetto è infrastruttura generica di trust/HPC; S4T è il primo caso d'uso/integrazione.
- **Containerizzato fin dal giorno 1**: ogni componente ha il suo Dockerfile; l'orchestrazione locale è docker-compose, quella "seria" è Kubernetes (manifests separati, stesso set di immagini).
- **Interfaccia minimale e separata**: niente UI dentro S4T; un'app Python standalone (dashboard leggera) che parla con i servizi via API/gRPC.
- **Linguaggi per componente** (dalla tua traccia):
  - Smart contract: Solidity + Hardhat
  - Server di gestione richieste blockchain: Python
  - Interfaccia: Python (separata da S4T)
  - Engine HPC/parallelizzazione: C/C++ (con gRPC verso il mondo Python)

---

## 2. Architettura a moduli (vista component-level)

```
┌─────────────────────────┐        ┌──────────────────────────┐
│   Interfaccia (Python)  │◄──────►│  Notification Service     │
│   minimale, standalone  │  API   │  (email/altro canale)     │
└────────────┬─────────────┘        └───────────┬──────────────┘
             │ REST/gRPC                         │ eventi on-chain
             ▼                                   ▼
┌─────────────────────────────────────────────────────────────┐
│        Blockchain Gateway (Python) — server richieste        │
│  - riceve richieste onboarding/consenso                      │
│  - traduce in tx verso smart contract                        │
│  - ascolta eventi (approval/revoke) e li ridistribuisce       │
└───────────┬───────────────────────────────────┬─────────────┘
            │ web3 / ethers                     │ gRPC
            ▼                                   ▼
┌───────────────────────────┐        ┌───────────────────────────────┐
│  Testnet privata (2-3      │        │   HPC Engine (C/C++)           │
│  nodi containerizzati,      │        │  - onboarding parallelo        │
│  Hardhat/Geth/Besu)         │        │  - deployment parallelo su     │
│  Smart contract Solidity    │        │    flotta board (token/lease)  │
└───────────────────────────┘        │  - espone servizi gRPC          │
                                       └───────────┬───────────────────┘
                                                    │ gRPC / plugin S4T
                                                    ▼
                                       ┌───────────────────────────────┐
                                       │   Stack4Things (IoTronic)      │
                                       │  Conductor + Crossbar +        │
                                       │  Lightning-Rod (flotta board)   │
                                       └───────────────────────────────┘
```

Ogni freccia = un'interfaccia da definire con un contratto esplicito (schema JSON per REST, `.proto` per gRPC, ABI per lo smart contract). Questo è ciò che rende i moduli riusabili anche fuori da S4T.

---

## 3. Fasi del progetto (dalla tua traccia, espanse)

### STEP 1 — Blockchain core + verifica compatibilità col server Python
**Obiettivo**: dimostrare che uno smart contract di autorizzazione/trust può essere scritto, deployato su una testnet multi-nodo containerizzata, e pilotato/osservato da un server Python.

Attività:
1. Definire lo **schema dati on-chain minimo**: richiesta onboarding (device_id, requester, owner, stato), evento di approvazione/rifiuto, evento di revoca/scadenza.
2. Scrivere smart contract Solidity (Hardhat) con funzioni: `requestOnboarding()`, `approve()`, `reject()`, `revoke()`, eventi corrispondenti.
3. Containerizzare una **testnet locale a 2-3 nodi** (vedi opzioni in §4.1).
4. Server Python (es. FastAPI + `web3.py`) che:
   - invia transazioni (richiesta/approvazione)
   - ascolta eventi via filtro/websocket
   - espone REST minime per essere richiamato dall'interfaccia
5. Test di compatibilità: round-trip completo richiesta→evento→lettura stato dal server Python.

**Deliverable**: repo `s4t-trust-chain` con contratto, test Hardhat, docker-compose per la testnet, server Python con test d'integrazione.

### STEP 2 — Interfaccia separata (Python)
**Obiettivo**: piccola dashboard che permette all'admin di richiedere onboarding e vedere lo stato, senza essere parte di S4T.

**→ Decisione presa**: GUI web leggera con **FastAPI** (backend, coerente col resto dei servizi Python del progetto che useranno già FastAPI/web3.py) + template server-side minimali (Jinja2) o una SPA leggerissima — niente framework frontend pesante, per restare "minimale".

Attività:
1. Backend FastAPI con routing verso le API del gateway blockchain (Step 1/M2): no accesso diretto alla blockchain dall'interfaccia, sempre mediato dal gateway.
2. Vista "richieste pendenti / approvate / revocate" (tabella semplice, polling o WebSocket per aggiornamenti realtime).
3. Autenticazione minima admin (anche solo basic auth in questa fase, da irrobustire in M10).

**Deliverable**: servizio FastAPI containerizzato, cartella `ui/` nel mono-repo, che parla solo via HTTP col gateway (`gateway/`).

### STEP 3 — HPC engine (C/C++), prima versione alpha *senza* smart contract
**Obiettivo**: isolare e validare la logica di parallelizzazione prima di collegarla alla blockchain, per capire bene il modello prima di irrigidirlo con la parte on-chain.

#### 3.1 — Parallelizzazione dati in fase di onboarding
- Scenario guida: 500 dispositivi da fare onboarding, verifica firme/credenziali in parallelo.
- Batching + parallelizzazione **intra-nodo** (thread pool, es. `std::thread`/`std::async` o thread pool custom) per verifica firme crittografiche.
- Output: throughput misurato (onboarding/sec) al variare del numero di thread e della dimensione del batch.

#### 3.2 — Parallelizzazione dei processi nel deployment su flotta board
- Due livelli concettuali, come li hai definiti tu:
  - **Livello applicativo (pipeline building)**: ottenere controllo on-demand dei dispositivi (leasing "scritto sulla blockchain" nella versione finale), onboarding automatizzato dei nodi nella pipeline.
  - **Livello di parallel processing (uso della pipeline)**: iniezione di porzioni di codice su nodi separati, esecuzione distribuita, raccolta risultati (es. il contatore incrementale distribuito che hai descritto come esempio).
- In questa fase (alpha, senza blockchain) il "leasing" può essere **simulato** con uno stato locale (es. una tabella in memoria/DB che finge il ruolo dello smart contract), per validare la logica di pipeline prima di aggiungere la complessità on-chain.

**Deliverable**: libreria/servizio C++ standalone (con binding CLI o gRPC di test) che dimostra: (a) verifica firme in parallelo su un batch simulato di N device, (b) costruzione ed esecuzione di una pipeline multi-nodo con un caso d'uso demo (counter distribuito).

### STEP 4 — Parallelizzazione: OpenMPI vs implementazione ex-novo
Decisione esplicitamente etichettata come "eventuale" nella tua traccia → vedi opzioni dettagliate in §4.3. Da prendere **dopo** aver visto i risultati dello Step 3, perché la scelta dipende dal modello di comunicazione emerso (fan-out semplice vs vera comunicazione inter-processo stile MPI).

### Integrazione finale
- Sostituire la simulazione di leasing dello Step 3.2 con le vere transazioni/eventi dello Step 1.
- Collegare l'HPC engine (C++) a Stack4Things tramite gRPC (vedi §4.2) e/o come plugin IoTronic.
- Collegare l'interfaccia (Step 2) come pannello unico su tutto il flusso.

---

## 4. Bivi architetturali da decidere esplicitamente (proposte multiple)

### 4.1 Topologia della testnet blockchain (2-3 nodi containerizzati)
La rete di sviluppo standard di Hardhat (`npx hardhat node`) è **single-node** e non replica bene uno scenario multi-nodo/multi-consenso. Per avere davvero 2-3 nodi containerizzati hai tre strade:

- **A. Hardhat single-node + più "client" che vi si connettono**: più semplice, più veloce da montare, ma **non è realmente multi-nodo** (nessun consenso distribuito reale). Va bene se l'obiettivo è solo "verificare la compatibilità col server Python", meno se vuoi dimostrare tolleranza a guasti/decentralizzazione.
- **B. Rete Ethereum privata multi-nodo con Geth in modalità Clique (PoA)**: 2-3 nodi Geth containerizzati, consenso Proof-of-Authority reale, Hardhat resta usato solo per compilare/deployare il contratto (puntando alla rete Geth invece che al suo nodo interno). Più fedele a un vero scenario multi-nodo, leggermente più complesso da orchestrare.
- **C. Hyperledger Besu con IBFT2.0**: pensato apposta per consorzi containerizzati multi-nodo, tooling di rete più maturo di Geth-Clique per questo scenario, ma introduce un secondo ecosistema (Besu invece di restare 100% nel mondo Hardhat/Geth).

**La mia raccomandazione di default** sarebbe stata l'opzione B, ma è stata scelta l'opzione **A (Hardhat single-node)** per velocità di spike.

**→ Decisione presa: A, con un adattamento per restare fedeli a "2-3 nodi containerizzati"**: dato che un singolo `npx hardhat node` non fa vero consenso distribuito, per non snaturare la traccia containerizziamo comunque **3 container separati**:
- 1 container con il nodo Hardhat (JSON-RPC su una porta interna alla rete Docker).
- 2 container "client" (es. script Python/web3.py o semplici processi Node) che si connettono allo stesso endpoint RPC e simulano ruoli diversi (es. "nodo admin" e "nodo owner"), utili anche più avanti per i test M2 (gateway) e per il modulo notifica.

Questo dà comunque una topologia a 3 container su rete Docker dedicata, utile per validare la comunicazione (obiettivo dichiarato dello Step 1: "verificare la compatibilità con un server Python"), rimandando un vero consenso multi-nodo (opzione B/C) a un'eventuale fase successiva se il progetto lo richiederà esplicitamente (es. in ottica di robustezza/decentralizzazione reale).

### 4.2 Dove si collega l'HPC engine C++ a Stack4Things
- **A. Servizio satellite indipendente**: l'engine C++ espone gRPC, un piccolo servizio Python (client gRPC) fa da "traduttore" e chiama le API/plugin di IoTronic dall'esterno. Nessuna modifica al codice di IoTronic. Più pulito per la modularità che vuoi, più lento nel loop di feedback con il device (passa sempre da Conductor/Crossbar).
- **B. Plugin IoTronic**: il codice che gira su Lightning-Rod (Python) diventa un client leggero che parla in gRPC con l'engine C++ (che può girare come sidecar sullo stesso host/board o centralizzato). Più integrato nel modello nativo di S4T (i plugin sono il meccanismo ufficiale di esecuzione remota), ma accoppia di più il progetto al ciclo di vita dei plugin IoTronic.
- **C. Ibrida**: livello applicativo (leasing/pipeline building) come servizio satellite (A), livello di parallel processing iniettato come plugin (B) sui singoli nodi. Coerente con la separazione a due livelli che hai già descritto tu stesso (gestione pipeline vs uso pipeline).

**→ Decisione presa: C (ibrida)**, confermata: rispecchia la tua descrizione a due livelli e mantiene la modularità (il "livello applicativo" resta riusabile anche senza S4T).

Implicazioni concrete per il codice:
- Il **servizio satellite** (livello pipeline/leasing) è un processo Python/C++ che sta *fuori* da IoTronic, parla in gRPC con l'HPC engine e in REST/gRPC con il gateway blockchain (M2) e l'interfaccia (M4).
- Il **plugin Lightning-Rod** è un modulo Python installato sul device (secondo il meccanismo nativo IoTronic dei plugin), che funge da client gRPC verso l'HPC engine: riceve "porzioni di codice"/task dal satellite e li esegue localmente, restituendo risultati (es. incremento del counter distribuito).
- Il confine gRPC tra satellite e plugin va definito con un `.proto` dedicato fin da M6, per evitare refactoring quando si collega S4T reale in M9.

### 4.3 Modello di parallelizzazione (Step 4)
- **A. OpenMPI**: standard de-facto per HPC, comunicazione inter-processo robusta e testata, ma pensato per cluster omogenei/controllati — si adatta meno bene a un contesto IoT con nodi eterogenei, NAT, on/off-boarding dinamico e "ownership" parziale dei device (che è invece lo scenario reale di S4T).
- **B. Framework custom leggero (thread pool intra-nodo + gRPC/streaming inter-nodo)**: più lavoro di sviluppo, ma modellabile esattamente sul concetto di "pipeline a nodi on-demand" che hai descritto (aggiunta/rimozione dinamica di nodi, token incrementale, gestione ownership) — cosa che MPI non gestisce nativamente (MPI assume un mondo statico definito a lancio, con `mpirun`/hostfile).
- **C. Ibrida**: usare OpenMPI *solo* come motore di calcolo puro all'interno di un sottoinsieme di nodi già "acquisiti" per una sessione (dove l'insieme è temporaneamente statico), mentre il layer di acquisizione/rilascio dinamico dei nodi resta custom (gRPC).

**Raccomandazione di default**: partire da **B**, e valutare **C** solo se emerge un reale bisogno di collettive MPI (broadcast, reduce) più sofisticate di un semplice fan-out/fan-in.

---

## 5.bis Struttura del mono-repo

```
s4t-trust-hpc/
├── chain/                 # Step 1 — smart contract
│   ├── contracts/          # Solidity (Hardhat)
│   ├── test/                # Test Hardhat
│   ├── scripts/             # Deploy script
│   ├── hardhat.config.js
│   └── Dockerfile           # container nodo Hardhat
├── gateway/                # Step 1 — server Python (web3.py, FastAPI)
│   ├── app/
│   ├── tests/
│   └── Dockerfile
├── notification/           # Modulo notifica (email/altro canale)
│   ├── app/
│   └── Dockerfile
├── ui/                     # Step 2 — interfaccia FastAPI
│   ├── app/
│   ├── templates/
│   └── Dockerfile
├── hpc-engine/             # Step 3/4 — C/C++
│   ├── src/
│   │   ├── onboarding/       # 3.1 parallelizzazione dati
│   │   └── pipeline/         # 3.2 pipeline multi-nodo
│   ├── proto/               # .proto condivisi gRPC (satellite <-> plugin <-> gateway)
│   ├── CMakeLists.txt
│   └── Dockerfile
├── satellite/              # Livello applicativo (pipeline/leasing), Python o C++
│   ├── app/
│   └── Dockerfile
├── s4t-plugin/              # Plugin Lightning-Rod (client gRPC verso hpc-engine)
│   └── plugin/
├── deploy/
│   ├── docker-compose.yml   # sviluppo locale, tutti i servizi + fork del compose S4T
│   └── k8s/                 # manifests Kubernetes (fase M10)
└── docs/
    └── outline_progetto_s4t_hpc_blockchain.md   # questo documento
```

Nota: `hpc-engine` e `satellite` restano import/dipendenze pulite via `.proto`, così sono riusabili anche fuori da questo mono-repo se in futuro servisse estrarli.

---

## 5. Piano implementativo passo-passo (ordine consigliato, con milestone)

> Ogni milestone è pensata per essere dimostrabile in isolamento (demo standalone), coerente con l'approccio bottom-up.

**M0 — Setup ambiente**
- Fork/estensione del repo `Stack4Things_DockerCompose_deployment` come base di partenza per l'ambiente S4T.
- Repo separato per il progetto (mono-repo con cartelle `chain/`, `gateway/`, `hpc-engine/`, `ui/`, `notification/`, oppure poli-repo — da decidere, vedi domande finali).
- Definizione della rete Docker/K8s condivisa (namespace unico, service discovery via DNS interno).

**M1 — Smart contract + testnet multi-nodo (Step 1, parte on-chain)**
- Contratto Solidity con test Hardhat completi (unit test su `approve/reject/revoke`).
- Docker-compose per topologia scelta in §4.1.
- Criterio di uscita: deploy riuscito su rete multi-nodo, transazione end-to-end verificata da script di test.

**M2 — Gateway Python ↔ blockchain (Step 1, parte server)**
- Server Python (`web3.py`) con REST minime: `POST /onboarding-request`, `GET /status/{id}`, webhook/listener per eventi.
- Criterio di uscita: test d'integrazione automatico chain↔server verde in CI.

**M3 — Notifica**
- Modulo notifica (email via SMTP/servizio terzo, o alternativa) agganciato agli eventi del gateway.
- Criterio di uscita: evento on-chain → email ricevuta, in un ambiente containerizzato.

**M4 — Interfaccia Python minimale (Step 2)**
- Consumo delle API di M2, vista richieste/stati.
- Criterio di uscita: un admin può, da interfaccia, generare una richiesta e vederne l'esito dopo l'azione dell'owner (simulata via script per ora).

**M5 — HPC engine alpha, no blockchain (Step 3.1)**
- Libreria C++ per batching + verifica firme in parallelo (thread pool).
- Benchmark su dataset simulato (es. 500 "device" fittizi) con firme sintetiche.
- Criterio di uscita: grafico throughput vs. numero di thread/batch size.

**M6 — HPC engine alpha, pipeline multi-nodo (Step 3.2)**
- Livello applicativo: leasing simulato (in-memory) di un pool di nodi containerizzati fittizi.
- Livello parallel processing: demo del "counter distribuito" (o applicazione equivalente) su questi nodi simulati.
- gRPC come collante tra i due livelli fin da qui (anche prima di collegarsi a S4T), per non dover ridisegnare l'interfaccia dopo.
- Criterio di uscita: demo end-to-end su nodi containerizzati locali (senza ancora board reali/virtuali S4T).

**M7 — Decisione e implementazione parallelizzazione avanzata (Step 4)**
- Solo se M6 mostra la necessità di collettive più ricche (vedi §4.3).

**M8 — Integrazione con blockchain reale**
- Sostituzione del leasing simulato (M6) con le vere chiamate al gateway M2 (possesso on-demand scritto su chain).

**M9 — Integrazione con Stack4Things reale**
- Collegamento a Lightning-Rod/Conductor secondo l'opzione scelta in §4.2 (probabilmente C: satellite + plugin).
- Demo finale sullo scenario "azienda con 500 dispositivi": onboarding batch, verifica firme in parallelo, deployment pipeline, esempio counter distribuito.

**M10 — Hardening**
- Gestione revoca/scadenza permessi end-to-end (propagazione disconnessione sicura, come da proposta originale).
- Manifests Kubernetes definitivi (accanto/al posto del docker-compose).
- Documentazione per riuso dei moduli fuori da S4T.

---

## 6. Rischi principali e mitigazioni

| Rischio | Mitigazione |
|---|---|
| Complessità della rete blockchain multi-nodo rallenta lo Step 1 | Partire con opzione A (§4.1) come spike veloce, poi migrare a B se serve realismo |
| Accoppiamento troppo stretto tra HPC engine e S4T rende il codice non riusabile | Tenere sempre un confine gRPC/`.proto` netto; testare l'HPC engine anche senza S4T (M5-M6) |
| MPI non si adatta al modello "on-demand ownership" | Validare con demo M6 prima di investire in Step 4; non implementare MPI "a priori" |
| Notifiche (email) come single point of failure per il consenso owner | Prevedere fin da subito un'interfaccia di fallback (polling da UI) oltre alla notifica push |
| Scope troppo ampio per i tempi disponibili | Le milestone M0-M6 sono già una tesi/progetto completo e dimostrabile anche senza M7-M10 |

---

## 7. Stato delle decisioni e prossimo passo operativo

Tutti e 4 i bivi architetturali sono stati chiusi (vedi §0.bis). Il piano è quindi pronto per partire da **M0**.

**Prossimo passo concreto suggerito**: creare lo scheletro del mono-repo (struttura §5.bis) e partire da **M1** (`chain/`):
1. `hardhat init` in `chain/`, primo smart contract con le 4 funzioni (`requestOnboarding`, `approve`, `reject`, `revoke`) ed eventi corrispondenti.
2. Dockerfile per il nodo Hardhat + i due container "client" di simulazione (vedi nota adattamento in §4.1).
3. Test Hardhat (`chain/test/`) per il ciclo completo richiesta→approvazione→evento.

Se vuoi, posso procedere a generare direttamente lo scheletro di file/cartelle del mono-repo (incluso il primo smart contract Solidity e il relativo `docker-compose` per i 3 container), oppure preferisci rivedere prima qualche punto dell'outline.