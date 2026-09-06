from __future__ import annotations

import asyncio
import os
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .auth_service import (
    create_access_session,
    get_access_session,
    revoke_access_session,
    verify_password,
)
from .config import get_settings
from .database import get_session
from .errors import AppError
from .face_service import (
    FaceNotFoundError,
    FaceServiceError,
    MultipleFacesFoundError,
    encode_face_with_box,
    face_distance,
    face_model_version,
    find_best_match,
    serialize_encoding,
)
from .models import AccessSession, AuthenticationAttempt, Member
from .schemas import (
    AdminLoginRequest,
    AdminOverviewResponse,
    AdminProfileResponse,
    AdminSessionResponse,
    AuthenticationAttemptResponse,
    CurrentMemberResponse,
    FaceAuthenticationResponse,
    MemberListResponse,
    MemberResponse,
    MemberStatusUpdate,
    MessageResponse,
    PublicSummaryResponse,
)


router = APIRouter()
bearer = HTTPBearer(auto_error=False)
settings = get_settings()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MEMBER_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,39}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.events: dict[str, deque[float]] = defaultdict(deque)

    def blocked(self, key: str) -> bool:
        now = time.monotonic()
        events = self.events[key]
        while events and now - events[0] > self.window_seconds:
            events.popleft()
        return len(events) >= self.limit

    def record_failure(self, key: str) -> None:
        self.events[key].append(time.monotonic())

    def clear(self, key: str) -> None:
        self.events.pop(key, None)


admin_limiter = SlidingWindowLimiter(limit=5, window_seconds=60)
face_limiter = SlidingWindowLimiter(limit=10, window_seconds=60)


def member_response(member: Member) -> MemberResponse:
    return MemberResponse.model_validate(member)


async def read_image(image: UploadFile) -> bytes:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise AppError("Upload a JPEG, PNG, or WebP image.", "INVALID_IMAGE_TYPE", 400)
    payload = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise AppError("Image must be 10 MB or smaller.", "IMAGE_TOO_LARGE", 413)
    return payload


async def encode_single_face(payload: bytes):
    try:
        return await asyncio.to_thread(
            encode_face_with_box, payload, require_single=True
        )
    except MultipleFacesFoundError as exc:
        raise AppError(str(exc), "MULTIPLE_FACES", 400) from exc
    except FaceNotFoundError as exc:
        raise AppError(str(exc), "FACE_NOT_FOUND", 400) from exc
    except FaceServiceError as exc:
        raise AppError(str(exc), "INVALID_FACE_IMAGE", 400) from exc


async def access_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
    session: AsyncSession,
    *,
    role: str | None = None,
) -> AccessSession:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("Sign in to continue.", "AUTHENTICATION_REQUIRED", 401)
    record = await get_access_session(session, credentials.credentials, role=role)
    if record is None:
        raise AppError("Your session is invalid or expired.", "SESSION_EXPIRED", 401)
    return record


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> AccessSession:
    return await access_from_credentials(credentials, session, role="admin")


