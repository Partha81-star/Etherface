from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import Post


def canonical_metadata(post: Post) -> bytes:
    timestamp = post.timestamp.isoformat()
    metadata = {
        "author": post.author,
        "caption": post.caption,
        "source_url": post.source_url,
        "timestamp": timestamp,
    }
    return json.dumps(
        metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def compute_post_hash(post: Post) -> bytes:
    image_bytes = Path(post.image_path).read_bytes()
    digest = hashlib.sha256()
    digest.update(image_bytes)
    digest.update(canonical_metadata(post))
    return digest.digest()


def hash_hex(value: bytes) -> str:
    return f"0x{value.hex()}"
