import { ethers } from "hardhat";
import * as fs from "fs";
import * as path from "path";

async function main() {
    console.log("Owner simulation starting... waiting for deployment file...");
    
    // Simple retry loop to wait for deployment file
    let contract;
    const [admin, owner] = await ethers.getSigners();
    const deployFile = path.join(__dirname, "..", "deployments", "localhost.json");
    let contractAddress;
    
    while (true) {
        try {
            if (fs.existsSync(deployFile)) {
                const deployData = JSON.parse(fs.readFileSync(deployFile, "utf8"));
                contractAddress = deployData.address;
                
                contract = await ethers.getContractAt("OnboardingTrust", contractAddress);
                const code = await ethers.provider.getCode(contractAddress);
                if (code !== "0x") {
                    break; // Contract is deployed
                }
            }
        } catch (e) {
            // Ignore error
        }
        await new Promise(r => setTimeout(r, 2000));
    }

    console.log(`Contract found at ${contractAddress}. Listening for OnboardingRequested events...`);
    
    contract.on("OnboardingRequested", async (requestId, deviceId, requester, ownerAddress) => {
        if (ownerAddress === owner.address) {
            console.log(`[Event] OnboardingRequested: reqId=${requestId}, deviceId=${deviceId}. Approving...`);
            const tx = await contract.connect(owner).approve(requestId);
            await tx.wait();
            console.log(`Approved request ${requestId}`);
        }
    });

    // Keep alive
    await new Promise(() => {});
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
