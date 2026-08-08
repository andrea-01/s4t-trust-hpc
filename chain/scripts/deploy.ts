import { ethers } from "hardhat";
import * as fs from "fs";
import * as path from "path";

async function main() {
    console.log("Deploying OnboardingTrust contract...");
    const [deployer] = await ethers.getSigners();
    console.log(`Deployer address: ${deployer.address}`);

    const Contract = await ethers.getContractFactory("OnboardingTrust");
    const contract = await Contract.deploy();
    await contract.waitForDeployment();

    const address = await contract.getAddress();
    const deployBlock = await ethers.provider.getBlockNumber();
    console.log(`Contract deployed to: ${address} at block ${deployBlock}`);

    // Save to file
    const deployDir = path.join(__dirname, "..", "deployments");
    if (!fs.existsSync(deployDir)) {
        fs.mkdirSync(deployDir, { recursive: true });
    }
    
    const deployData = {
        address: address,
        blockNumber: deployBlock,
        network: (await ethers.provider.getNetwork()).name,
        timestamp: new Date().toISOString()
    };
    
    fs.writeFileSync(
        path.join(deployDir, "localhost.json"), 
        JSON.stringify(deployData, null, 2)
    );
    console.log("Deployment info saved to deployments/localhost.json");

    // Deploy LeasingRegistry
    console.log("Deploying LeasingRegistry contract...");
    const LeasingRegistry = await ethers.getContractFactory("LeasingRegistry");
    const leasingContract = await LeasingRegistry.deploy(address);
    await leasingContract.waitForDeployment();

    const leasingAddress = await leasingContract.getAddress();
    const leasingBlock = await ethers.provider.getBlockNumber();
    console.log(`LeasingRegistry deployed to: ${leasingAddress} at block ${leasingBlock}`);

    const leasingDeployData = {
        address: leasingAddress,
        blockNumber: leasingBlock,
        network: (await ethers.provider.getNetwork()).name,
        timestamp: new Date().toISOString()
    };
    
    fs.writeFileSync(
        path.join(deployDir, "leasing-localhost.json"), 
        JSON.stringify(leasingDeployData, null, 2)
    );
    console.log("LeasingRegistry deployment info saved to deployments/leasing-localhost.json");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
