from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Protocol, TypeVar

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

class FaceServiceError(ValueError):
    """Base error for invalid or unusable face images."""


class InvalidImageError(FaceServiceError):
    pass


class FaceNotFoundError(FaceServiceError):
    pass


class MultipleFacesFoundError(FaceServiceError):
    pass


class FaceCandidate(Protocol):
    face_encoding: bytes


CandidateT = TypeVar("CandidateT", bound=FaceCandidate)


@dataclass(frozen=True)
class FaceResult:
    encoding: np.ndarray
    box: tuple[int, int, int, int]  # top, right, bottom, left
    provider: str
    image_width: int
    image_height: int


def _load_rgb(image_bytes: bytes) -> np.ndarray:
    if not image_bytes:
        raise InvalidImageError("The uploaded image is empty.")
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((2048, 2048))
            return np.asarray(image)
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("The upload is not a readable image.") from exc


def _encode_with_face_recognition(
    rgb: np.ndarray, *, require_single: bool = False
) -> FaceResult | None:
    try:
        import face_recognition
    except ImportError:
        return None

    locations = face_recognition.face_locations(rgb, model="hog")
    if not locations:
        raise FaceNotFoundError("No face was found in the image.")
    if require_single and len(locations) != 1:
        raise MultipleFacesFoundError(
            "Use an image containing exactly one clearly visible face."
        )

    box = max(locations, key=lambda item: (item[2] - item[0]) * (item[1] - item[3]))
    encodings = face_recognition.face_encodings(rgb, [box])
    if not encodings:
        raise FaceNotFoundError("A face was detected, but an encoding could not be created.")

    height, width = rgb.shape[:2]
    return FaceResult(
        encoding=np.asarray(encodings[0], dtype=np.float32),
        box=tuple(int(value) for value in box),
        provider="face_recognition",
        image_width=width,
        image_height=height,
    )


def _fallback_descriptor(rgb: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    top, right, bottom, left = box
    crop = Image.fromarray(rgb[top:bottom, left:right]).convert("L").resize((16, 8))
    descriptor = np.asarray(crop, dtype=np.float32).reshape(-1)
    descriptor -= float(descriptor.mean())
    norm = float(np.linalg.norm(descriptor))
    return descriptor / norm if norm else descriptor


def _encode_with_mediapipe(
    rgb: np.ndarray, *, require_single: bool = False
) -> FaceResult:
    try:
        import mediapipe as mp
    except ImportError as exc:
        raise FaceServiceError(
            "No face backend is installed. Install face-recognition or mediapipe."
        ) from exc

    height, width = rgb.shape[:2]
    with mp.solutions.face_detection.FaceDetection(
        model_selection=1, min_detection_confidence=0.5
    ) as detector:
        output = detector.process(rgb)

    if not output.detections:
        raise FaceNotFoundError("No face was found in the image.")
    if require_single and len(output.detections) != 1:
        raise MultipleFacesFoundError(
            "Use an image containing exactly one clearly visible face."
        )

    detection = max(
        output.detections,
        key=lambda item: item.location_data.relative_bounding_box.width
        * item.location_data.relative_bounding_box.height,
    )
    relative = detection.location_data.relative_bounding_box
    left = max(0, int(relative.xmin * width))
    top = max(0, int(relative.ymin * height))
    right = min(width, int((relative.xmin + relative.width) * width))
    bottom = min(height, int((relative.ymin + relative.height) * height))
    if right <= left or bottom <= top:
        raise FaceNotFoundError("The detected face bounds were invalid.")

    box = (top, right, bottom, left)
    return FaceResult(
        encoding=_fallback_descriptor(rgb, box),
        box=box,
        provider="mediapipe",
        image_width=width,
        image_height=height,
    )


def encode_face_with_box(
    image_bytes: bytes, *, require_single: bool = False
) -> FaceResult:
    rgb = _load_rgb(image_bytes)
    preferred = os.getenv("FACE_BACKEND", "auto").lower()
    if preferred not in {"auto", "face_recognition", "mediapipe"}:
        raise FaceServiceError("FACE_BACKEND must be auto, face_recognition, or mediapipe.")

    if preferred != "mediapipe":
        result = _encode_with_face_recognition(rgb, require_single=require_single)
        if result is not None:
            return result
        if preferred == "face_recognition":
            raise FaceServiceError("face_recognition is selected but is not installed.")

    return _encode_with_mediapipe(rgb, require_single=require_single)


def encode_face(image_bytes: bytes) -> np.ndarray:
    return encode_face_with_box(image_bytes).encoding


def serialize_encoding(encoding: np.ndarray) -> bytes:
    stream = io.BytesIO()
    np.save(stream, np.asarray(encoding, dtype=np.float32), allow_pickle=False)
    return stream.getvalue()


def deserialize_encoding(value: bytes) -> np.ndarray:
    return np.load(io.BytesIO(value), allow_pickle=False).astype(np.float32)


def face_model_version(provider: str) -> str:
    if provider == "face_recognition":
        return "dlib-128-v1"
    if provider == "mediapipe":
        return "mediapipe-crop-128-demo-v1"
    return f"{provider}-unknown"


def face_distance(first: np.ndarray, second: np.ndarray) -> float | None:
    left = np.asarray(first, dtype=np.float32)
    right = np.asarray(second, dtype=np.float32)
    if left.shape != right.shape:
        return None
    return float(np.linalg.norm(left - right))


def find_best_match(
    query_encoding: np.ndarray,
    posts: list[CandidateT],
    tolerance: float | None = None,
) -> tuple[CandidateT, float] | None:
    threshold = tolerance if tolerance is not None else float(
        os.getenv("FACE_MATCH_TOLERANCE", "0.6")
    )
    candidates: list[tuple[CandidateT, float]] = []
    query = np.asarray(query_encoding, dtype=np.float32)

    for post in posts:
        stored = deserialize_encoding(post.face_encoding)
        if stored.shape != query.shape:
            continue
        candidates.append((post, float(np.linalg.norm(stored - query))))

    if not candidates:
        return None
    best = min(candidates, key=lambda item: item[1])
    return best if best[1] <= threshold else None
