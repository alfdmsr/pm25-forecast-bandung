# Tes src/features.py: pembuatan fitur, one-hot stasiun, dan kategori ISPU.

import numpy as np
import pandas as pd
import pytest

from src.features import (
    FITUR,
    STASIUN,
    buat_fitur,
    fitur_dari_input,
    kategori_pm25,
    tambah_fitur_waktu,
)

CUACA_DASAR = {
    "suhu_C": 24.0,
    "kelembaban_pct": 75.0,
    "kecepatan_angin_ms": 1.5,
    "arah_angin_deg": 90.0,
    "curah_hujan_mm": 0.0,
}


def baris(waktu, stasiun="Dago", pm25=20.0, **cuaca):
    return {
        "waktu": pd.Timestamp(waktu),
        "stasiun": stasiun,
        "pm25_ugm3": float(pm25),
        **{**CUACA_DASAR, **cuaca},
    }


def test_fitur_berisi_kolom_cuaca_waktu_dan_lima_stasiun():
    assert len(FITUR) == 16
    assert FITUR == [
        "pm25_ugm3", "suhu_C", "kelembaban_pct", "kecepatan_angin_ms", "curah_hujan_mm",
        "angin_sin", "angin_cos", "jam_sin", "jam_cos", "bulan_sin", "bulan_cos",
    ] + [f"st_{s}" for s in STASIUN]
    assert len(set(FITUR)) == len(FITUR)


def test_one_hot_stasiun_tepat_satu_yang_menyala():
    df = pd.DataFrame([baris("2026-06-10 15:00", stasiun="Soekarno-Hatta")])
    hasil = tambah_fitur_waktu(df)

    menyala = [s for s in STASIUN if hasil.loc[0, f"st_{s}"] == 1]

    assert menyala == ["Soekarno-Hatta"]


def test_jam_dan_bulan_dibuat_melingkar():
    df = pd.DataFrame([baris("2026-01-01 06:00")])      # jam 06, bulan Januari
    hasil = tambah_fitur_waktu(df)

    assert hasil.loc[0, "jam_sin"] == pytest.approx(1.0)
    assert hasil.loc[0, "jam_cos"] == pytest.approx(0.0, abs=1e-12)
    assert hasil.loc[0, "bulan_sin"] == pytest.approx(0.0, abs=1e-12)
    assert hasil.loc[0, "bulan_cos"] == pytest.approx(1.0)


def test_arah_angin_timur_dan_barat_berbeda_tanda():
    df = pd.DataFrame([
        baris("2026-06-10 12:00", arah_angin_deg=90.0),
        baris("2026-06-10 12:00", arah_angin_deg=270.0),
    ])
    hasil = tambah_fitur_waktu(df)

    assert hasil.loc[0, "angin_sin"] == pytest.approx(1.0)
    assert hasil.loc[1, "angin_sin"] == pytest.approx(-1.0)


def test_target_memakai_jarak_tiga_jam_walau_ada_jam_hilang():
    waktu = pd.date_range("2026-01-01 00:00", periods=10, freq="h")
    df = pd.DataFrame([baris(t, pm25=i) for i, t in enumerate(waktu)])
    df = df.drop(index=5).reset_index(drop=True)          # jam 05:00 hilang

    hasil = buat_fitur(df).set_index("waktu")

    # dari 03:00, tiga baris berikutnya adalah 07:00, tetapi target harus 06:00
    assert hasil.loc["2026-01-01 03:00", "target_pm25"] == 6.0
    assert hasil.loc["2026-01-01 00:00", "target_pm25"] == 3.0


def test_target_time_selalu_tambah_tiga_jam():
    waktu = pd.date_range("2026-01-01 00:00", periods=8, freq="h")
    hasil = buat_fitur(pd.DataFrame([baris(t) for t in waktu]))

    assert (hasil["target_time"] - hasil["waktu"] == pd.Timedelta(hours=3)).all()


def test_lubang_tiga_jam_hanya_diisi_dua_jam():
    waktu = pd.date_range("2026-01-01 00:00", periods=12, freq="h")
    df = pd.DataFrame([baris(t, pm25=10.0) for t in waktu])
    df = df.drop(index=[1, 2, 3]).reset_index(drop=True)  # 3 jam hilang berurutan

    hasil = buat_fitur(df).set_index("waktu")

    assert hasil.loc["2026-01-01 04:00", "pm25_lag2"] == 10.0   # 02:00 terisi
    assert pd.isna(hasil.loc["2026-01-01 04:00", "pm25_lag1"])  # 03:00 tetap kosong


def test_fitur_dari_input_urutannya_sesuai_daftar_fitur():
    x = fitur_dari_input("Dago", "2026-06-10 15:00", 35.0, 24.0, 75.0, 1.5, 90.0, 0.0)

    assert list(x.columns) == FITUR
    assert len(x) == 1
    assert x.loc[0, "pm25_ugm3"] == 35.0
    assert x.loc[0, "st_Dago"] == 1
    assert x.loc[0, "st_Antapani"] == 0
    assert x.loc[0, "jam_sin"] == pytest.approx(np.sin(2 * np.pi * 15 / 24))


@pytest.mark.parametrize(
    "nilai, kategori",
    [(0, "baik"), (15.5, "baik"), (15.6, "sedang"), (55, "sedang"), (55.1, "tidak sehat")],
)
def test_batas_kategori_ispu(nilai, kategori):
    assert kategori_pm25(nilai) == kategori
