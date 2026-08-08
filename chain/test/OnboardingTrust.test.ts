import { loadFixture } from "@nomicfoundation/hardhat-toolbox/network-helpers";
import { expect } from "chai";
import { ethers } from "hardhat";

describe("OnboardingTrust", function () {
  async function deployContractFixture() {
    const [admin, owner, otherAccount] = await ethers.getSigners();
    const Contract = await ethers.getContractFactory("OnboardingTrust");
    const contract = await Contract.deploy();
    return { contract, admin, owner, otherAccount };
  }

  describe("requestOnboarding", function () {
    it("Should create a request and emit event", async function () {
      const { contract, admin, owner } = await loadFixture(deployContractFixture);
      
      await expect(contract.connect(admin).requestOnboarding("dev-01", owner.address))
        .to.emit(contract, "OnboardingRequested")
        .withArgs(0, "dev-01", admin.address, owner.address);

      const req = await contract.requests(0);
      expect(req.deviceId).to.equal("dev-01");
      expect(req.requester).to.equal(admin.address);
      expect(req.owner).to.equal(owner.address);
      expect(req.status).to.equal(0); // Status.Pending
    });
  });

  describe("approve", function () {
    it("Should approve if called by owner", async function () {
      const { contract, admin, owner } = await loadFixture(deployContractFixture);
      await contract.connect(admin).requestOnboarding("dev-01", owner.address);
      
      await expect(contract.connect(owner).approve(0))
        .to.emit(contract, "OnboardingApproved")
        .withArgs(0, "dev-01", owner.address);

      const req = await contract.requests(0);
      expect(req.status).to.equal(1); // Status.Approved
    });

    it("Should revert if called by non-owner", async function () {
      const { contract, admin, owner, otherAccount } = await loadFixture(deployContractFixture);
      await contract.connect(admin).requestOnboarding("dev-01", owner.address);
      
      await expect(contract.connect(otherAccount).approve(0)).to.be.revertedWith("Not the owner");
    });
  });

  describe("reject", function () {
    it("Should reject if called by owner", async function () {
      const { contract, admin, owner } = await loadFixture(deployContractFixture);
      await contract.connect(admin).requestOnboarding("dev-01", owner.address);
      
      await expect(contract.connect(owner).reject(0))
        .to.emit(contract, "OnboardingRejected")
        .withArgs(0, "dev-01", owner.address);

      const req = await contract.requests(0);
      expect(req.status).to.equal(2); // Status.Rejected
    });
  });

  describe("revoke", function () {
    it("Should revoke if called by admin on approved request", async function () {
      const { contract, admin, owner } = await loadFixture(deployContractFixture);
      await contract.connect(admin).requestOnboarding("dev-01", owner.address);
      await contract.connect(owner).approve(0);
      
      await expect(contract.connect(admin).revoke(0))
        .to.emit(contract, "OnboardingRevoked")
        .withArgs(0, "dev-01", admin.address);

      const req = await contract.requests(0);
      expect(req.status).to.equal(3); // Status.Revoked
    });

    it("Should revoke if called by owner on approved request", async function () {
        const { contract, admin, owner } = await loadFixture(deployContractFixture);
        await contract.connect(admin).requestOnboarding("dev-01", owner.address);
        await contract.connect(owner).approve(0);
        
        await expect(contract.connect(owner).revoke(0))
          .to.emit(contract, "OnboardingRevoked")
          .withArgs(0, "dev-01", owner.address);
  
        const req = await contract.requests(0);
        expect(req.status).to.equal(3); // Status.Revoked
      });

    it("Should revert if called by non-authorized", async function () {
      const { contract, admin, owner, otherAccount } = await loadFixture(deployContractFixture);
      await contract.connect(admin).requestOnboarding("dev-01", owner.address);
      await contract.connect(owner).approve(0);
      
      await expect(contract.connect(otherAccount).revoke(0)).to.be.revertedWith("Not authorized");
    });
  });

  describe("getDeviceStatus", function () {
    it("Should return correct status even after many historical requests (gas limit check)", async function () {
      const { contract, admin, owner } = await loadFixture(deployContractFixture);
      
      // 1. Create 30 historical requests for filler devices
      for (let i = 0; i < 30; i++) {
        await contract.connect(admin).requestOnboarding(`filler-device-${i}`, owner.address);
      }

      // 2. Add our target device (worker-1)
      await contract.connect(admin).requestOnboarding("worker-1", owner.address);
      await contract.connect(owner).approve(30);

      // 3. Create a few more requests after it to make sure it's buried in the middle
      for (let i = 31; i < 35; i++) {
        await contract.connect(admin).requestOnboarding(`filler-device-${i}`, owner.address);
      }

      // 4. Verify getDeviceStatus
      const status = await contract.getDeviceStatus("worker-1");
      expect(status).to.equal(1); // Status.Approved

      // 5. Estimate and log gas used for getDeviceStatus
      const gasEstimate = await contract.getDeviceStatus.estimateGas("worker-1");
      console.log(`\t[Gas Cost] getDeviceStatus("worker-1") across ~35 total historical records: ${gasEstimate.toString()} gas`);
    });

    it("Should revert if device not found", async function () {
      const { contract } = await loadFixture(deployContractFixture);
      await expect(contract.getDeviceStatus("non-existent")).to.be.revertedWith("Device not found");
    });
  });
});
