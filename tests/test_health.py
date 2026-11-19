# Tes endpoint /health di level aplikasi (tanpa Docker).

from src.features import FITUR


def test_health_ok(client):
    r = client.get("/health")

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["jumlah_fitur"] == len(FITUR)
    assert data["versi_model"] == "9.9.9"


def test_health_503_bila_model_dan_metadata_tidak_sinkron(buat_client, buat_model, meta):
    model = buat_model(50.0)
    model.n_features_in_ = 99                    # metadata tetap 16 fitur

    r = buat_client(model, meta).get("/health")

    assert r.status_code == 503
    assert "tidak sinkron" in r.json()["detail"]
