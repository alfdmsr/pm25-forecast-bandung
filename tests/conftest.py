from __future__ import annotations

import importlib
import sys

import numpy as np
import pytest

from src import predict as predict_mod
from src.features import FITUR, STASIUN


def metadata_palsu(**ubah):
    meta = {
        "versi_model": "9.9.9",
        "algoritma": "ModelPalsu",
        "fitur_masukan": list(FITUR),
        "stasiun": list(STASIUN),
        "rentang_pm25_latih": [1.0, 128.4],
        "threshold": {"peringatan_ugm3": 39},
        "metrik": {"test": {"model": {"MAE": 4.599, "recall_55": 0.937, "precision_55": 0.205}}},
    }
    meta.update(ubah)
    return meta


class ModelPalsu:
    """Model tiruan: selalu memprediksi satu nilai tetap."""

    def __init__(self, nilai=50.0):
        self.nilai = float(nilai)
        self.n_features_in_ = len(FITUR)
        self.diterima = None

    def predict(self, X):
        self.diterima = X
        return np.array([self.nilai], dtype=float)


@pytest.fixture
def masukan():
    """Masukan API yang valid, semuanya di dalam BATAS dan RENTANG_LATIH."""
    return {
        "stasiun": "Dago",
        "waktu": "2026-06-10T15:00:00",
        "pm25": 35.0,
        "suhu": 24.0,
        "kelembaban": 75.0,
        "kecepatan_angin": 1.5,
        "arah_angin": 90.0,
        "curah_hujan": 0.0,
    }


@pytest.fixture
def meta():
    return metadata_palsu()


@pytest.fixture
def model_palsu():
    return ModelPalsu(50.0)


@pytest.fixture
def buat_model():
    """Pabrik model: `buat_model(60.0)` -> model yang memprediksi 60.0."""
    return ModelPalsu


@pytest.fixture
def buat_client(monkeypatch):
    """Pabrik TestClient: `buat_client(model, meta)`."""

    def _buat(model, meta):
        monkeypatch.setattr(predict_mod, "muat_model", lambda *a, **k: (model, meta))
        sys.modules.pop("app.api.main", None)
        modul = importlib.import_module("app.api.main")

        from fastapi.testclient import TestClient

        return TestClient(modul.app)

    return _buat


@pytest.fixture
def client(buat_client, model_palsu, meta):
    return buat_client(model_palsu, meta)
