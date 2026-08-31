"""Render QA — magnitude gate.

Measures how much a rendered image actually differs from the base photo, so the
render job can detect a "near-copy" (model under-applied the edit) and retry with
progressive multi-step edits. Uses a normalized luminance difference on a small
downscaled grayscale image (structure-focused, lighting-tolerant).
"""
import io
import os

import numpy as np
import cv2
from PIL import Image

_SIZE = 96  # downscale for a fast, framing-level comparison


def _prep(img_bytes: bytes) -> np.ndarray:
    im = Image.open(io.BytesIO(img_bytes)).convert("L").resize((_SIZE, _SIZE))
    a = np.asarray(im, dtype=np.float32)
    # Normalize contrast so global brightness/encoding shifts don't dominate.
    a = (a - a.mean()) / (a.std() + 1e-6)
    return a


def change_score(base_bytes: bytes, out_bytes: bytes) -> float:
    """0.0 = visually identical, higher = more different. Typical body-comp
    edits land ~0.15-0.6; a near-copy is < ~0.08."""
    try:
        a, b = _prep(base_bytes), _prep(out_bytes)
        return float(np.mean(np.abs(a - b)))
    except Exception:
        # If decoding fails, don't block the pipeline — treat as "changed".
        return 1.0


# A visible change is expected when the body-fat delta is at least this many pts.
VISIBLE_THRESHOLD_BF = 4.0
# Below this score while a visible change was expected == near-copy -> retry.
NEAR_COPY_MAX = 0.08

# --- Identity (face-embedding) gate -----------------------------------------
# SFace cosine similarity: >= this == same identity (OpenCV-recommended 0.363).
IDENTITY_MIN = 0.363

_MODELS = os.path.join(os.path.dirname(__file__), "models")
_detector = None
_recognizer = None


def _load_face_models():
    global _detector, _recognizer
    if _recognizer is None:
        _detector = cv2.FaceDetectorYN.create(
            os.path.join(_MODELS, "yunet.onnx"), "", (320, 320), 0.6, 0.3, 5000)
        _recognizer = cv2.FaceRecognizerSF.create(
            os.path.join(_MODELS, "sface.onnx"), "")
    return _detector, _recognizer


def _bgr(img_bytes: bytes) -> np.ndarray:
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


def _largest_face(det, img):
    h, w = img.shape[:2]
    det.setInputSize((w, h))
    _, faces = det.detect(img)
    if faces is None or len(faces) == 0:
        return None
    # pick the largest by area (col 2*3 = w*h)
    return max(faces, key=lambda f: f[2] * f[3])


def _embedding(img_bytes: bytes):
    det, rec = _load_face_models()
    img = _bgr(img_bytes)
    face = _largest_face(det, img)
    if face is None:
        return None
    aligned = rec.alignCrop(img, face)
    return rec.feature(aligned)


def face_similarity(base_bytes: bytes, out_bytes: bytes):
    """SFace cosine similarity in [-1,1] between the two faces. Returns None if a
    face cannot be detected in either image (identity cannot be verified)."""
    try:
        _, rec = _load_face_models()
        fb = _embedding(base_bytes)
        fo = _embedding(out_bytes)
        if fb is None or fo is None:
            return None
        return float(rec.match(fb, fo, cv2.FaceRecognizerSF_FR_COSINE))
    except Exception:
        return None
