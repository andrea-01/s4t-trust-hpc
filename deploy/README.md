# Deploy

Questa cartella contiene i file Docker Compose per orchestrare ed eseguire l'intero ecosistema `s4t-trust-hpc` localmente.

L'architettura del progetto è suddivisa in stack logici gestiti da compose file separati, che mantengono l'isolamento dei componenti comunicando tramite reti Docker dedicate (in particolare `s4t-bridge`).

---

## 1. Stack Base (`docker-compose.yml`)

Questo stack contiene l'infrastruttura fondamentale di trust, onboarding e monitoraggio.

I container esposti sono:
- `hardhat-node`: Nodo blockchain locale Ethereum/Hardhat [porta 8545].
- `contract-deployer`: Script di deployment iniziale dei contratti (`OnboardingTrust.sol` e `LeasingRegistry.sol`).
- `owner-auto-approver`: Demone reattivo (sostituisce i vecchi script di simulazione manuale) che intercetta gli eventi `OnboardingRequested` e auto-approva on-chain i dispositivi che corrispondono all'allowlist definita in `chain/config/trusted-devices.json`.
- `gateway`: Proxy REST (FastAPI) [porta 8000].
- `mailpit`: SMTP catcher locale con interfaccia web per ispezionare le notifiche email [porta 8025 / SMTP 1025].
- `notification`: Demone Python indipendente per l'invio delle email ai proprietari dei device con tracciamento dello stato su file.
- `ui`: Dashboard web (FastAPI + Jinja2) [porta 8080].
- `auto-onboard`: Script di bootstrapping che registra e approva on-chain i worker standard (`worker-1`, `worker-2`, `worker-3`).

**Per avviare lo stack base:**
```bash
cp .env.example .env
docker compose up -d --build
```

---

## 2. Configurazione e Autenticazione (`.env`)

Il file `.env` (creato a partire da `.env.example`) definisce le configurazioni essenziali per la sicurezza e l'integrazione:
- **Autenticazione HTTP Basic**: `UI_ADMIN_USERNAME` e `UI_ADMIN_PASSWORD` proteggono l'accesso alla dashboard `ui/` e agli endpoint amministrativi del `gateway/` (`/trust/stacks`).
- **Custodia Chiavi**: `ADMIN_PRIVATE_KEY` per la firma delle transazioni blockchain dal gateway.
- **Credenziali Keystone**: parametri `OS_AUTH_URL`, `OS_USERNAME`, `OS_PASSWORD`, `OS_PROJECT_NAME` per consentire al satellite di autenticarsi con lo stack IoTronic.

---

## 3. Stack IoTronic Esterno (Prerequisito Pipeline)

A partire da M9.3, l'esecuzione HPC non chiama direttamente i container C++, ma passa attraverso l'infrastruttura di gestione IoTronic (Stack4Things). 
Lo stack IoTronic risiede nel repository sibling esterno `Stack4Things_DockerCompose_deployment` e crea la rete `stack4things_dockercompose_deployment_s4t`.

I container Lightning-Rod (board IoTronic) sono connessi sia alla rete `s4t` che alla rete `s4t-bridge`, con il plugin gRPC (`plugin_bundle.py`) iniettato.

**Avvio:**
```bash
cd ../Stack4Things_DockerCompose_deployment
docker compose up -d
```

---

## 4. Stack Pipeline (`docker-compose.pipeline.yml`)

Questo stack contiene i componenti per il calcolo distribuito:
- `satellite`: Orchestratore HPC (FastAPI) [porta 8001], connesso sia a `s4t-bridge` sia alla rete IoTronic `stack4things_dockercompose_deployment_s4t`.
- `worker-1`, `worker-2`, `worker-3`: Nodi di calcolo C++ con server gRPC (porta 50051) connessi a `s4t-bridge` e `pipeline-net`.

**Per avviare lo stack pipeline:**
```bash
docker compose -f docker-compose.pipeline.yml up -d --build
```

---

## 5. Stack Benchmark Distribuito (`docker-compose.benchmark.yml`)

Introdotto in M11.3 per i test di scalabilità orizzontale e analisi prestazionale:
- Espone fino a 8 nodi worker C++ indipendenti (`bench-worker-1` .. `bench-worker-8`) su rete isolata `bench-net`.
- Mappa le porte host da `50051` a `50058` per consentire l'esecuzione concorrente dei benchmark distribuiti (OpenMP intra-nodo + gRPC batch inter-nodo) orchestrati da script dedicati in `hpc-engine/benchmarks/`.

**Per avviare lo stack di benchmark:**
```bash
docker compose -f docker-compose.benchmark.yml up -d --build
```

---

## 6. Setup di Rete Condivisa (`s4t-bridge`)

Affinché i diversi stack possano comunicare in modo trasparente e sicuro, è necessario creare la rete esterna condivisa **una sola volta** sul demone Docker locale:

```bash
docker network create s4t-bridge
```
Se la rete non è presente, Docker rifiuterà l'avvio segnalando l'assenza della rete esterna dichiarata nei file Compose.
