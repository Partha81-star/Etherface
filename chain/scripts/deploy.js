import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { network } from "hardhat";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
  const { ethers } = await network.create();
  const registry = await ethers.deployContract("ContentRegistry");
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  const payload = {
    address,
    abi: JSON.parse(registry.interface.formatJson()),
    chainId: Number((await ethers.provider.getNetwork()).chainId),
    deployedAt: new Date().toISOString(),
  };

  const destinations = [
    path.resolve(__dirname, "../../backend/chain/deployed_address.json"),
    path.resolve(__dirname, "../../frontend/src/chain/abi.json"),
  ];

  for (const destination of destinations) {
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, `${JSON.stringify(payload, null, 2)}\n`);
  }

  console.log(`ContentRegistry deployed to: ${address}`);
  console.log(`Network chain ID: ${payload.chainId}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
