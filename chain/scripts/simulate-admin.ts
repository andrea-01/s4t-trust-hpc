import { ethers } from "hardhat";

async function main() {
    console.log("Admin simulation starting...");
    const [admin, owner] = await ethers.getSigners();
    
    // Deploy contract
    const Contract = await ethers.getContractFactory("OnboardingTrust");
    const contract = await Contract.deploy();
    await contract.waitForDeployment();
    
    const address = await contract.getAddress();
    console.log(`Contract deployed to: ${address}`);
    
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
