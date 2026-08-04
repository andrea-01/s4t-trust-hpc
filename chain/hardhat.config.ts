import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";

const config: HardhatUserConfig = {
  solidity: "0.8.24",
  networks: {
    docker: {
      url: process.env.RPC_URL || "http://hardhat-node:8545"
    }
  }
};

export default config;
