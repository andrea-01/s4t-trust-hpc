import { ethers } from "hardhat";
import * as fs from "fs";
import * as path from "path";

async function main() {
    console.log("Starting auto-onboarding for workers...");
    const [admin, owner] = await ethers.getSigners();
    
    // Read OnboardingTrust address
    const deployPath = path.join(__dirname, "..", "deployments", "localhost.json");
    if (!fs.existsSync(deployPath)) {
        throw new Error(`Deployment file not found at ${deployPath}`);
    }
    
    const deployData = JSON.parse(fs.readFileSync(deployPath, "utf8"));
    const trustAddress = deployData.address;
    
    const OnboardingTrust = await ethers.getContractAt("OnboardingTrust", trustAddress);
    
    const workers = ["worker-1", "worker-2", "worker-3"];
    
    for (const workerId of workers) {
        console.log(`Processing ${workerId}...`);
        
        try {
            // Check status first
            const status = await OnboardingTrust.getDeviceStatus(workerId);
            if (status === 1n) {
                console.log(`- ${workerId} is already Approved.`);
                continue;
            }
        } catch (e: any) {
            // If the transaction reverts (e.g., Device not found), we assume it's not approved.
            console.log(`- ${workerId} not found or not approved. Proceeding to onboard.`);
        }
        
        // Request onboarding
        console.log(`- Requesting onboarding for ${workerId}...`);
        const tx1 = await OnboardingTrust.connect(admin).requestOnboarding(workerId, owner.address);
        const receipt1 = await tx1.wait();
        
        // Find requestId from event
        let requestId;
        for (const log of receipt1!.logs) {
            try {
                const parsedLog = OnboardingTrust.interface.parseLog(log as any);
                if (parsedLog && parsedLog.name === "OnboardingRequested") {
                    requestId = parsedLog.args[0];
                    break;
                }
            } catch (err) {
                // Ignore logs that aren't parsed by this interface
            }
        }
        
        if (requestId === undefined) {
            throw new Error(`Failed to find requestId for ${workerId}`);
        }
        
        // Approve
        console.log(`- Approving request ${requestId} for ${workerId}...`);
        const tx2 = await OnboardingTrust.connect(owner).approve(requestId);
        await tx2.wait();
        
        console.log(`- ${workerId} successfully onboarded and approved.`);
    }
    
    console.log("Auto-onboarding completed.");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
