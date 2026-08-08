import { loadFixture } from "@nomicfoundation/hardhat-toolbox/network-helpers";
import { expect } from "chai";
import { ethers } from "hardhat";

describe("LeasingRegistry", function () {
  async function deployContractsFixture() {
    const [admin, owner, otherAccount] = await ethers.getSigners();
    
    const OnboardingTrust = await ethers.getContractFactory("OnboardingTrust");
    const trust = await OnboardingTrust.deploy();

    const LeasingRegistry = await ethers.getContractFactory("LeasingRegistry");
    const registry = await LeasingRegistry.deploy(await trust.getAddress());

    return { trust, registry, admin, owner, otherAccount };
  }

  describe("leaseNode", function () {
    it("Should lease an approved node", async function () {
      const { trust, registry, admin, owner, otherAccount } = await loadFixture(deployContractsFixture);
      
      await trust.connect(admin).requestOnboarding("worker-1", owner.address);
      await trust.connect(owner).approve(0);

      await expect(registry.connect(otherAccount).leaseNode("worker-1"))
        .to.emit(registry, "NodeLeased")
        .withArgs("worker-1", otherAccount.address);

      const leaseInfo = await registry.leases("worker-1");
      expect(leaseInfo.isLeased).to.be.true;
      expect(leaseInfo.leasedBy).to.equal(otherAccount.address);
    });

    it("Should revert if node is not approved", async function () {
      const { trust, registry, admin, owner, otherAccount } = await loadFixture(deployContractsFixture);
      
      await trust.connect(admin).requestOnboarding("worker-1", owner.address);
      // Not approved

      await expect(registry.connect(otherAccount).leaseNode("worker-1"))
        .to.be.revertedWith("Node not approved");
    });

    it("Should revert if node does not exist", async function () {
      const { registry, otherAccount } = await loadFixture(deployContractsFixture);
      
      await expect(registry.connect(otherAccount).leaseNode("worker-1"))
        .to.be.revertedWith("Device not found");
    });

    it("Should revert if node is already leased", async function () {
      const { trust, registry, admin, owner, otherAccount } = await loadFixture(deployContractsFixture);
      
      await trust.connect(admin).requestOnboarding("worker-1", owner.address);
      await trust.connect(owner).approve(0);

      await registry.connect(otherAccount).leaseNode("worker-1");

      await expect(registry.connect(admin).leaseNode("worker-1"))
        .to.be.revertedWith("Node already leased");
    });
  });

  describe("releaseNode", function () {
    it("Should release a leased node", async function () {
      const { trust, registry, admin, owner, otherAccount } = await loadFixture(deployContractsFixture);
      
      await trust.connect(admin).requestOnboarding("worker-1", owner.address);
      await trust.connect(owner).approve(0);
      await registry.connect(otherAccount).leaseNode("worker-1");

      await expect(registry.connect(otherAccount).releaseNode("worker-1"))
        .to.emit(registry, "NodeReleased")
        .withArgs("worker-1", otherAccount.address);

      const leaseInfo = await registry.leases("worker-1");
      expect(leaseInfo.isLeased).to.be.false;
      expect(leaseInfo.leasedBy).to.equal(ethers.ZeroAddress);
    });

    it("Should revert if called by someone else", async function () {
      const { trust, registry, admin, owner, otherAccount } = await loadFixture(deployContractsFixture);
      
      await trust.connect(admin).requestOnboarding("worker-1", owner.address);
      await trust.connect(owner).approve(0);
      await registry.connect(otherAccount).leaseNode("worker-1");

      await expect(registry.connect(admin).releaseNode("worker-1"))
        .to.be.revertedWith("Not the current leaser");
    });

    it("Should revert if node is not leased", async function () {
      const { registry, otherAccount } = await loadFixture(deployContractsFixture);
      
      await expect(registry.connect(otherAccount).releaseNode("worker-1"))
        .to.be.revertedWith("Node not leased");
    });
  });
});
