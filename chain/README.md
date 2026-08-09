# Chain - Smart Contracts

Questo modulo contiene l'infrastruttura blockchain del progetto, sviluppata utilizzando il framework **Hardhat** e **TypeScript**.

## Smart Contracts

Gli smart contract sono situati nella cartella `contracts/`:
- **`OnboardingTrust.sol`**: Gestisce il ciclo di vita dell'onboarding dei dispositivi IoT (richiesta, approvazione, rifiuto, revoca). È la base di tutto il sistema di trust.
- **`LeasingRegistry.sol`**: Gestisce il leasing on-chain dei nodi worker per il calcolo distribuito (HPC). È subordinato allo stato `Approved` del contratto `OnboardingTrust.sol`.

## Architettura e Esecuzione

In ambiente di test e sviluppo, la rete blockchain locale è fornita dal nodo Hardhat containerizzato (vedi `Dockerfile` e la directory `deploy/`). Non viene utilizzato Geth o Besu in questa fase.

### Deployments
L'output della compilazione (Artifacts) e gli indirizzi dei contratti deployati vengono scritti in `deployments/`. Questi file (`localhost.json` per OnboardingTrust, `leasing-localhost.json` per LeasingRegistry) sono letti dal Gateway per connettersi agli smart contract corretti al riavvio.

## Sviluppo e Testing Locale

Per testare e compilare i contratti logicamente fuori dall'ambiente Docker:

1. Installa Node.js v22 (come da `.nvmrc`) e le dipendenze:
   ```bash
   nvm use
   npm install
   ```

2. Compila i contratti e genera i typechain:
   ```bash
   npx hardhat compile
   ```

3. Esegui la suite di test completa (Onboarding e Leasing):
   ```bash
   npx hardhat test
   ```

*Nota: non modificare `OnboardingTrust.sol` o le logiche base stabilite nella fase M1, in quanto altri moduli dipendono dai suoi eventi in modo retrocompatibile.*
