"""
tests/test_ai_pipeline.py – Integration tests for the AI pipeline.

These tests verify that:
  1. The model files exist at the expected paths.
  2. Feature extraction works correctly on a synthetic keypoint array.
  3. The full pipeline can be imported and model-holder singleton works.

Run with:
    pytest tests/test_ai_pipeline.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# ── Make Model_IA importable ──────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]           # backend/
_MODEL_IA = _ROOT.parent / "Model_IA"
if str(_MODEL_IA) not in sys.path:
    sys.path.insert(0, str(_MODEL_IA))


# ─────────────────────────────────────────────────────────────────────────────
# 1. Model file existence
# ─────────────────────────────────────────────────────────────────────────────

class TestModelFilesExist:
    """Verify that the trained model artefacts are present on disk."""

    def test_yolo_model_exists(self):
        path = _MODEL_IA / "best.pt"
        assert path.exists(), f"YOLO model not found at {path}"

    def test_posture_model_exists(self):
        path = _MODEL_IA / "rf_model.pkl"
        assert path.exists(), f"Posture RF model not found at {path}"

    def test_disease_model_exists(self):
        path = _MODEL_IA / "disease_rf_model.pkl"
        assert path.exists(), f"Disease RF model not found at {path}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Feature extraction (posture_features.py)
# ─────────────────────────────────────────────────────────────────────────────

class TestPostureFeatures:
    """Unit-tests for the feature-extraction module."""

    def test_import_posture_features(self):
        from posture_features import build_feature_vector, FEATURE_DIM  # type: ignore
        assert FEATURE_DIM == 5

    def test_build_feature_vector_shape(self):
        from posture_features import build_feature_vector  # type: ignore

        # Create a plausible set of normalised COCO keypoints (17 × 2)
        rng = np.random.default_rng(42)
        xyn = rng.uniform(0.1, 0.9, size=(17, 2)).astype(np.float32)
        conf = np.ones(17, dtype=np.float32)

        vec = build_feature_vector(xyn, conf)
        assert vec.shape == (5,), f"Expected shape (5,), got {vec.shape}"

    def test_build_feature_vector_values_in_range(self):
        from posture_features import build_feature_vector  # type: ignore

        rng = np.random.default_rng(0)
        xyn = rng.uniform(0.05, 0.95, size=(17, 2)).astype(np.float32)
        conf = np.ones(17, dtype=np.float32) * 0.9

        vec = build_feature_vector(xyn, conf)
        # Angles are in [0, pi]
        assert np.all(vec >= 0.0), "All angles should be non-negative"
        assert np.all(vec <= np.pi + 1e-5), "All angles should be ≤ π"

    def test_vector_to_feature_dict(self):
        from posture_features import vector_to_feature_dict, ENGINEERED_NAMES  # type: ignore

        vec = np.array([1.0, 0.5, 2.0, 1.2, 0.8], dtype=np.float32)
        d = vector_to_feature_dict(vec)
        assert set(d.keys()) == set(ENGINEERED_NAMES)

    def test_parse_largest_person_no_detections(self):
        """parse_largest_person_from_yolo_result must handle empty results."""
        from posture_features import parse_largest_person_from_yolo_result  # type: ignore

        class FakeResult:
            boxes = None

        xyn, conf = parse_largest_person_from_yolo_result(FakeResult())
        assert xyn is None
        assert conf is None


# ─────────────────────────────────────────────────────────────────────────────
# 3. Settings & config loading
# ─────────────────────────────────────────────────────────────────────────────

class TestConfig:
    """Verify that settings load and model paths resolve correctly."""

    def test_settings_import(self):
        from app.config import settings  # type: ignore
        assert settings.app_name

    def test_yolo_path_resolves(self):
        from app.config import settings  # type: ignore
        # The path doesn't have to exist in CI; just check it resolves.
        assert isinstance(settings.yolo_model_path, Path)

    def test_sync_database_url_sqlite(self):
        from app.config import settings  # type: ignore
        if "sqlite" in settings.database_url:
            assert "aiosqlite" not in settings.sync_database_url


# ─────────────────────────────────────────────────────────────────────────────
# 4. FastAPI app smoke-test
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint():
    """The /health endpoint should return 200 without DB or AI models."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
