from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError, TransactionNotFound

from .config import Settings, get_settings


class ChainServiceError(RuntimeError):
    pass


class HashAlreadyRegisteredError(ChainServiceError):
    pass


@dataclass(frozen=True)
class RegisteredHash:
    submitter: str
    timestamp: int
    metadata_uri: str


class ChainService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.web3 = Web3(Web3.HTTPProvider(self.settings.rpc_url))
        self._artifact: dict[str, Any] | None = None
        self._contract: Contract | None = None

    def _load_artifact(self) -> dict[str, Any]:
        if self._artifact is not None:
            return self._artifact
        path = Path(self.settings.chain_artifact_path)
        if not path.is_file():
            raise ChainServiceError(
                f"Contract deployment artifact was not found at {path}. Deploy the contract first."
            )
        try:
            self._artifact = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ChainServiceError("The contract deployment artifact is invalid.") from exc
        return self._artifact

    @property
    def contract(self) -> Contract:
        if self._contract is None:
            if not self.web3.is_connected():
                raise ChainServiceError(
                    f"Could not connect to the blockchain RPC at {self.settings.rpc_url}."
                )
            artifact = self._load_artifact()
            address = self.settings.contract_address or artifact.get("address")
            if not address:
                raise ChainServiceError("No deployed contract address is configured.")
            self._contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(address), abi=artifact["abi"]
            )
        return self._contract

    @property
    def contract_address(self) -> str:
        return str(self.contract.address)

    def _sender(self) -> str:
        if self.settings.private_key:
            return self.web3.eth.account.from_key(self.settings.private_key).address
        accounts = self.web3.eth.accounts
        if not accounts:
            raise ChainServiceError(
                "The RPC exposes no unlocked account. Configure PRIVATE_KEY for this network."
            )
        return accounts[0]

    def register_hash(self, content_hash: bytes, metadata_uri: str) -> Any:
        if len(content_hash) != 32:
            raise ChainServiceError("content_hash must be exactly 32 bytes.")
        existing = self.verify_hash(content_hash)
        if existing is not None:
            raise HashAlreadyRegisteredError("This content hash is already registered.")

        sender = self._sender()
        function = self.contract.functions.registerHash(content_hash, metadata_uri)
        try:
            if self.settings.private_key:
                transaction = function.build_transaction(
                    {
                        "from": sender,
                        "nonce": self.web3.eth.get_transaction_count(sender),
                        "chainId": self.web3.eth.chain_id,
                        "gas": function.estimate_gas({"from": sender}),
                        "maxFeePerGas": self.web3.eth.gas_price * 2,
                        "maxPriorityFeePerGas": self.web3.to_wei(1, "gwei"),
                    }
                )
                signed = self.web3.eth.account.sign_transaction(
                    transaction, self.settings.private_key
                )
                tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
            else:
                tx_hash = function.transact({"from": sender})
            return self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        except ContractLogicError as exc:
            if "HashAlreadyRegistered" in str(exc):
                raise HashAlreadyRegisteredError(
                    "This content hash is already registered."
                ) from exc
            raise ChainServiceError(f"The contract rejected the transaction: {exc}") from exc
        except (OSError, TransactionNotFound, ValueError) as exc:
            raise ChainServiceError(f"Blockchain transaction failed: {exc}") from exc

    def verify_hash(self, content_hash: bytes) -> RegisteredHash | None:
        if len(content_hash) != 32:
            raise ChainServiceError("content_hash must be exactly 32 bytes.")
        try:
            submitter, timestamp, metadata_uri = self.contract.functions.verifyHash(
                content_hash
            ).call()
        except (OSError, ValueError, ContractLogicError) as exc:
            raise ChainServiceError(f"Could not read from the blockchain: {exc}") from exc
        if int(timestamp) == 0 or submitter == "0x0000000000000000000000000000000000000000":
            return None
        return RegisteredHash(
            submitter=submitter,
            timestamp=int(timestamp),
            metadata_uri=metadata_uri,
        )


def explorer_url(tx_hash: str, chain_id: int) -> str | None:
    if chain_id == 80002:
        return f"https://amoy.polygonscan.com/tx/{tx_hash}"
    return None
