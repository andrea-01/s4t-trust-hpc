import { ethers } from "hardhat";

const CONTRACT_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3";

async function main() {
    console.log("Owner simulation starting... waiting for admin to deploy...");
    
    // Simple retry loop to wait for contract deployment
    let contract;
    const [admin, owner] = await ethers.getSigners();
    
    while (true) {
        try {
            contract = await ethers.getContractAt("OnboardingTrust", CONTRACT_ADDRESS);
            const code = await ethers.provider.getCode(CONTRACT_ADDRESS);
            if (code !== "0x") {
                break; // Contract is deployed
            }
        } catch (e) {
            // Ignore error
        }
        await new Promise(r => setTimeout(r, 2000));
    }

    console.log("Contract found. Listening for OnboardingRequested events...");
    
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
