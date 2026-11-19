"""Aplikasi prakiraan PM2.5 untuk warga dan petugas dinas.

Jalankan dari folder utama repo:
    streamlit run app/ui/streamlit_app.py

Secara bawaan aplikasi memuat model langsung dari GitHub.
Jika variabel lingkungan PM25_API_URL diisi (misalnya http://127.0.0.1:8000),
prakiraan diminta ke API tersebut.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # agar folder src bisa di-import
from src.features import STASIUN
from src.predict import BATAS, cek_masukan, muat_model, prakirakan

API_URL = os.environ.get("PM25_API_URL")
WIB = timezone(timedelta(hours=7))
WARNA = {"baik": "green", "sedang": "orange", "tidak sehat": "red"}

st.set_page_config(page_title="Prakiraan PM2.5 Bandung", layout="centered")


@st.cache_resource
def ambil_model():
    return muat_model()


def minta_prakiraan(masukan):
    if API_URL:
        data = dict(masukan, waktu=masukan["waktu"].isoformat())
        r = requests.post(f"{API_URL}/predict", json=data, timeout=10)
        if r.status_code != 200:
            raise ValueError(r.json().get("detail"))
        return r.json()
    model, metadata = ambil_model()
    return prakirakan(model, metadata, masukan)


st.title("Prakiraan PM2.5 Bandung")
st.write("Masukkan kondisi udara saat ini untuk melihat prakiraan PM2.5 tiga jam lagi.")

sekarang = datetime.now(WIB)
with st.form("masukan"):
    stasiun = st.selectbox("Stasiun", STASIUN)
    kolom1, kolom2 = st.columns(2)
    tanggal = kolom1.date_input("Tanggal", sekarang.date())
    jam = kolom2.selectbox("Jam saat ini (WIB)", range(24), index=sekarang.hour, format_func=lambda j: f"{j:02d}:00")

    pm25 = st.number_input("PM2.5 saat ini (µg/m³)", value=None, step=1.0, placeholder="contoh: 35")
    kolom1, kolom2 = st.columns(2)
    suhu = kolom1.number_input("Suhu (°C)", value=24.0, step=0.5)
    kelembaban = kolom2.number_input("Kelembapan (%)", value=75.0, step=1.0)
    kecepatan_angin = kolom1.number_input("Kecepatan angin (m/detik)", value=1.5, step=0.1)
    arah_angin = kolom2.number_input("Arah angin (derajat, 0 = utara)", value=90.0, step=10.0)
    curah_hujan = st.number_input("Curah hujan jam ini (mm)", value=0.0, step=0.5)
    kirim = st.form_submit_button("Prakirakan")

if kirim:
    waktu = datetime.combine(tanggal, datetime.min.time()).replace(hour=jam)
    masukan = {
        "stasiun": stasiun, "waktu": waktu, "pm25": pm25, "suhu": suhu, "kelembaban": kelembaban,
        "kecepatan_angin": kecepatan_angin, "arah_angin": arah_angin, "curah_hujan": curah_hujan,
    }

    galat = cek_masukan(masukan)
    for pesan in galat:
        st.error(pesan)

    if not galat:
        try:
            hasil = minta_prakiraan(masukan)
        except Exception as e:
            hasil = None
            st.error(f"Prakiraan gagal dibuat: {e}")

        if hasil:
            jam_target = (waktu + timedelta(hours=3)).strftime("%H:%M")
            st.subheader(f"Prakiraan pukul {jam_target} WIB di {stasiun}")
            selisih = hasil["prakiraan_pm25"] - pm25
            st.metric("PM2.5 tiga jam lagi", f"{hasil['prakiraan_pm25']} µg/m³", f"{selisih:+.1f} dari sekarang",
                      delta_color="inverse")
            st.markdown(f"Kategori: :{WARNA[hasil['kategori']]}[**{hasil['kategori']}**]")
            if hasil["peringatan"]:
                st.warning(hasil["saran"])
            else:
                st.success(hasil["saran"])
            if hasil["catatan"]:
                st.info(hasil["catatan"])

with st.expander("Tentang model"):
    try:
        _, metadata = ambil_model()
        test = metadata["metrik"]["test"]
        st.write(
            f"Model: {metadata['algoritma']} (versi {metadata['versi_model']}). "
            f"Rata-rata selisih prakiraan di data uji {test['model']['MAE']} µg/m³, "
            f"dibanding {test['baseline_persistence']['MAE']} µg/m³ jika menganggap tiga jam lagi sama dengan sekarang. "
            f"Peringatan diberikan jika prakiraan di atas {metadata['threshold']['peringatan_ugm3']} µg/m³."
        )
    except Exception:
        st.write("Informasi model belum bisa dimuat.")
    st.caption("Data yang dipakai untuk melatih model adalah data sintetis untuk tugas kuliah.")
