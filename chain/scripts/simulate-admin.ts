import { ethers } from "hardhat";
import * as fs from "fs";
import * as path from "path";

async function main() {
    console.log("Admin simulation starting...");
    const [admin, owner] = await ethers.getSigners();
    
    // Read contract address from deployments
    const deployFile = path.join(__dirname, "..", "deployments", "localhost.json");
    if (!fs.existsSync(deployFile)) {
        throw new Error(`Deployment file not found at ${deployFile}. Ensure deploy.ts is run first.`);
    }
    const deployData = JSON.parse(fs.readFileSync(deployFile, "utf8"));
    const address = deployData.address;
    
    const contract = await ethers.getContractAt("OnboardingTrust", address);
    console.log(`Connected to contract at: ${address}`);
    
    // Listen for events before requesting so we don't miss them
    contract.on("OnboardingApproved", (requestId, deviceId, ownerAddress) => {
        console.log(`[Event] OnboardingApproved: reqId=${requestId}, deviceId=${deviceId}, owner=${ownerAddress}`);
    });
    
    contract.on("OnboardingRejected", (requestId, deviceId, ownerAddress) => {
        console.log(`[Event] OnboardingRejected: reqId=${requestId}, deviceId=${deviceId}, owner=${ownerAddress}`);
    });

    // Request onboarding
    console.log("Requesting onboarding for dev-sim-01...");
    const tx = await contract.connect(admin).requestOnboarding("dev-sim-01", owner.address);
    await tx.wait();
    console.log("Onboarding requested.");

    console.log("Admin is now listening for events...");
    // Keep alive
    await new Promise(() => {});
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
