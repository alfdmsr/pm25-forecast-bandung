"""Tes smoke container: build image, nyalakan, tanya /health dan /predict.

Dilewati secara bawaan karena build pertama 5-8 menit. Jalankan dengan:

    JALANKAN_DOCKER=1 .venv/bin/python -m pytest tests/test_docker.py -q -s
"""

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid

import pytest

DOCKER = shutil.which("docker")
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

pytestmark = pytest.mark.skipif(
    DOCKER is None or os.environ.get("JALANKAN_DOCKER") != "1",
    reason="butuh Docker dan JALANKAN_DOCKER=1",
)

MASUKAN = {
    "stasiun": "Dago",
    "waktu": "2026-06-10T15:00:00",
    "pm25": 35,
    "suhu": 24,
    "kelembaban": 75,
    "kecepatan_angin": 1.5,
    "arah_angin": 90,
    "curah_hujan": 0,
}


def port_bebas():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def tunggu(url, batas=180):
    mulai = time.time()
    while time.time() - mulai < batas:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return json.loads(r.read())
        except Exception:
            time.sleep(2)
    raise AssertionError(f"{url} tidak siap dalam {batas} detik")


def kirim(url, muatan):
    req = urllib.request.Request(
        url,
        data=json.dumps(muatan).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read())


@pytest.fixture(scope="module")
def kontainer():
    tag = f"pm25-smoke:{uuid.uuid4().hex[:8]}"
    nama = f"pm25-smoke-{uuid.uuid4().hex[:8]}"
    port = port_bebas()

    subprocess.run([DOCKER, "build", "-t", tag, "."], cwd=AKAR, check=True)
    subprocess.run(
        [DOCKER, "run", "-d", "--name", nama,
         "-e", "LAYANAN=api", "-p", f"127.0.0.1:{port}:7860", tag],
        check=True, capture_output=True, text=True,
    )

    try:
        yield {"url": f"http://127.0.0.1:{port}", "nama": nama}
    finally:
        subprocess.run([DOCKER, "rm", "-f", nama], check=False, capture_output=True)
        subprocess.run([DOCKER, "rmi", "-f", tag], check=False, capture_output=True)


def test_health_di_dalam_container(kontainer):
    data = tunggu(f"{kontainer['url']}/health")

    assert data["status"] == "ok"
    assert data["jumlah_fitur"] == 16


def test_predict_di_dalam_container(kontainer):
    tunggu(f"{kontainer['url']}/health")
    status, hasil = kirim(f"{kontainer['url']}/predict", MASUKAN)

    assert status == 200
    assert 0 <= hasil["prakiraan_pm25"] <= 500
    assert hasil["kategori"] in {"baik", "sedang", "tidak sehat"}
    assert hasil["saran"]
    assert isinstance(hasil["peringatan"], bool)


def test_masukan_tidak_wajar_ditolak(kontainer):
    tunggu(f"{kontainer['url']}/health")

    with pytest.raises(urllib.error.HTTPError) as exc:
        kirim(f"{kontainer['url']}/predict", dict(MASUKAN, pm25=900))

    assert exc.value.code == 422


def test_container_berjalan_sebagai_user_1000(kontainer):
    """HF Spaces mensyaratkan container berjalan sebagai UID 1000, bukan root."""
    uid = subprocess.run(
        [DOCKER, "exec", kontainer["nama"], "id", "-u"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    assert uid == "1000"
