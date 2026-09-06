from __future__ import annotations

import hashlib
import io
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.chain_service import ChainService
from app.content_service import compute_post_hash
from app.face_service import encode_face_with_box, find_best_match, serialize_encoding
from app.main import app
from app.models import Post


def png_bytes() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (12, 12), (90, 130, 160)).save(stream, format="PNG")
    return stream.getvalue()


def test_face_encoding_on_known_image(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = np.linspace(-0.5, 0.5, 128, dtype=np.float32)
    stub = SimpleNamespace(
        face_locations=lambda _rgb, model: [(1, 10, 10, 1)],
        face_encodings=lambda _rgb, _boxes: [expected],
    )
    monkeypatch.setitem(sys.modules, "face_recognition", stub)

    result = encode_face_with_box(png_bytes())

    np.testing.assert_allclose(result.encoding, expected)
    assert result.box == (1, 10, 10, 1)
    assert result.provider == "face_recognition"


def test_best_match_uses_closest_authorized_encoding() -> None:
    query = np.zeros(128, dtype=np.float32)
    close = SimpleNamespace(face_encoding=serialize_encoding(np.full(128, 0.01)))
    far = SimpleNamespace(face_encoding=serialize_encoding(np.full(128, 0.2)))

    result = find_best_match(query, [far, close], tolerance=0.6)

    assert result is not None
    assert result[0] is close
    assert result[1] == pytest.approx(np.sqrt(128) * 0.01)


def test_content_hash_covers_image_and_metadata(tmp_path) -> None:
    image = tmp_path / "owned.jpg"
    image.write_bytes(b"authorized image bytes")
    post = Post(
        id=1,
        image_path=str(image),
        caption="Original caption",
        author="Owner",
        source_url="https://example.test/post/1",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        face_encoding=b"unused",
    )
    first = compute_post_hash(post)
    assert len(first) == 32

    post.caption = "Tampered caption"
    assert compute_post_hash(post) != first
    post.caption = "Original caption"
    image.write_bytes(b"modified image bytes")
    assert compute_post_hash(post) != first


def test_scan_rejects_non_image_with_structured_error() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/scan", files={"image": ("notes.txt", b"not an image", "text/plain")}
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Upload a JPEG, PNG, or WebP image.",
        "code": "INVALID_IMAGE_TYPE",
    }


@pytest.mark.chain
@pytest.mark.skipif(
    os.getenv("RUN_CHAIN_TESTS") != "1",
    reason="Set RUN_CHAIN_TESTS=1 with a deployed local contract to run this test.",
)
def test_register_and_verify_against_local_chain() -> None:
    service = ChainService()
    content_hash = hashlib.sha256(os.urandom(32)).digest()
    receipt = service.register_hash(content_hash, "face-verify-chain://tests/1")
    record = service.verify_hash(content_hash)

    assert int(receipt["status"]) == 1
    assert record is not None
    assert record.metadata_uri == "face-verify-chain://tests/1"
