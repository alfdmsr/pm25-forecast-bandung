"""Kecocokan artefak yang di-commit dengan kode fitur.

Ini yang menangkap training-serving skew: kalau FITUR diubah tetapi model
tidak dilatih ulang, tes langsung gagal.
"""

import json
from pathlib import Path

import pytest

from src.features import FITUR, STASIUN

AKAR = Path(__file__).resolve().parents[1]
METADATA = AKAR / "artifacts" / "metadata.json"
MODEL = AKAR / "artifacts" / "model.joblib"


def baca_metadata():
    return json.loads(METADATA.read_text(encoding="utf-8"))


def test_berkas_artefak_ada():
    assert METADATA.exists(), "artifacts/metadata.json wajib ikut di-commit"
    assert MODEL.exists(), "artifacts/model.joblib wajib ikut di-commit"


def test_urutan_fitur_metadata_sama_dengan_kode():
    assert baca_metadata()["fitur_masukan"] == FITUR


def test_daftar_stasiun_metadata_sama_dengan_kode():
    assert baca_metadata()["stasiun"] == STASIUN


def test_metadata_punya_kunci_yang_dipakai_dashboard():
    meta = baca_metadata()

    assert {"versi_model", "algoritma", "threshold", "metrik"} <= set(meta)
    assert "peringatan_ugm3" in meta["threshold"]
    assert {"MAE", "recall_55"} <= set(meta["metrik"]["test"]["model"])


def test_model_bisa_dimuat_dan_jumlah_fitur_cocok():
    pytest.importorskip("sklearn")
    joblib = pytest.importorskip("joblib")

    model = joblib.load(MODEL)

    assert model.n_features_in_ == len(FITUR)
