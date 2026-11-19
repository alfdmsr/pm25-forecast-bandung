"""Memuat model dari GitHub dan membuat prakiraan. Dipakai oleh API dan aplikasi Streamlit."""
import json
import tempfile
import urllib.request
from pathlib import Path

import joblib

from src.features import STASIUN, fitur_dari_input, kategori_pm25

GITHUB_RAW = "https://raw.githubusercontent.com/alfdmsr/pm25-forecast-bandung/main"

# Batas masukan yang masih masuk akal untuk Bandung
BATAS = {
    "pm25": (0, 500),
    "suhu": (5, 40),
    "kelembaban": (0, 100),
    "kecepatan_angin": (0, 30),
    "arah_angin": (0, 360),
    "curah_hujan": (0, 150),
}

NAMA = {
    "pm25": "PM2.5", "suhu": "Suhu", "kelembaban": "Kelembapan",
    "kecepatan_angin": "Kecepatan angin", "arah_angin": "Arah angin", "curah_hujan": "Curah hujan",
}

SARAN = {
    "baik": "Udara baik. Aman untuk beraktivitas di luar ruangan.",
    "sedang": "Udara sedang. Kelompok sensitif sebaiknya tidak terlalu lama beraktivitas berat di luar.",
    "waspada": "Udara berpotensi tidak sehat. Penderita asma sebaiknya menyiapkan masker.",
    "tidak sehat": "Udara tidak sehat. Pakai masker, kurangi aktivitas di luar, dan tutup jendela.",
}


def muat_model(github_raw=GITHUB_RAW):
    """Unduh model.joblib dan metadata.json dari repo GitHub, lalu muat."""
    folder = Path(tempfile.gettempdir()) / "pm25_artifacts"
    folder.mkdir(exist_ok=True)
    for nama in ["model.joblib", "metadata.json"]:
        urllib.request.urlretrieve(f"{github_raw}/artifacts/{nama}", folder / nama)
    model = joblib.load(folder / "model.joblib")
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    return model, metadata


def cek_masukan(masukan):
    """Kembalikan daftar pesan galat. Daftar kosong berarti masukan aman dipakai."""
    galat = []
    if masukan.get("stasiun") not in STASIUN:
        galat.append(f"Stasiun harus salah satu dari: {', '.join(STASIUN)}.")
    if not masukan.get("waktu"):
        galat.append("Waktu wajib diisi.")
    for kolom, (bawah, atas) in BATAS.items():
        nilai = masukan.get(kolom)
        if nilai is None:
            galat.append(f"{NAMA[kolom]} wajib diisi.")
        elif not bawah <= nilai <= atas:
            galat.append(f"{NAMA[kolom]} {nilai} di luar rentang wajar ({bawah} sampai {atas}).")
    return galat


def prakirakan(model, metadata, masukan):
    """Prakiraan PM2.5 tiga jam lagi dari kondisi saat ini."""
    galat = cek_masukan(masukan)
    if galat:
        raise ValueError(" ".join(galat))

    x = fitur_dari_input(**masukan)
    nilai = max(0.0, float(model.predict(x[metadata["fitur_masukan"]])[0]))
    kategori = kategori_pm25(nilai)
    peringatan = nilai > metadata["threshold"]["peringatan_ugm3"]

    if kategori == "tidak sehat":
        saran = SARAN["tidak sehat"]
    elif peringatan:
        saran = SARAN["waspada"]
    else:
        saran = SARAN[kategori]

    catatan = None
    if masukan["pm25"] > metadata["rentang_pm25_latih"][1]:
        catatan = "PM2.5 saat ini lebih tinggi dari data latih, jadi prakiraan kurang dapat dipercaya."

    return {
        "prakiraan_pm25": round(nilai, 1),
        "kategori": kategori,
        "peringatan": bool(peringatan),
        "saran": saran,
        "catatan": catatan,
    }
