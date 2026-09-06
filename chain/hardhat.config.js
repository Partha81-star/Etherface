import "dotenv/config";
import hardhatEthers from "@nomicfoundation/hardhat-ethers";
import hardhatEthersChaiMatchers from "@nomicfoundation/hardhat-ethers-chai-matchers";
import hardhatMocha from "@nomicfoundation/hardhat-mocha";
import { defineConfig } from "hardhat/config";

const privateKey = process.env.PRIVATE_KEY;

export default defineConfig({
  plugins: [hardhatEthers, hardhatEthersChaiMatchers, hardhatMocha],
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },
  networks: {
    localhost: {
      type: "http",
      chainType: "l1",
      url: process.env.RPC_URL || "http://127.0.0.1:8545",
      accounts: "remote",
    },
    amoy: {
      type: "http",
      chainType: "generic",
      url: process.env.AMOY_RPC_URL || "https://rpc-amoy.polygon.technology",
      accounts: privateKey ? [privateKey] : [],
      chainId: 80002,
    },
  },
});
