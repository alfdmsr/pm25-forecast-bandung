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
from src.predict import cek_masukan, muat_model, prakirakan

API_URL = os.environ.get("PM25_API_URL")
WIB = timezone(timedelta(hours=7))
UNGU = "#9D6CFF"
WARNA = {"baik": "green", "sedang": "orange", "tidak sehat": "red"}
ARAH_ANGIN = {
    "Utara": 0, "Timur laut": 45, "Timur": 90, "Tenggara": 135,
    "Selatan": 180, "Barat daya": 225, "Barat": 270, "Barat laut": 315,
}

st.set_page_config(page_title="Prakiraan PM2.5 Bandung", layout="centered")

# Gaya tampilan: huruf, judul besar, label kecil, kartu statistik, dan footer ungu
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap');
html, body, [class*="st-"], p, label, input, button {{ font-family: 'DM Sans', sans-serif; }}
h1, h2, h3, h4, .judul, .angka {{ font-family: 'Space Grotesk', sans-serif !important; }}
.block-container {{ padding-top: 2.5rem; max-width: 720px; }}

.hero {{ display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1.5rem; }}
.tag {{ font-size: 12px; letter-spacing: .25em; color: {UNGU}; font-weight: 700; }}
.judul {{ font-size: 64px; font-weight: 700; line-height: 1; margin: .3rem 0; letter-spacing: -.02em; }}
.judul span {{ color: {UNGU}; }}
.sub {{ font-size: 15px; opacity: .75; max-width: 320px; }}
.lingkaran {{ flex: none; width: 140px; height: 140px; border-radius: 50%; background: {UNGU}; color: #111;
              display: flex; flex-direction: column; align-items: center; justify-content: center; }}
.lingkaran .angka {{ font-size: 48px; font-weight: 700; line-height: 1; }}
.lingkaran small {{ font-size: 11px; letter-spacing: .15em; font-weight: 700; }}

.statistik {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 2rem; }}
.statistik div {{ border: 1px solid #2c2c2c; border-radius: 6px; padding: 12px 14px; font-size: 11px;
                  letter-spacing: .12em; opacity: .9; }}
.statistik .angka {{ display: block; font-size: 24px; font-weight: 700; letter-spacing: 0; color: {UNGU}; }}

