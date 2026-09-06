// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ContentRegistry
/// @notice An immutable registry of content hashes for consented media.
contract ContentRegistry {
    struct Record {
        address submitter;
        uint256 timestamp;
        string metadataURI;
    }

    mapping(bytes32 => Record) public records;

    event HashRegistered(
        bytes32 indexed contentHash,
        address indexed submitter,
        uint256 timestamp
    );

    error HashAlreadyRegistered(bytes32 contentHash);
    error EmptyHash();

    function registerHash(bytes32 contentHash, string calldata metadataURI) external {
        if (contentHash == bytes32(0)) revert EmptyHash();
        if (records[contentHash].timestamp != 0) {
            revert HashAlreadyRegistered(contentHash);
        }

        records[contentHash] = Record({
            submitter: msg.sender,
            timestamp: block.timestamp,
            metadataURI: metadataURI
        });

        emit HashRegistered(contentHash, msg.sender, block.timestamp);
    }

    function verifyHash(bytes32 contentHash) external view returns (Record memory) {
        return records[contentHash];
    }
}
