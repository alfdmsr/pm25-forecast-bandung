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

# Rentang nilai yang ada di data latih (data/clean.csv). Di luar rentang ini model hanya menebak.
RENTANG_LATIH = {
    "pm25": (1, 128.4),
    "suhu": (12, 31.9),
    "kelembaban": (51, 100),
    "kecepatan_angin": (0.1, 7.9),
    "curah_hujan": (0, 24.9),
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
    try:
        for nama in ["model.joblib", "metadata.json"]:
            urllib.request.urlretrieve(f"{github_raw}/artifacts/{nama}", folder / nama)
    except Exception as e:
        raise RuntimeError(
            "Model tidak bisa diunduh dari GitHub. Periksa koneksi internet dan pastikan folder "
            "artifacts sudah ada di repo."
        ) from e
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
    if masukan.get("pm25") == 0:
        galat.append("PM2.5 0 biasanya berarti sensor gagal membaca. Isi dengan nilai yang terukur.")
    return galat


def prakirakan(model, metadata, masukan):
    """Prakiraan PM2.5 tiga jam lagi dari kondisi saat ini."""
    galat = cek_masukan(masukan)
    if galat:
        raise ValueError(" ".join(galat))

    x = fitur_dari_input(**masukan)
    nilai = max(0.0, float(model.predict(x[metadata["fitur_masukan"]])[0]))
    kategori = kategori_pm25(nilai)
    sudah_tidak_sehat = masukan["pm25"] > 55
    peringatan = nilai > metadata["threshold"]["peringatan_ugm3"] or sudah_tidak_sehat

    if kategori == "tidak sehat":
        saran = SARAN["tidak sehat"]
    elif peringatan:
        saran = SARAN["waspada"]
    else:
        saran = SARAN[kategori]
    if sudah_tidak_sehat:
        # Prakiraan boleh turun, tetapi warga perlu tahu bahwa udara saat ini sudah tidak sehat
        saran = "Saat ini udara sudah tidak sehat. Pakai masker, kurangi aktivitas di luar, dan tutup jendela."

    di_luar = [NAMA[k] if k == "pm25" else NAMA[k].lower()
               for k, (bawah, atas) in RENTANG_LATIH.items() if not bawah <= masukan[k] <= atas]
    catatan = None
    if masukan["pm25"] > RENTANG_LATIH["pm25"][1]:
        catatan = ("PM2.5 saat ini lebih tinggi dari semua data latih. Di data latih, PM2.5 setinggi ini "
                   "biasanya turun dalam beberapa jam, tetapi prakiraan untuk kondisi ini kurang dapat dipercaya.")
    elif di_luar:
        catatan = (f"Di luar rentang data latih: {', '.join(di_luar)}. Model belum pernah melihat kondisi ini, "
                   "jadi prakiraan kurang dapat dipercaya.")

    return {
        "prakiraan_pm25": round(nilai, 1),
        "kategori": kategori,
        "peringatan": bool(peringatan),
        "saran": saran,
        "catatan": catatan,
    }
