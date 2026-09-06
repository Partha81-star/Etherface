from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from .database import SessionLocal, init_db
from .face_service import FaceServiceError, encode_face, serialize_encoding
from .models import Post


SEED_DIR = Path(__file__).resolve().parents[1] / "seed_images"
DEFAULT_MANIFEST = SEED_DIR / "posts.json"


def parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)


async def seed(manifest_path: Path) -> tuple[int, int]:
    await init_db()
    manifest_path = manifest_path.resolve()
    records = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Seed manifest must be a JSON array.")

    created = 0
    skipped = 0
    async with SessionLocal() as session:
        for record in records:
            image_path = (manifest_path.parent / record["image"]).resolve()
            if manifest_path.parent not in image_path.parents:
                raise ValueError(f"Image path escapes seed directory: {record['image']}")
            if not image_path.is_file():
                print(f"SKIP {record['image']}: file not found")
                skipped += 1
                continue

            existing = await session.scalar(
                select(Post).where(Post.image_path == str(image_path))
            )
            if existing:
                print(f"SKIP {record['image']}: already seeded")
                skipped += 1
                continue

            try:
                encoding = encode_face(image_path.read_bytes())
            except FaceServiceError as exc:
                print(f"SKIP {record['image']}: {exc}")
                skipped += 1
                continue

            session.add(
                Post(
                    image_path=str(image_path),
                    caption=record["caption"],
                    author=record["author"],
                    source_url=record["source_url"],
                    timestamp=parse_timestamp(record["timestamp"]),
                    face_encoding=serialize_encoding(encoding),
                )
            )
            created += 1
            print(f"ADD  {record['image']}")
        await session.commit()

    return created, skipped


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Seed authorized posts and face encodings")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    created, skipped = await seed(args.manifest)
    print(f"Seed complete: {created} added, {skipped} skipped")


if __name__ == "__main__":
    asyncio.run(async_main())
