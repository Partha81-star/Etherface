from __future__ import annotations

import os
from pathlib import Path


TEST_DATABASE = Path(__file__).resolve().parent / "test_face_verify.db"
if TEST_DATABASE.exists():
    TEST_DATABASE.unlink()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DATABASE.as_posix()}"
os.environ.setdefault("FACE_BACKEND", "face_recognition")
