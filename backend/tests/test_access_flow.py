from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from app import access_api
from app.auth_service import hash_password, verify_password
from app.face_service import FaceResult, MultipleFacesFoundError
from app.main import app


def face_result(value: float = 0.02) -> FaceResult:
    return FaceResult(
        encoding=np.full(128, value, dtype=np.float32),
        box=(10, 110, 130, 10),
        provider="face_recognition",
        image_width=160,
        image_height=160,
    )


def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/admin/login",
        json={"email": "admin@faceverify.local", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_password_hash_is_salted_and_verifiable() -> None:
    encoded = hash_password("correct horse battery staple")
    assert "correct horse battery staple" not in encoded
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_admin_login_rejects_invalid_credentials() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/admin/login",
            json={"email": "admin@faceverify.local", "password": "wrong"},
        )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


def test_enroll_authenticate_deactivate_and_logout(monkeypatch) -> None:
    monkeypatch.setattr(
        access_api,
        "encode_face_with_box",
        lambda _payload, require_single=True: face_result(),
    )

    with TestClient(app) as client:
        assert client.get("/api/admin/members").status_code == 401
        headers = admin_headers(client)

        enrollment = client.post(
            "/api/admin/members",
            headers=headers,
            data={
                "member_code": "EMP-1042",
                "full_name": "Aarav Sharma",
                "email": "aarav@example.test",
                "department": "Product",
                "consent_confirmed": "true",
            },
            files={"image": ("aarav.jpg", b"fake-image", "image/jpeg")},
        )
        assert enrollment.status_code == 201, enrollment.text
        member = enrollment.json()
        assert member["member_code"] == "EMP-1042"
        assert member["is_active"] is True
        assert "face_encoding" not in member

        duplicate = client.post(
            "/api/admin/members",
            headers=headers,
            data={
                "member_code": "EMP-2042",
                "full_name": "Different Person",
                "email": "different@example.test",
                "department": "Finance",
                "consent_confirmed": "true",
            },
            files={"image": ("duplicate.jpg", b"same-face", "image/jpeg")},
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == "FACE_ALREADY_ENROLLED"

        unknown = client.post(
            "/api/auth/face",
            data={"member_code": "UNKNOWN"},
            files={"image": ("login.jpg", b"same-face", "image/jpeg")},
        )
        assert unknown.status_code == 401
        assert unknown.json()["code"] == "FACE_AUTH_FAILED"

        authenticated = client.post(
            "/api/auth/face",
            data={"member_code": "EMP-1042"},
            files={"image": ("login.jpg", b"fresh-capture", "image/jpeg")},
        )
        assert authenticated.status_code == 200, authenticated.text
        member_token = authenticated.json()["access_token"]
        member_headers = {"Authorization": f"Bearer {member_token}"}
        assert client.get("/api/auth/me", headers=member_headers).status_code == 200

        logout = client.post("/api/auth/logout", headers=member_headers)
        assert logout.status_code == 200
        assert client.get("/api/auth/me", headers=member_headers).status_code == 401

        deactivated = client.patch(
            f"/api/admin/members/{member['id']}/status",
            headers=headers,
            json={"is_active": False},
        )
        assert deactivated.status_code == 200
        assert deactivated.json()["is_active"] is False
        blocked = client.post(
            "/api/auth/face",
            data={"member_code": "EMP-1042"},
            files={"image": ("login.jpg", b"fresh-capture", "image/jpeg")},
        )
        assert blocked.status_code == 401
        assert blocked.json()["code"] == "FACE_AUTH_FAILED"


def test_enrollment_rejects_multiple_faces(monkeypatch) -> None:
    def multiple(_payload, require_single=True):
        raise MultipleFacesFoundError("Use an image containing exactly one clearly visible face.")

    monkeypatch.setattr(access_api, "encode_face_with_box", multiple)
    with TestClient(app) as client:
        response = client.post(
            "/api/admin/members",
            headers=admin_headers(client),
            data={
                "member_code": "EMP-3000",
                "full_name": "Multiple Face Test",
                "email": "multiple@example.test",
                "department": "QA",
                "consent_confirmed": "true",
            },
            files={"image": ("group.jpg", b"group", "image/jpeg")},
        )
    assert response.status_code == 400
    assert response.json()["code"] == "MULTIPLE_FACES"
