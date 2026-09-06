import { expect } from "chai";
import hre from "hardhat";

const { ethers } = await hre.network.create();

describe("ContentRegistry", function () {
  async function deployRegistry() {
    const [owner, other] = await ethers.getSigners();
    const registry = await ethers.deployContract("ContentRegistry");
    await registry.waitForDeployment();
    return { registry, owner, other };
  }

  it("registers a hash and emits its immutable anchor event", async function () {
    const { registry, owner } = await deployRegistry();
    const contentHash = ethers.sha256(ethers.toUtf8Bytes("authorized-post"));

    await expect(registry.registerHash(contentHash, "post://1"))
      .to.emit(registry, "HashRegistered")
      .withArgs(contentHash, owner.address, (value) => value > 0n);

    const record = await registry.verifyHash(contentHash);
    expect(record.submitter).to.equal(owner.address);
    expect(record.timestamp).to.be.greaterThan(0n);
    expect(record.metadataURI).to.equal("post://1");
  });

  it("rejects duplicate registrations", async function () {
    const { registry } = await deployRegistry();
    const contentHash = ethers.sha256(ethers.toUtf8Bytes("same-post"));
    await registry.registerHash(contentHash, "post://1");

    await expect(registry.registerHash(contentHash, "post://changed"))
      .to.be.revertedWithCustomError(registry, "HashAlreadyRegistered")
      .withArgs(contentHash);
  });

  it("returns the stored data through verifyHash", async function () {
    const { registry, other } = await deployRegistry();
    const contentHash = ethers.sha256(ethers.toUtf8Bytes("post-two"));
    await registry.connect(other).registerHash(contentHash, "ipfs://authorized/2");

    const record = await registry.verifyHash(contentHash);
    expect(record.submitter).to.equal(other.address);
    expect(record.metadataURI).to.equal("ipfs://authorized/2");
  });

  it("returns an empty record for an unknown hash", async function () {
    const { registry } = await deployRegistry();
    const unknownHash = ethers.sha256(ethers.toUtf8Bytes("unknown"));

    const record = await registry.verifyHash(unknownHash);
    expect(record.submitter).to.equal(ethers.ZeroAddress);
    expect(record.timestamp).to.equal(0n);
    expect(record.metadataURI).to.equal("");
  });
});
