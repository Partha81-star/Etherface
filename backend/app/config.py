from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str
    rpc_url: str
    private_key: str | None
    contract_address: str | None
    face_match_tolerance: float
    frontend_origin: str
    chain_artifact_path: Path
    admin_name: str
    admin_email: str
    admin_password_hash: str
    admin_session_minutes: int
    member_session_minutes: int


@lru_cache
def get_settings() -> Settings:
    tolerance = float(os.getenv("FACE_MATCH_TOLERANCE", "0.6"))
    if not 0 < tolerance <= 2:
        raise ValueError("FACE_MATCH_TOLERANCE must be greater than 0 and at most 2")

    return Settings(
        database_url=os.getenv(
            "DATABASE_URL", "sqlite+aiosqlite:///./face_verify.db"
        ),
        rpc_url=os.getenv("RPC_URL", "http://127.0.0.1:8545"),
        private_key=os.getenv("PRIVATE_KEY") or None,
        contract_address=os.getenv("CONTRACT_ADDRESS") or None,
        face_match_tolerance=tolerance,
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
        chain_artifact_path=Path(
            os.getenv(
                "CHAIN_ARTIFACT_PATH",
                str(BACKEND_DIR / "chain" / "deployed_address.json"),
            )
        ),
        admin_name=os.getenv("ADMIN_NAME", "Local Administrator").strip(),
        admin_email=os.getenv(
            "ADMIN_EMAIL", "admin@faceverify.local"
        ).strip().lower(),
        admin_password_hash=os.getenv("ADMIN_PASSWORD_HASH")
        or (
            "pbkdf2_sha256$310000$ZXRoZXJmYWNlLWxvY2FsLWFkbWluLXYx$"
            "d0x4RJEWVpe2mEmtsaDSlkqs-8oLnnfZV1hfwIQB8Dc"
        ),
        admin_session_minutes=int(os.getenv("ADMIN_SESSION_MINUTES", "480")),
        member_session_minutes=int(os.getenv("MEMBER_SESSION_MINUTES", "60")),
    )
