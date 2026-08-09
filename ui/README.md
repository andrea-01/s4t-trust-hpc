# Dashboard UI

Questo modulo implementa un'interfaccia web minimale sviluppata in Python (FastAPI + Jinja2). 
La sua funzione è quella di fornire una dashboard per interagire con il Gateway: permette di visionare in tempo reale le richieste di onboarding e di crearne di nuove, disaccoppiando l'utente finale dalle chiamate API dirette e mascherando la complessità della blockchain sottostante.

## Caratteristiche
- **Rendering Lato Server**: Le viste HTML sono generate dal server tramite i template Jinja2 (nella cartella `templates/`).
- **Aggiornamento Real-time (Polling)**: La UI utilizza Vanilla JavaScript (`static/app.js`) per effettuare il polling asincrono in background verso il Gateway, aggiornando dinamicamente la tabella degli stati (Pending, Approved, Rejected, Revoked) senza necessità di ricaricare la pagina.
- **Nessuna Autenticazione**: In questa fase (M4+), la UI è puramente orientata allo sviluppo/dimostrazione, e non presenta livelli di autenticazione o gestione sessioni (previsti per M10).
- **Integrazione Gateway**: Interagisce esclusivamente via REST API verso il servizio `gateway`. Non comunica in modo diretto con il database, la blockchain o il demone notifiche (Mailpit).

## Avvio
La UI è integrata nel file compose principale (Stack Base). Si avvia insieme al resto dell'infrastruttura di onboarding:

```bash
cd ../deploy
docker compose up -d
```

Una volta avviata, la dashboard è visitabile all'indirizzo [http://localhost:8080](http://localhost:8080).

## Sviluppo Locale
Se si desidera eseguire la UI isolata per lo sviluppo (assumendo che il gateway sia in esecuzione sulla porta 8000):

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```