async def require_member(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> AccessSession:
    return await access_from_credentials(credentials, session, role="member")


async def require_any_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> AccessSession:
    return await access_from_credentials(credentials, session)


@router.get("/api/public/summary", response_model=PublicSummaryResponse)
async def public_summary(
    session: AsyncSession = Depends(get_session),
) -> PublicSummaryResponse:
    active_members = await session.scalar(
        select(func.count(Member.id)).where(Member.is_active.is_(True))
    )
    backend = os.getenv("FACE_BACKEND", "auto")
    return PublicSummaryResponse(
        active_members=int(active_members or 0),
        face_backend="dlib preferred" if backend == "auto" else backend,
    )


@router.post("/api/admin/login", response_model=AdminSessionResponse)
async def admin_login(
    credentials: AdminLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> AdminSessionResponse:
    email = credentials.email.strip().lower()
    limiter_key = email or "blank"
    if admin_limiter.blocked(limiter_key):
        raise AppError(
            "Too many sign-in attempts. Wait one minute and try again.",
            "RATE_LIMITED",
            429,
        )
    valid = email == settings.admin_email and verify_password(
        credentials.password, settings.admin_password_hash
    )
    if not valid:
        admin_limiter.record_failure(limiter_key)
        raise AppError("Email or password is incorrect.", "INVALID_CREDENTIALS", 401)

    admin_limiter.clear(limiter_key)
    token, record = await create_access_session(
        session,
        role="admin",
        subject=settings.admin_email,
        duration_minutes=settings.admin_session_minutes,
    )
    await session.commit()
    return AdminSessionResponse(
        access_token=token,
        expires_at=record.expires_at,
        admin_name=settings.admin_name,
        admin_email=settings.admin_email,
    )


@router.get("/api/admin/me", response_model=AdminProfileResponse)
async def admin_me(_: AccessSession = Depends(require_admin)) -> AdminProfileResponse:
    return AdminProfileResponse(name=settings.admin_name, email=settings.admin_email)


@router.post("/api/auth/logout", response_model=MessageResponse)
async def logout(
    access: AccessSession = Depends(require_any_session),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    await revoke_access_session(session, access)
    await session.commit()
    return MessageResponse(detail="Signed out successfully.")


@router.post("/api/admin/members", response_model=MemberResponse, status_code=201)
async def enroll_member(
    member_code: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    department: str | None = Form(None),
    consent_confirmed: bool = Form(...),
    image: UploadFile = File(...),
    _: AccessSession = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> MemberResponse:
    code = member_code.strip().upper()
    name = " ".join(full_name.split())
    normalized_email = email.strip().lower()
    normalized_department = " ".join(department.split()) if department else None

    if not consent_confirmed:
        raise AppError(
            "Confirm the member's consent before enrollment.",
            "CONSENT_REQUIRED",
            400,
        )
    if not MEMBER_CODE_PATTERN.fullmatch(code):
        raise AppError(
            "Member ID must be 3–40 characters using letters, numbers, hyphens, or underscores.",
            "INVALID_MEMBER_CODE",
            422,
        )
    if len(name) < 2 or len(name) > 160:
        raise AppError("Enter the member's full name.", "INVALID_FULL_NAME", 422)
    if not EMAIL_PATTERN.fullmatch(normalized_email):
        raise AppError("Enter a valid email address.", "INVALID_EMAIL", 422)
    if normalized_department and len(normalized_department) > 120:
        raise AppError("Department must be 120 characters or fewer.", "INVALID_DEPARTMENT", 422)

    existing_code = await session.scalar(
        select(Member.id).where(Member.member_code == code)
    )
    if existing_code is not None:
        raise AppError("That member ID is already in use.", "MEMBER_CODE_EXISTS", 409)
    existing_email = await session.scalar(
        select(Member.id).where(Member.email == normalized_email)
    )
    if existing_email is not None:
        raise AppError("That email address is already enrolled.", "EMAIL_EXISTS", 409)

    payload = await read_image(image)
    face = await encode_single_face(payload)
    version = face_model_version(face.provider)
    compatible = list(
        (
            await session.scalars(
                select(Member).where(
                    Member.face_provider == face.provider,
                    Member.encoding_version == version,
                )
            )
        ).all()
    )
    duplicate = find_best_match(
        face.encoding, compatible, settings.face_match_tolerance
    )
    if duplicate is not None:
        raise AppError(
            "This face is already enrolled to another member.",
            "FACE_ALREADY_ENROLLED",
            409,
        )

    member = Member(
        member_code=code,
        full_name=name,
        email=normalized_email,
        department=normalized_department,
        face_encoding=serialize_encoding(face.encoding),
        face_provider=face.provider,
        encoding_version=version,
    )
    session.add(member)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            "A member with that ID or email already exists.",
            "MEMBER_ALREADY_EXISTS",
            409,
        ) from exc
    await session.refresh(member)
    return member_response(member)


@router.get("/api/admin/members", response_model=MemberListResponse)
async def list_members(
    search: str | None = Query(None, max_length=120),
    status: str = Query("all", pattern="^(all|active|inactive)$"),
    limit: int = Query(100, ge=1, le=250),
    offset: int = Query(0, ge=0),
    _: AccessSession = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> MemberListResponse:
    filters = []
    if status == "active":
        filters.append(Member.is_active.is_(True))
    elif status == "inactive":
        filters.append(Member.is_active.is_(False))
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        filters.append(
            or_(
                func.lower(Member.member_code).like(term),
                func.lower(Member.full_name).like(term),
                func.lower(Member.email).like(term),
                func.lower(func.coalesce(Member.department, "")).like(term),
            )
        )

    count_query = select(func.count(Member.id))
    query = select(Member).order_by(Member.enrolled_at.desc()).limit(limit).offset(offset)
    if filters:
        count_query = count_query.where(*filters)
        query = query.where(*filters)
    total = await session.scalar(count_query)
    members = list((await session.scalars(query)).all())
    return MemberListResponse(
        items=[member_response(member) for member in members], total=int(total or 0)
    )


@router.patch("/api/admin/members/{member_id}/status", response_model=MemberResponse)
async def update_member_status(
    member_id: int,
    change: MemberStatusUpdate,
    _: AccessSession = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> MemberResponse:
    member = await session.get(Member, member_id)
    if member is None:
        raise AppError("Member not found.", "MEMBER_NOT_FOUND", 404)
    member.is_active = change.is_active
    member.updated_at = datetime.now(timezone.utc)
    if not change.is_active:
        await session.execute(
            update(AccessSession)
            .where(
                AccessSession.member_id == member.id,
                AccessSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
    await session.commit()
    await session.refresh(member)
    return member_response(member)


def attempt_response(
    attempt: AuthenticationAttempt, member: Member | None
) -> AuthenticationAttemptResponse:
    return AuthenticationAttemptResponse(
        id=attempt.id,
        status=attempt.status,
        member_code=member.member_code if member else None,
        member_name=member.full_name if member else None,
        attempted_at=attempt.attempted_at,
    )


async def recent_attempts(
    session: AsyncSession, *, limit: int
) -> list[AuthenticationAttemptResponse]:
    rows = (
        await session.execute(
            select(AuthenticationAttempt, Member)
            .outerjoin(Member, AuthenticationAttempt.member_id == Member.id)
            .order_by(AuthenticationAttempt.attempted_at.desc())
            .limit(limit)
        )
    ).all()
    return [attempt_response(attempt, member) for attempt, member in rows]


@router.get("/api/admin/overview", response_model=AdminOverviewResponse)
async def admin_overview(
    _: AccessSession = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminOverviewResponse:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = await session.scalar(select(func.count(Member.id)))
    active = await session.scalar(
        select(func.count(Member.id)).where(Member.is_active.is_(True))
    )
    attempts_today = await session.scalar(
        select(func.count(AuthenticationAttempt.id)).where(
            AuthenticationAttempt.attempted_at >= today
        )
    )
    successful_today = await session.scalar(
        select(func.count(AuthenticationAttempt.id)).where(
            AuthenticationAttempt.attempted_at >= today,
            AuthenticationAttempt.status == "success",
        )
    )
    return AdminOverviewResponse(
        total_members=int(total or 0),
        active_members=int(active or 0),
        authentications_today=int(attempts_today or 0),
        successful_today=int(successful_today or 0),
        recent_attempts=await recent_attempts(session, limit=8),
    )


@router.get(
    "/api/admin/authentication-attempts",
    response_model=list[AuthenticationAttemptResponse],
)
async def list_authentication_attempts(
    limit: int = Query(50, ge=1, le=250),
    _: AccessSession = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[AuthenticationAttemptResponse]:
    return await recent_attempts(session, limit=limit)


async def record_failure(
    session: AsyncSession,
    *,
    failure_code: str,
    provider: str | None = None,
) -> None:
    session.add(
        AuthenticationAttempt(
            status="failed",
            face_provider=provider,
            failure_code=failure_code,
        )
    )
    await session.commit()


@router.post("/api/auth/face", response_model=FaceAuthenticationResponse)
async def authenticate_face(
    member_code: str = Form(...),
    image: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> FaceAuthenticationResponse:
    code = member_code.strip().upper()
    limiter_key = code or "blank"
    if face_limiter.blocked(limiter_key):
        raise AppError(
            "Too many attempts. Wait one minute and try again.",
            "RATE_LIMITED",
            429,
        )
    payload = await read_image(image)
    try:
        face = await encode_single_face(payload)
    except AppError as exc:
        await record_failure(session, failure_code=exc.code)
        raise

    member = await session.scalar(select(Member).where(Member.member_code == code))
    version = face_model_version(face.provider)
    distance = None
    if (
        member is not None
        and member.is_active
        and member.face_provider == face.provider
        and member.encoding_version == version
    ):
        stored_match = find_best_match(
            face.encoding, [member], settings.face_match_tolerance
        )
        if stored_match is not None:
            _, distance = stored_match

    if member is None or distance is None:
        face_limiter.record_failure(limiter_key)
        await record_failure(
            session, failure_code="FACE_AUTH_FAILED", provider=face.provider
        )
        raise AppError(
            "Authentication failed. Check your member ID and try a fresh face scan.",
            "FACE_AUTH_FAILED",
            401,
        )

    face_limiter.clear(limiter_key)
    now = datetime.now(timezone.utc)
    member.last_authenticated_at = now
    member.successful_auth_count += 1
    attempt = AuthenticationAttempt(
        member_id=member.id,
        status="success",
        distance=distance,
        face_provider=face.provider,
    )
    session.add(attempt)
    token, access = await create_access_session(
        session,
        role="member",
        subject=member.member_code,
        duration_minutes=settings.member_session_minutes,
        member_id=member.id,
    )
    await session.commit()
    await session.refresh(member)
    match_score = max(
        0.0, min(1.0, 1.0 - distance / settings.face_match_tolerance)
    )
    return FaceAuthenticationResponse(
        access_token=token,
        expires_at=access.expires_at,
        member=member_response(member),
        authenticated_at=now,
        match_score=round(match_score, 4),
    )


@router.get("/api/auth/me", response_model=CurrentMemberResponse)
async def current_member(
    access: AccessSession = Depends(require_member),
    session: AsyncSession = Depends(get_session),
) -> CurrentMemberResponse:
    member = await session.get(Member, access.member_id) if access.member_id else None
    if member is None or not member.is_active:
        await revoke_access_session(session, access)
        await session.commit()
        raise AppError("Your member access is no longer active.", "MEMBER_INACTIVE", 401)
    return CurrentMemberResponse(
        member=member_response(member), session_expires_at=access.expires_at
    )
