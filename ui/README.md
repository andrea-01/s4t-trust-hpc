# Dashboard UI

Questo modulo implementa l'interfaccia web per l'amministrazione e il monitoraggio dell'ecosistema `s4t-trust-hpc`, sviluppata in Python con **FastAPI** e **Jinja2**.

La UI disaccoppia l'utente dall'interazione diretta con la blockchain o con le API REST, offrendo viste dedicate al monitoraggio delle richieste di onboarding e alla gestione degli stack fidati per l'auto-approvazione.

---

## Caratteristiche Principali

- **Rendering Lato Server**: Viste HTML generate dinamicamente tramite template Jinja2 (cartella `templates/`).
- **Aggiornamento Real-time (Polling)**: Script Vanilla JavaScript (`static/app.js`) per effettuare il polling asincrono in background verso il Gateway, aggiornando in tempo reale lo stato delle richieste di trust (`Pending`, `Approved`, `Rejected`, `Revoked`) senza ricaricare la pagina.
- **Autenticazione HTTP Basic**: L'accesso alla dashboard e a tutte le sue route è protetto da autenticazione HTTP Basic (FastAPI `HTTPBasic`). Le credenziali sono caricate da variabili d'ambiente (`UI_ADMIN_USERNAME`, `UI_ADMIN_PASSWORD`), senza valori di default insicuri nel codice.
- **Integrazione Esclusiva con Gateway**: La UI non parla mai direttamente con la blockchain, i database o i container worker. Tutte le letture e le mutazioni passano per il proxy REST `gateway/` tramite `app/gateway_client.py`.

---

## Viste Disponibili

### 1. Dashboard Onboarding (`/`)
- Mostra in tempo reale lo storico delle richieste di onboarding sulla blockchain.
- Include un form per inoltrare nuove richieste di onboarding specificando `device_id` e `owner_address`.
- Fornisce collegamenti rapidi a Mailpit (`http://localhost:8025`) per verificare la ricezione delle email di notifica.

### 2. Gestione Stack Fidati (`/trust`)
- Permette di visionare la configurazione attiva dell'allowlist di trust (`chain/config/trusted-devices.json`).
- Offre un'interfaccia protetta per aggiungere nuovi stack fidati specificando `stack_id`, descrizione e lista di prefissi `deviceId` ammessi (es. `worker-`).
- Consente la rimozione di stack fidati esistenti.
- Tutte le operazioni su questa vista invocano gli endpoint protetti `/trust/stacks` del Gateway con le credenziali Basic Auth configurate.

---

## Avvio e Utilizzo

La UI è parte integrante dello **Stack Base** in `deploy/docker-compose.yml`:

```bash
cd ../deploy
docker compose up -d
```

Una volta avviata, la dashboard è raggiungibile su:
- **URL**: [http://localhost:8080](http://localhost:8080)
- **Credenziali predefinite (in `.env.example`)**: `admin` / `adminpassword`

---

## Sviluppo Locale

Per avviare la UI in locale durante lo sviluppo (con il Gateway attivo su `http://localhost:8000`):

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configura le credenziali di test
export UI_ADMIN_USERNAME=admin
export UI_ADMIN_PASSWORD=adminpassword
export GATEWAY_URL=http://localhost:8000

uvicorn app.main:app --reload --port 8080
```

