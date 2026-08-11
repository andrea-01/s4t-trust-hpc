# Appunti di Integrazione: IoTronic e Lightning-Rod (M9.1)

Questo documento raccoglie le scoperte fatte durante il deploy dello stack Stack4Things (IoTronic) e l'analisi del meccanismo dei plugin, come richiesto dalla fase M9.1 del progetto.

## Deploy dello Stack IoTronic

Lo stack è stato deployato clonando il repository `Stack4Things_DockerCompose_deployment` come cartella sibling (allo stesso livello) rispetto alla root del mono-repo `s4t-trust-hpc`, secondo la convenzione stabilita (path relativo `../Stack4Things_DockerCompose_deployment`).

**Modifiche richieste al deploy:**
- Per rispettare la regola di **non patchare il codice upstream** (`docker-compose.yml`), il container `lightning-rod` falliva il pull dell'immagine a causa di un placeholder `docker.io/mdslab/lrod:compose@sha256:<resolved-image-digest>`.
- È stato creato un file `docker-compose.override.yml` locale che corregge l'immagine in `docker.io/mdslab/lrod:compose` permettendo allo stack di avviarsi correttamente.
- Il conflitto locale sulla porta `50094` (usata da `iotronic-wstun` che tenta di esporre `50001-50100` sull'host) è stato mitigato semplicemente riprovando il deploy una volta che la porta effimera dell'host si è liberata (essendo in uso dinamico per chiamate outbound). Nessun patching è stato necessario per le porte.

## Meccanismo dei Plugin (Lightning-Rod)

Dal codice analizzato (`iotronic-lightning-rod` repo, file `modules/plugin_manager.py` e gli esempi), il meccanismo di esecuzione remota del codice non è uno script bash/python grezzo, ma segue un preciso scaffold orientato agli oggetti:

- **Linguaggio Atteso**: Python 3.
- **Entrypoint**: Il plugin deve definire una classe `Worker` che eredita da `iotronic_lightningrod.modules.plugins.Plugin.Plugin`.
- **Esecuzione Sincrona vs Asincrona**:
  - **Sincrona (`PluginCall`)**: Il metodo `run()` viene eseguito e restituisce il risultato al chiamante inserendolo nella coda interna (`self.q_result.put(risultato)`).
  - **Asincrona (`PluginStart`)**: La classe lavora come un Thread (il manager fa `worker.start()`). Il plugin viene mantenuto attivo (anche al reboot se la flag `onboot` è attiva) fino a che non riceve un segnale di stop.
- **Parametri (Input)**: Passati come dizionario JSON tramite l'argomento `params` del costruttore.

## Analisi Comparativa: Scostamenti rispetto all'Outline

Come richiesto, ecco un confronto esplicito tra quanto rilevato ora e le ipotesi riportate in `docs/outline_progetto_s4t_hpc_blockchain.md` (§0 e §4.2):

### Rispetto al §0 (Grounding architettura S4T)
- **Ipotesi Outline**: "Lightning-Rod: agente Python lato dispositivo [...], esegue i plugin (codice Python) ricevuti dal Conductor".
- **Realtà (Confermata)**: L'architettura è esattamente quella descritta. I plugin vengono prima "iniettati" (salvati in `/var/lib/iotronic/plugins/`) e poi chiamati o avviati. L'onboarding manuale via UI → board-code → Crossbar si è dimostrato essere il flusso di default documentato nel README dello stack.

### Rispetto al §4.2 (Connessione HPC engine ↔ Stack4Things)
- **Ipotesi Outline (Opzione C)**: "Il plugin Lightning-Rod è un modulo Python installato sul device (secondo il meccanismo nativo IoTronic dei plugin), che funge da client gRPC verso l'HPC engine: riceve porzioni di codice/task dal satellite e li esegue localmente, restituendo risultati".
- **Realtà (Da tenere in considerazione)**: L'ipotesi architetturale è confermata ed è fattibile senza ostacoli. Il plugin *dovrà* essere una classe `Worker` che nel metodo `run()` implementa un client gRPC python (tramite le librerie standard `grpcio`) e apre una connessione verso il container del Worker C++.
- **Scostamenti identificati**: Nessun scostamento bloccante, ma l'implementazione pratica del plugin sarà strutturata come una classe Python estesa, non come uno script autonomo. Bisogna inoltre prestare attenzione alla dipendenza di `grpcio` sul device emulato: essendo l'emulatore Docker `lrod:compose` basato su un ambiente specifico, se la libreria gRPC non è pre-installata nell'immagine Docker nativa di Lightning-Rod, il plugin potrebbe fallire l'import. Nel caso, sarà necessario installarla dinamicamente al runtime (es. `subprocess.call(['pip', 'install', 'grpcio'])`) o creare un'immagine custom per M9.2.

## Esempio Plugin "Hello World"
È stato redatto un plugin minimale (in `/s4t-plugin/hello_world_test/plugin.py`) pronto all'iniezione non appena la board sarà confermata online (via onboarding manuale utente). Il plugin semplicemente legge eventuali parametri e restituisce una stringa di conferma, dimostrando l'operatività del `q_result`.
