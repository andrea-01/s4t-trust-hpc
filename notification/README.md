# S4T Trust HPC - Notification Module

Questo modulo si occupa di ascoltare gli eventi sulla blockchain (Hardhat) e inviare email di notifica agli owner (ruolo simulato).

## Caratteristiche
- **Poller Indipendente**: Si collega al nodo RPC e controlla nuovi blocchi in background.
- **Idempotenza**: Salva l'ultimo blocco processato nel volume `state/` (in `last_processed_block.txt`) per non reinviare notifiche ai riavvii.
- **Mailpit**: Usa Mailpit come server SMTP locale per catturare le email inviate senza bisogno di configurare provider esterni o credenziali reali.

## Avvio
In genere si avvia tramite docker compose dal livello root `deploy/`:

```bash
docker compose up -d
```

## Visualizzazione Email
Le email possono essere visualizzate tramite l'interfaccia web di Mailpit, disponibile all'indirizzo:
[http://localhost:8025](http://localhost:8025)

## Test
Per eseguire i test unitari e di integrazione (dalla directory di questo modulo):
```bash
pytest tests/
```
