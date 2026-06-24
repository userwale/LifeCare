"""
app/ai/pipeline.py – FastAPI-friendly wrapper around the Model_IA pipeline.

Loads all three models once at startup (lazy singleton) and exposes a
single `analyze_frame` function that returns a structured result dict.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# ── Make Model_IA importable ──────────────────────────────────────────────────
_MODEL_IA_ROOT = Path(__file__).resolve().parents[3] / "Model_IA"
if str(_MODEL_IA_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODEL_IA_ROOT))

from app.config import settings  # noqa: E402

# ── Types ─────────────────────────────────────────────────────────────────────

@dataclass
class PostureResult:
    posture: str                       # "GOOD" | "BAD"
    disease: Optional[str] = None      # e.g. "Lombalgie" – only when posture == BAD
    confidence: Optional[float] = None # 0–100 %
    error: Optional[str] = None        # Set if analysis failed


# ── Singleton model holder ────────────────────────────────────────────────────

class _ModelHolder:
    _instance: "_ModelHolder | None" = None

    def __init__(self) -> None:
        self._yolo = None
        self._posture_model = None
        self._posture_backend: str = ""
        self._feat_cols = None
        self._disease_model = None
        self._disease_labels: list[str] = []
        self._loaded = False

    @classmethod
    def get(cls) -> "_ModelHolder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self) -> None:
        """Load all AI models. Call once at application startup."""
        if self._loaded:
            return

        # Import pipeline helpers from Model_IA
        from full_test_pipeline import (  # type: ignore[import]
            load_disease_model,
            load_posture_model,
            load_yolo,
        )

        self._yolo = load_yolo(settings.yolo_model_path)
        self._posture_model, self._posture_backend, self._feat_cols = load_posture_model(
            settings.posture_model_path
        )
        self._disease_model, self._disease_labels = load_disease_model(
            settings.disease_model_path
        )
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded


# Expose a module-level accessor for convenience
def get_model_holder() -> _ModelHolder:
    return _ModelHolder.get()


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_frame(frame: np.ndarray) -> PostureResult:
    """
    Run the full posture → disease pipeline on a single BGR frame.

    Parameters
    ----------
    frame : np.ndarray
        BGR image array (e.g. from cv2.imread or a decoded video frame).

    Returns
    -------
    PostureResult
        Structured result with posture label, optional disease and confidence.
    """
    import torch

    from full_test_pipeline import (  # type: ignore[import]
        extract_features,
        extract_keypoints,
        predict_disease,
        predict_posture,
    )

    holder = get_model_holder()
    if not holder.is_loaded:
        holder.load()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    try:
        xyn, conf = extract_keypoints(holder._yolo, frame)
        features = extract_features(xyn, conf)

        posture_pred = predict_posture(
            holder._posture_model,
            holder._posture_backend,
            holder._feat_cols,
            features,
            device,
        )

        if posture_pred == 0:
            return PostureResult(posture="GOOD")

        disease_name, confidence = predict_disease(
            holder._disease_model,
            features,
            holder._disease_labels,
        )
        return PostureResult(posture="BAD", disease=disease_name, confidence=confidence)

    except Exception as exc:  # noqa: BLE001
        return PostureResult(posture="UNKNOWN", error=str(exc))


def analyze_image_path(image_path: str | Path) -> PostureResult:
    """Convenience wrapper: load an image from disk and analyze it."""
    frame = cv2.imread(str(image_path))
    if frame is None:
        return PostureResult(posture="UNKNOWN", error=f"Cannot read image: {image_path}")
    return analyze_frame(frame)
