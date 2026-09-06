from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    image_path: Mapped[str] = mapped_column(String(1024), unique=True)
    caption: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(String(2048))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    face_encoding: Mapped[bytes] = mapped_column(LargeBinary)

    verifications: Mapped[list["VerificationRecord"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class VerificationRecord(Base):
    __tablename__ = "verification_records"
    __table_args__ = (
        Index("idx_verification_records_post_id", "post_id"),
        Index("idx_verification_records_content_hash", "content_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    block_number: Mapped[int] = mapped_column(nullable=False)
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="confirmed", nullable=False)
    distance: Mapped[float | None] = mapped_column(Float, nullable=True)

    post: Mapped[Post] = relationship(back_populates="verifications")


class ScanLog(Base):
    __tablename__ = "scan_logs"
    __table_args__ = (Index("idx_scan_logs_matched_post_id", "matched_post_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    matched_post_id: Mapped[int | None] = mapped_column(
        ForeignKey("posts.id"), nullable=True
    )
    distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (
        Index("idx_members_member_code", "member_code", unique=True),
        Index("idx_members_email", "email", unique=True),
        Index("idx_members_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    member_code: Mapped[str] = mapped_column(String(40), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    face_encoding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    face_provider: Mapped[str] = mapped_column(String(40), nullable=False)
    encoding_version: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    consent_confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    last_authenticated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    successful_auth_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )


class AuthenticationAttempt(Base):
    __tablename__ = "authentication_attempts"
    __table_args__ = (
        Index("idx_authentication_attempts_member_id", "member_id"),
        Index("idx_authentication_attempts_status", "status"),
        Index("idx_authentication_attempts_attempted_at", "attempted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int | None] = mapped_column(
        ForeignKey("members.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    face_provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AccessSession(Base):
    __tablename__ = "access_sessions"
    __table_args__ = (
        Index("idx_access_sessions_token_hash", "token_hash", unique=True),
        Index("idx_access_sessions_member_id", "member_id"),
        Index("idx_access_sessions_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    member_id: Mapped[int | None] = mapped_column(
        ForeignKey("members.id"), nullable=True
    )
    subject: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