.label {{ font-size: 12px; letter-spacing: .2em; font-weight: 700; color: {UNGU}; margin: .4rem 0 .2rem; }}
.footer {{ background: {UNGU}; color: #111; border-radius: 8px; padding: 1.25rem 1.5rem; margin-top: 2.5rem; font-size: 14px; }}
.footer b {{ font-family: 'Space Grotesk', sans-serif; letter-spacing: .15em; font-size: 12px; }}
.footer p {{ margin: .4rem 0 0; color: #111; }}

@media (max-width: 600px) {{
  .judul {{ font-size: 46px; }}
  .lingkaran {{ width: 100px; height: 100px; }}
  .lingkaran .angka {{ font-size: 34px; }}
  .statistik {{ grid-template-columns: 1fr; }}
}}
</style>
""", unsafe_allow_html=True)


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


def skala_kategori(nilai):
    """Batang warna baik, sedang, tidak sehat, dengan penanda posisi prakiraan (skala 0 sampai 100)."""
    posisi = min(nilai, 100)
    return f"""
<div style="position:relative;margin:4px 0 24px">
  <div style="display:flex;height:10px;border-radius:5px;overflow:hidden">
    <div style="width:15.5%;background:#3fae5a"></div>
    <div style="width:39.5%;background:#e8a33a"></div>
    <div style="width:45%;background:#d9534f"></div>
  </div>
  <div style="position:absolute;top:-5px;left:{posisi}%;transform:translateX(-50%);width:4px;height:20px;
              border-radius:2px;background:#fff"></div>
  <div style="position:absolute;top:14px;left:0;font-size:12px;opacity:.7">0</div>
  <div style="position:absolute;top:14px;left:15.5%;transform:translateX(-50%);font-size:12px;opacity:.7">15,5</div>
  <div style="position:absolute;top:14px;left:55%;transform:translateX(-50%);font-size:12px;opacity:.7">55</div>
  <div style="position:absolute;top:14px;right:0;font-size:12px;opacity:.7">100+</div>
</div>"""


def label(teks):
    st.markdown(f'<div class="label">{teks}</div>', unsafe_allow_html=True)


# Bagian atas
try:
    _, metadata = ambil_model()
except Exception:
    metadata = None

st.markdown("""
<div class="hero">
  <div>
    <div class="tag">KOTA BANDUNG</div>
    <div class="judul">PM2.5<span>.</span></div>
    <div class="sub">Prakiraan kualitas udara tiga jam ke depan di lima stasiun pemantau.</div>
  </div>
  <div class="lingkaran"><span class="angka">+3</span><small>JAM</small></div>
</div>
""", unsafe_allow_html=True)

if metadata:
    test = metadata["metrik"]["test"]["model"]
    st.markdown(f"""
<div class="statistik">
  <div><span class="angka">5</span>STASIUN</div>
  <div><span class="angka">{test['MAE']:.1f}</span>RATA-RATA SELISIH (µg/m³)</div>
  <div><span class="angka">{test['recall_55'] * 100:.0f}%</span>JAM TIDAK SEHAT TERDETEKSI</div>
</div>
""", unsafe_allow_html=True)

# Form masukan
sekarang = datetime.now(WIB)
with st.form("masukan"):
    label("LOKASI DAN WAKTU")
    stasiun = st.selectbox("Stasiun", STASIUN)
    kolom1, kolom2 = st.columns(2)
    tanggal = kolom1.date_input("Tanggal", sekarang.date(), format="DD/MM/YYYY")
    jam = kolom2.selectbox("Jam saat ini (WIB)", range(24), index=sekarang.hour, format_func=lambda j: f"{j:02d}:00")

    label("KONDISI SAAT INI")
    pm25 = st.number_input("PM2.5 (µg/m³)", value=None, step=1.0, format="%.1f", placeholder="contoh: 35")
    kolom1, kolom2 = st.columns(2)
    suhu = kolom1.number_input("Suhu (°C)", value=24.0, step=0.5, format="%.1f")
    kelembaban = kolom2.number_input("Kelembapan (%)", value=75.0, step=1.0, format="%.0f")
    kecepatan_angin = kolom1.number_input("Kecepatan angin (m/detik)", value=1.5, step=0.1, format="%.1f")
    arah = kolom2.selectbox("Angin bertiup dari", list(ARAH_ANGIN), index=2)
    curah_hujan = st.number_input("Curah hujan satu jam terakhir (mm)", value=0.0, step=0.5, format="%.1f")

    kirim = st.form_submit_button("Prakirakan", type="primary", width="stretch")

# Hasil
if kirim:
    waktu = datetime.combine(tanggal, datetime.min.time()).replace(hour=jam)
    masukan = {
        "stasiun": stasiun, "waktu": waktu, "pm25": pm25, "suhu": suhu, "kelembaban": kelembaban,
        "kecepatan_angin": kecepatan_angin, "arah_angin": ARAH_ANGIN[arah], "curah_hujan": curah_hujan,
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
            with st.container(border=True):
                label(f"{stasiun.upper()}, PUKUL {jam_target} WIB")
                kolom1, kolom2 = st.columns([3, 2], vertical_alignment="center")
                selisih = hasil["prakiraan_pm25"] - pm25
                kolom1.metric("Prakiraan PM2.5 tiga jam lagi", f"{hasil['prakiraan_pm25']:.1f} µg/m³",
                              f"{selisih:+.1f} dari sekarang", delta_color="inverse")
                with kolom2:
                    st.badge(hasil["kategori"].capitalize(), color=WARNA[hasil["kategori"]])
                st.markdown(skala_kategori(hasil["prakiraan_pm25"]), unsafe_allow_html=True)

                if hasil["peringatan"]:
                    st.warning(hasil["saran"])
                else:
                    st.success(hasil["saran"])
                if hasil["catatan"]:
                    st.info(hasil["catatan"])

# Footer
if metadata:
    st.markdown(f"""
<div class="footer">
  <b>TENTANG MODEL</b>
  <p>{metadata['algoritma']} versi {metadata['versi_model']}. Peringatan diberikan jika prakiraan di atas
  {metadata['threshold']['peringatan_ugm3']} µg/m³. Kategori: baik sampai 15,5, sedang sampai 55,
  tidak sehat di atas 55 µg/m³.</p>
  <p>Model dilatih dengan data sintetis untuk tugas kuliah.</p>
</div>
""", unsafe_allow_html=True)
