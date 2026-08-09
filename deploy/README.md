# Deploy

Questa cartella contiene i file Docker Compose per orchestrare ed eseguire l'intero ecosistema `s4t-trust-hpc` localmente.

L'architettura del progetto è suddivisa in due stack logici, gestiti da due compose file separati, che mantengono l'isolamento dei componenti ma possono comunicare tramite una rete condivisa (`s4t-bridge`).

## 1. Stack Base (`docker-compose.yml`)
Questo stack contiene l'infrastruttura fondamentale di trust e onboarding.
I container esposti sono:
- `hardhat-node`: Nodo blockchain locale.
- `gateway`: Proxy REST (FastAPI) [porta 8000].
- `notification`: Demone invio mail (background) e Mailpit SMTP catcher [porta 8025].
- `ui`: Dashboard utente (FastAPI) [porta 8080].
- `client-admin` / `client-owner`: Script effimeri utilizzati per test e simulazioni iniziali, eseguiti in batch.

**Per avviare lo stack base:**
```bash
docker compose up -d --build
```

## 2. Stack Pipeline (`docker-compose.pipeline.yml`)
Questo stack contiene l'infrastruttura per il calcolo distribuito (HPC).
I container esposti sono:
- `satellite`: Orchestratore HPC (FastAPI) [porta 8001].
- `worker-1`, `worker-2`, `worker-3`: Nodi C++ che eseguono le computazioni parallele e offrono l'interfaccia gRPC.
- `auto-onboard`: Script effimero che, all'avvio, contatta il `gateway` per registrare e approvare i worker on-chain in automatico.

**Per avviare lo stack pipeline:**
```bash
docker compose -f docker-compose.pipeline.yml up -d --build
```

## Setup di Rete (Importante)
Affinché lo stack pipeline (`satellite`, `auto-onboard`) possa comunicare in modo sicuro con lo stack base (`gateway`), è necessario creare la rete esterna condivisa **una sola volta** sul proprio demone Docker prima di avviare gli stack:

```bash
docker network create s4t-bridge
```

Se la rete non è creata, il demone Docker rifiuterà l'avvio lamentando l'assenza della rete esterna definita nei compose.
