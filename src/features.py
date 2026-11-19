"""Fungsi pembuat fitur untuk prakiraan PM2.5 tiga jam ke depan.

Dipakai saat pelatihan (buat_fitur) dan saat prediksi di aplikasi (fitur_dari_input),
supaya fitur yang dipakai selalu sama.
"""
import numpy as np
import pandas as pd

STASIUN = ["Dago", "Soekarno-Hatta", "Cibeureum", "Antapani", "Ujungberung"]
CUACA = ["suhu_C", "kelembaban_pct", "kecepatan_angin_ms", "arah_angin_deg", "curah_hujan_mm"]

# Fitur kondisi saat ini. Semuanya bisa diisi pengguna aplikasi.
FITUR = [
    "pm25_ugm3", "suhu_C", "kelembaban_pct", "kecepatan_angin_ms", "curah_hujan_mm",
    "angin_sin", "angin_cos", "jam_sin", "jam_cos", "bulan_sin", "bulan_cos",
] + [f"st_{s}" for s in STASIUN]

# Riwayat PM2.5 (jam lalu). Hanya dipakai untuk perbandingan di notebook.
FITUR_RIWAYAT = ["pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_lag21", "pm25_lag24"]


def tambah_fitur_waktu(df):
    """Jam, bulan, dan arah angin diubah ke sin/cos supaya 23 dan 0, atau 359 derajat dan 1 derajat, berdekatan."""
    jam = df["waktu"].dt.hour
    bulan = df["waktu"].dt.month
    sudut = np.deg2rad(df["arah_angin_deg"])
    df["jam_sin"] = np.sin(2 * np.pi * jam / 24)
    df["jam_cos"] = np.cos(2 * np.pi * jam / 24)
    df["bulan_sin"] = np.sin(2 * np.pi * (bulan - 1) / 12)
    df["bulan_cos"] = np.cos(2 * np.pi * (bulan - 1) / 12)
    df["angin_sin"] = np.sin(sudut)
    df["angin_cos"] = np.cos(sudut)
    for s in STASIUN:
        df[f"st_{s}"] = (df["stasiun"] == s).astype(int)
    return df


def buat_fitur(df_clean):
    """Fitur dan target untuk data historis yang sudah bersih.

    Setiap stasiun diubah ke grid per jam yang lengkap dulu, supaya shift(1) berarti tepat 1 jam
    dan shift(-3) berarti tepat 3 jam, walaupun ada jam yang hilang di data.
    """
    bagian = []
    for stasiun, g in df_clean.groupby("stasiun"):
        g = g.set_index("waktu").sort_index()
        jam_asli = g.index
        g = g.asfreq("h")

        hasil = pd.DataFrame(index=g.index)
        hasil["stasiun"] = stasiun
        hasil["pm25_asli"] = g["pm25_ugm3"]                    # untuk baseline persistence
        hasil["target_pm25"] = g["pm25_ugm3"].shift(-3)        # PM2.5 tiga jam lagi

        terisi = g[["pm25_ugm3"] + CUACA].ffill(limit=2)       # data kosong 1-2 jam diisi nilai terakhir
        hasil[["pm25_ugm3"] + CUACA] = terisi
        for k in [1, 2, 3, 21, 24]:
            hasil[f"pm25_lag{k}"] = terisi["pm25_ugm3"].shift(k)

        bagian.append(hasil.loc[jam_asli])

    data = pd.concat(bagian).rename_axis("waktu").reset_index()
    data["target_time"] = data["waktu"] + pd.Timedelta(hours=3)
    return tambah_fitur_waktu(data)


def fitur_dari_input(stasiun, waktu, pm25, suhu, kelembaban, kecepatan_angin, arah_angin, curah_hujan):
    """Satu baris fitur dari masukan aplikasi."""
    df = pd.DataFrame([{
        "stasiun": stasiun, "waktu": pd.Timestamp(waktu), "pm25_ugm3": pm25, "suhu_C": suhu,
        "kelembaban_pct": kelembaban, "kecepatan_angin_ms": kecepatan_angin,
        "arah_angin_deg": arah_angin, "curah_hujan_mm": curah_hujan,
    }])
    return tambah_fitur_waktu(df)[FITUR]


def kategori_pm25(nilai):
    """Kategori PM2.5 mengikuti batas ISPU."""
    if nilai <= 15.5:
        return "baik"
    if nilai <= 55:
        return "sedang"
    return "tidak sehat"
