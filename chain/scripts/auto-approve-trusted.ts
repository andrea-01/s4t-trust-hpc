import { ethers } from "hardhat";
import * as fs from "fs";
import * as path from "path";

interface TrustedStack {
    stackId: string;
    description?: string;
    deviceIdPrefixes: string[];
}

interface TrustedDevicesConfig {
    trustedStacks: TrustedStack[];
}

function loadConfig(): TrustedDevicesConfig {
    const configPath = process.env.TRUSTED_DEVICES_CONFIG
        || path.join(__dirname, "..", "config", "trusted-devices.json");

    if (!fs.existsSync(configPath)) {
        console.warn(
            `[auto-approve] Nessun file di config trovato in ${configPath}. ` +
            `Default-deny: nessuna richiesta verra' auto-approvata.`
        );
        return { trustedStacks: [] };
    }

    try {
        const raw = fs.readFileSync(configPath, "utf8");
        return JSON.parse(raw);
    } catch (err) {
        console.warn(
            `[auto-approve] Errore durante la lettura/parsing del config in ${configPath}: ${err}. ` +
            `Trattato come default-deny per questo ciclo.`
        );
        return { trustedStacks: [] };
    }
}

function matchTrustedStack(deviceId: string, config: TrustedDevicesConfig): string | null {
    for (const stack of config.trustedStacks) {
        for (const prefix of stack.deviceIdPrefixes) {
            if (deviceId.startsWith(prefix)) {
                return stack.stackId;
            }
        }
    }
    return null;
}

async function main() {
    console.log("Auto-approve service (default-deny) starting...");
    const [admin, owner] = await ethers.getSigners();

    const deployFile = path.join(__dirname, "..", "deployments", "localhost.json");
    let contract;
    let contractAddress;

    // Stesso pattern di attesa gia' usato in simulate-owner.ts / simulate-admin.ts
    while (true) {
        try {
            if (fs.existsSync(deployFile)) {
                const deployData = JSON.parse(fs.readFileSync(deployFile, "utf8"));
                contractAddress = deployData.address;
                contract = await ethers.getContractAt("OnboardingTrust", contractAddress);
                const code = await ethers.provider.getCode(contractAddress);
                if (code !== "0x") break;
            }
        } catch (e) {
            // Ignora, riprova
        }
        await new Promise(r => setTimeout(r, 2000));
    }

    console.log(`Contract found at ${contractAddress}. Loading trusted devices config...`);
    const initialConfig = loadConfig();
    console.log(`Initial trusted stacks (${initialConfig.trustedStacks.length}): ` +
        (initialConfig.trustedStacks.map(s => s.stackId).join(", ") || "(none)"));

    contract.on("OnboardingRequested", async (requestId, deviceId, requester, ownerAddress) => {
        // Reagisce solo alle richieste indirizzate all'owner simulato di questo servizio,
        // coerente con lo schema esistente (client-admin/client-owner condividono lo stesso
        // account #1 di Hardhat come owner di test).
        if (ownerAddress !== owner.address) {
            return;
        }

        const currentConfig = loadConfig();
        const stackId = matchTrustedStack(deviceId, currentConfig);

        if (!stackId) {
            console.log(
                `[Event] OnboardingRequested: reqId=${requestId}, deviceId=${deviceId}. ` +
                `NON presente in trusted-devices.json -> resta PENDING (default-deny). ` +
                `Richiede approvazione manuale dell'owner.`
            );
            return;
        }

        console.log(
            `[Event] OnboardingRequested: reqId=${requestId}, deviceId=${deviceId}. ` +
            `Match con lo stack fidato '${stackId}' -> approvazione automatica.`
        );

        try {
            const tx = await contract.connect(owner).approve(requestId);
            await tx.wait();
            console.log(`Approved request ${requestId} (stack: ${stackId})`);
        } catch (e: any) {
            // Caso noto: auto-onboard-workers.ts potrebbe aver gia' approvato questo stesso
            // device in modo sincrono all'avvio dello stack pipeline. Non e' un errore reale,
            // solo una corsa tra due meccanismi che coprono lo stesso device_id.
            const msg = String(e?.message || e).toLowerCase();
            if (msg.includes("request not pending")) {
                console.log(
                    `Request ${requestId} risultava gia' non piu' Pending ` +
                    `(probabilmente approvata da auto-onboard-workers.ts all'avvio). Ignorato.`
                );
            } else {
                console.error(`Errore approvando request ${requestId}:`, e);
            }
        }
    });

    console.log("Auto-approve service in ascolto sugli eventi OnboardingRequested...");
    await new Promise(() => {});
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});