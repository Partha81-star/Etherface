from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AccessSession


PBKDF2_ITERATIONS = 310_000


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    chosen_salt = salt or secrets.token_bytes(18)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), chosen_salt, PBKDF2_ITERATIONS
    )
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
        f"{_b64encode(chosen_salt)}${_b64encode(digest)}"
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, expected_raw = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = _b64decode(salt_raw)
        expected = _b64decode(expected_raw)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual, expected)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def create_access_session(
    session: AsyncSession,
    *,
    role: str,
    subject: str,
    duration_minutes: int,
    member_id: int | None = None,
) -> tuple[str, AccessSession]:
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    record = AccessSession(
        token_hash=token_digest(raw_token),
        role=role,
        member_id=member_id,
        subject=subject,
        created_at=now,
        expires_at=now + timedelta(minutes=duration_minutes),
    )
    session.add(record)
    await session.flush()
    return raw_token, record


async def get_access_session(
    session: AsyncSession, token: str, *, role: str | None = None
) -> AccessSession | None:
    record = await session.scalar(
        select(AccessSession).where(AccessSession.token_hash == token_digest(token))
    )
    if record is None or record.revoked_at is not None:
        return None
    if role is not None and record.role != role:
        return None
    if as_utc(record.expires_at) <= datetime.now(timezone.utc):
        return None
    return record


async def revoke_access_session(
    session: AsyncSession, record: AccessSession
) -> None:
    record.revoked_at = datetime.now(timezone.utc)
    await session.flush()


if __name__ == "__main__":
    import getpass

    print(hash_password(getpass.getpass("New admin password: ")))
