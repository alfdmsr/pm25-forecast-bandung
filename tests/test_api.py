# Tes HTTP API dengan artefak palsu (tidak mengunduh model).

from src.features import FITUR


def test_status(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "versi_model": "9.9.9"}


def test_metadata(client):
    r = client.get("/metadata")
    assert r.status_code == 200
    assert r.json()["fitur_masukan"] == FITUR


def test_predict_mengembalikan_lima_kunci(client, masukan):
    r = client.post("/predict", json=masukan)

    assert r.status_code == 200
    data = r.json()
    assert set(data) == {"prakiraan_pm25", "kategori", "peringatan", "saran", "catatan"}
    assert data["prakiraan_pm25"] == 50.0        # nilai bawaan ModelPalsu


def test_predict_stasiun_di_luar_daftar_422(client, masukan):
    masukan["stasiun"] = "Cimahi"
    assert client.post("/predict", json=masukan).status_code == 422


def test_predict_nilai_di_luar_batas_422(client, masukan):
    masukan["pm25"] = 900
    assert client.post("/predict", json=masukan).status_code == 422


def test_predict_kolom_kurang_422(client, masukan):
    masukan.pop("suhu")
    assert client.post("/predict", json=masukan).status_code == 422
