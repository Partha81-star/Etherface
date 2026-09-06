from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    detail: str
    code: str


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caption: str
    author: str
    source_url: str
    timestamp: datetime
    image_url: str


class FaceBox(BaseModel):
    top: int = Field(ge=0)
    right: int = Field(ge=0)
    bottom: int = Field(ge=0)
    left: int = Field(ge=0)
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)


class ScanResponse(BaseModel):
    match: PostResponse
    distance: float = Field(ge=0)
    tolerance: float = Field(gt=0)
    face_box: FaceBox
    face_provider: str


class ChainRegisterResponse(BaseModel):
    post_id: int
    content_hash: str
    tx_hash: str
    block_number: int
    contract_address: str
    explorer_url: str | None = None


class OnChainRecord(BaseModel):
    submitter: str
    timestamp: int
    metadata_uri: str
    content_hash: str


class VerificationStatusResponse(BaseModel):
    post_id: int
    verified: bool
    local_hash: str
    on_chain_hash: str | None
    on_chain_record: OnChainRecord | None
    status: str


class AdminLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class AdminSessionResponse(SessionResponse):
    admin_name: str
    admin_email: str


class AdminProfileResponse(BaseModel):
    name: str
    email: str
    role: str = "admin"


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_code: str
    full_name: str
    email: str
    department: str | None
    is_active: bool
    face_provider: str
    encoding_version: str
    consent_confirmed_at: datetime
    enrolled_at: datetime
    last_authenticated_at: datetime | None
    successful_auth_count: int


class MemberListResponse(BaseModel):
    items: list[MemberResponse]
    total: int


class MemberStatusUpdate(BaseModel):
    is_active: bool


class FaceAuthenticationResponse(SessionResponse):
    authenticated: bool = True
    member: MemberResponse
    authenticated_at: datetime
    match_score: float = Field(ge=0, le=1)


class CurrentMemberResponse(BaseModel):
    member: MemberResponse
    session_expires_at: datetime


class AuthenticationAttemptResponse(BaseModel):
    id: int
    status: str
    member_code: str | None
    member_name: str | None
    attempted_at: datetime


class AdminOverviewResponse(BaseModel):
    total_members: int
    active_members: int
    authentications_today: int
    successful_today: int
    recent_attempts: list[AuthenticationAttemptResponse]


class PublicSummaryResponse(BaseModel):
    active_members: int
    face_backend: str
    authentication_mode: str = "member_id_and_face"


class MessageResponse(BaseModel):
    detail: str
