# PROGRESS

## Sessione Attuale
**Data:** 2026-08-04
**Fase:** M3

### Task Completati
- [x] M0: Scaffolding repo e placeholder creati.
- [x] M1: Smart contract `OnboardingTrust.sol`, test Hardhat, script di simulazione client in Node.js e setup testnet in Docker Compose completati.

### Note e Troubleshooting (Fase M1)
- **Compatibilità Node.js / `ts-node`**: L'ultima versione di Node.js presente (v24.19) ha mostrato incompatibilità con l'integrazione nativa TypeScript di Hardhat (errore interno di `ts-node` legato alla lettura dei file di configurazione). Il problema è stato isolato e risolto effettuando il downgrade di `typescript` (4.9.5) e vincolando il progetto all'ambiente Node.js 22 (inserito limite `engines` in `package.json` e creato file `.nvmrc`).
- **Valutazione `npm audit`**: Eseguito `npm audit` in `chain/` che riporta 46 vulnerabilità (17 high), legate prevalentemente alle versioni di `hardhat` (2.22.x) e le sue dipendenze storiche (`undici`, `serialize-javascript`, ecc.). Poiché le librerie infette sono limitate all'ambiente di `devDependencies` locale usato solo per lo sviluppo e il deploy dello smart contract (nessun web server di produzione esposto) e tentare un `npm audit fix --force` introdurrebbe breaking changes passando a Hardhat 3.x (che riaprirebbe i problemi ESM/TypeScript), ho giudicato l'audit report **non bloccante** per questa fase.

## Fase: M2 (Gateway Python)

### Task Completati
- [x] 0. Eccezione su M1: Modificato `chain/` per avere uno script di deploy unico `deploy.ts` che salva l'indirizzo su volume condiviso, introdotto servizio `contract-deployer` in docker-compose.yml per fornire l'indirizzo ai client M1 e (successivamente) al gateway. (Commit: fix(chain): add dedicated deploy script and shared address file).
- [x] 1. Scaffold gateway project and dependencies (Commit: feat: scaffold gateway project and dependencies).
- [x] 2. Add chain_client for smart contract interaction (Commit: feat: add chain_client for smart contract interaction).
- [x] 3. Add event_poller for background event caching (Commit: feat: add event_poller for background event caching).
- [x] 4. Implement FastAPI endpoints (Commit: feat: implement FastAPI endpoints).
- [x] 5. Add integration tests for gateway against local hardhat node (Commit: test: add integration tests for gateway against local hardhat node).
- [x] 6. Create gateway Dockerfile (Commit: feat: create gateway Dockerfile).
- [x] 7. Integrate gateway into docker-compose (Commit: feat: integrate gateway into docker-compose).
- [x] 8. Update README with gateway instructions (Commit: docs: update README with gateway instructions).
- [x] Fix correttivi M2: Rimosso requester_key in favore di ADMIN_PRIVATE_KEY da env, aggiunta validazione owner_address, gestite eccezioni web3.py. (Commit: fix(gateway): remove private key from API surface, add input validation).

## Fase: M3 (Notifiche Email)

### Task Completati
- [x] 1. Scaffold modulo `notification/` e `owners.json` (Punti 1 e 2)
- [x] 2. Implementazione di `owners_registry.py` e `mailer.py` con test (Punti 3 e 5)
- [x] 3. Gestione Checkpoint Idempotenza (Punto 4)
- [x] 4. Implementazione di `chain_listener.py` e `main.py` (Punti 3 e 6)
- [x] 5. Integrazione Docker Compose e Mailpit con test integrazione (Punti 8, 9, 10, 7)

### Note (Fase M3)
- Abbiamo mantenuto la condivisione tramite volume degli artifact on-chain. Il checkpoint è persistito in un file su `state/`. Mailpit è stato configurato per essere avviato e gestito tramite compose.
- **Chain Reset Detection**: È stata aggiunta un'estensione non originariamente pianificata ma essenziale per la robustezza locale. Se il nodo locale Hardhat viene distrutto e ricreato (ad esempio tramite un restart distruttivo di docker-compose), la chain riparte dal blocco 0. Il listener Python ora se ne accorge confrontando il blocco corrente col suo checkpoint e si resetta a 0 per non bloccarsi aspettando blocchi futuri inesistenti, garantendo resilienza durante lo sviluppo.

### Domande Aperte
- Nessuna.
