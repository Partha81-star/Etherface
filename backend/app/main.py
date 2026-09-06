from __future__ import annotations

import asyncio
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .access_api import require_admin, router as access_router
from .chain_service import (
    ChainService,
    ChainServiceError,
    HashAlreadyRegisteredError,
    explorer_url,
)
from .config import get_settings
from .content_service import compute_post_hash, hash_hex
from .database import get_session, init_db
from .errors import AppError
from .face_service import FaceServiceError, encode_face_with_box, find_best_match
from .models import AccessSession, Post, ScanLog, VerificationRecord
from .schemas import (
    ChainRegisterResponse,
    ErrorResponse,
    FaceBox,
    OnChainRecord,
    PostResponse,
    ScanResponse,
    VerificationStatusResponse,
)


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="EtherFace Access API",
    version="2.0.0",
    description="Admin-managed local face enrollment and member authentication.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.frontend_origin.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Request validation failed.", "code": "VALIDATION_ERROR", "errors": exc.errors()},
    )


app.include_router(access_router)


def post_response(post: Post) -> PostResponse:
    return PostResponse(
        id=post.id,
        caption=post.caption,
        author=post.author,
        source_url=post.source_url,
        timestamp=post.timestamp,
        image_url=f"/api/posts/{post.id}/image",
    )


async def require_post(post_id: int, session: AsyncSession) -> Post:
    post = await session.get(Post, post_id)
    if post is None:
        raise AppError("Post not found.", "POST_NOT_FOUND", 404)
    return post


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/posts", response_model=list[PostResponse])
async def list_posts(session: AsyncSession = Depends(get_session)) -> list[PostResponse]:
    posts = (await session.scalars(select(Post).order_by(Post.timestamp.desc()))).all()
    return [post_response(post) for post in posts]


@app.get("/api/posts/{post_id}/image")
async def post_image(post_id: int, session: AsyncSession = Depends(get_session)) -> FileResponse:
    post = await require_post(post_id, session)
    path = Path(post.image_path)
    if not path.is_file():
        raise AppError("The post image is missing.", "IMAGE_NOT_FOUND", 404)
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


@app.post(
    "/api/scan",
    response_model=ScanResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def scan(
    image: UploadFile = File(...), session: AsyncSession = Depends(get_session)
) -> ScanResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise AppError("Upload a JPEG, PNG, or WebP image.", "INVALID_IMAGE_TYPE", 400)
    payload = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise AppError("Image must be 10 MB or smaller.", "IMAGE_TOO_LARGE", 413)

    try:
        face = await asyncio.to_thread(encode_face_with_box, payload)
    except FaceServiceError as exc:
        raise AppError(str(exc), "FACE_NOT_FOUND", 400) from exc

    posts = list((await session.scalars(select(Post))).all())
    match = find_best_match(face.encoding, posts, settings.face_match_tolerance)
    if match is None:
        session.add(ScanLog(provider=face.provider, status="no_match"))
        await session.commit()
        raise AppError(
            "No match was found in the authorized local dataset.",
            "NO_MATCH",
            404,
        )

    post, distance = match
    session.add(
        ScanLog(
            matched_post_id=post.id,
            distance=distance,
            provider=face.provider,
            status="matched",
        )
    )
    await session.commit()
    top, right, bottom, left = face.box
    return ScanResponse(
        match=post_response(post),
        distance=distance,
        tolerance=settings.face_match_tolerance,
        face_provider=face.provider,
        face_box=FaceBox(
            top=top,
            right=right,
            bottom=bottom,
            left=left,
            image_width=face.image_width,
            image_height=face.image_height,
        ),
    )


@app.post(
    "/api/verify/{post_id}",
    response_model=ChainRegisterResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def register_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
    _admin: AccessSession = Depends(require_admin),
) -> ChainRegisterResponse:
    post = await require_post(post_id, session)
    try:
        content_hash = await asyncio.to_thread(compute_post_hash, post)
    except OSError as exc:
        raise AppError("The local post image cannot be read.", "IMAGE_NOT_FOUND", 404) from exc

    chain = ChainService()
    metadata_uri = f"face-verify-chain://posts/{post.id}"
    try:
        receipt = await asyncio.to_thread(chain.register_hash, content_hash, metadata_uri)
        chain_id = await asyncio.to_thread(lambda: chain.web3.eth.chain_id)
    except HashAlreadyRegisteredError as exc:
        raise AppError(str(exc), "HASH_ALREADY_REGISTERED", 409) from exc
    except ChainServiceError as exc:
        raise AppError(str(exc), "CHAIN_UNAVAILABLE", 503) from exc

    tx_hash = receipt["transactionHash"].hex()
    if not tx_hash.startswith("0x"):
        tx_hash = f"0x{tx_hash}"
    record = VerificationRecord(
        post_id=post.id,
        content_hash=hash_hex(content_hash),
        tx_hash=tx_hash,
        block_number=int(receipt["blockNumber"]),
        contract_address=chain.contract_address,
        status="confirmed",
    )
    session.add(record)
    await session.commit()

    return ChainRegisterResponse(
        post_id=post.id,
        content_hash=record.content_hash,
        tx_hash=record.tx_hash,
        block_number=record.block_number,
        contract_address=record.contract_address,
        explorer_url=explorer_url(record.tx_hash, chain_id),
    )


@app.get(
    "/api/verify/{post_id}/status",
    response_model=VerificationStatusResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def verification_status(
    post_id: int, session: AsyncSession = Depends(get_session)
) -> VerificationStatusResponse:
    post = await require_post(post_id, session)
    latest = await session.scalar(
        select(VerificationRecord)
        .where(VerificationRecord.post_id == post_id)
        .order_by(VerificationRecord.verified_at.desc())
        .limit(1)
    )
    try:
        local_hash = await asyncio.to_thread(compute_post_hash, post)
    except OSError as exc:
        raise AppError("The local post image cannot be read.", "IMAGE_NOT_FOUND", 404) from exc

    if latest is None:
        return VerificationStatusResponse(
            post_id=post_id,
            verified=False,
            local_hash=hash_hex(local_hash),
            on_chain_hash=None,
            on_chain_record=None,
            status="not_registered",
        )

    registered_hash = bytes.fromhex(latest.content_hash.removeprefix("0x"))
    try:
        on_chain = await asyncio.to_thread(ChainService().verify_hash, registered_hash)
    except ChainServiceError as exc:
        raise AppError(str(exc), "CHAIN_UNAVAILABLE", 503) from exc

    verified = on_chain is not None and local_hash == registered_hash
    on_chain_record = (
        OnChainRecord(
            submitter=on_chain.submitter,
            timestamp=on_chain.timestamp,
            metadata_uri=on_chain.metadata_uri,
            content_hash=latest.content_hash,
        )
        if on_chain
        else None
    )
    return VerificationStatusResponse(
        post_id=post_id,
        verified=verified,
        local_hash=hash_hex(local_hash),
        on_chain_hash=latest.content_hash if on_chain else None,
        on_chain_record=on_chain_record,
        status="verified" if verified else "mismatch",
    )
