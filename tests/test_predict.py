#Tes src/predict.py: validasi masukan dan logika keluaran prakiraan.

import pytest

from src.features import FITUR
from src.predict import SARAN, cek_masukan, prakirakan


def test_masukan_valid_tidak_menghasilkan_galat(masukan):
    assert cek_masukan(masukan) == []


def test_stasiun_tidak_dikenal_ditolak(masukan):
    masukan["stasiun"] = "Cimahi"
    assert any("Stasiun harus" in g for g in cek_masukan(masukan))


def test_waktu_kosong_ditolak(masukan):
    masukan["waktu"] = None
    assert any("Waktu wajib" in g for g in cek_masukan(masukan))


def test_kolom_hilang_dilaporkan(masukan):
    masukan.pop("curah_hujan")
    assert any("Curah hujan wajib" in g for g in cek_masukan(masukan))


def test_pm25_nol_dianggap_sensor_gagal(masukan):
    masukan["pm25"] = 0
    assert any("sensor gagal" in g for g in cek_masukan(masukan))


@pytest.mark.parametrize(
    "kolom, nilai",
    [("pm25", -1), ("pm25", 900), ("suhu", 50), ("kelembaban", 101),
     ("kecepatan_angin", 99), ("arah_angin", 361), ("curah_hujan", 999)],
)
def test_nilai_di_luar_rentang_wajar(masukan, kolom, nilai):
    masukan[kolom] = nilai
    assert any("di luar rentang wajar" in g for g in cek_masukan(masukan))


def test_prakiraan_tidak_sehat(meta, buat_model, masukan):
    hasil = prakirakan(buat_model(60.0), meta, masukan)

    assert hasil["prakiraan_pm25"] == 60.0
    assert hasil["kategori"] == "tidak sehat"
    assert hasil["peringatan"] is True
    assert hasil["saran"] == SARAN["tidak sehat"]
    assert hasil["catatan"] is None


def test_sedang_tapi_di_atas_ambang_peringatan_dapat_saran_waspada(meta, buat_model, masukan):
    hasil = prakirakan(buat_model(45.0), meta, masukan)

    assert hasil["kategori"] == "sedang"        # 45 masih <= 55
    assert hasil["peringatan"] is True          # tetapi > 39
    assert hasil["saran"] == SARAN["waspada"]

def test_saran_khusus_bila_udara_saat_ini_sudah_tidak_sehat(meta, buat_model, masukan):
    masukan["pm25"] = 60.0                        # kondisi sekarang sudah > 55
    hasil = prakirakan(buat_model(12.0), meta, masukan)

    assert hasil["kategori"] == "baik"            # prakiraan 12 -> baik
    assert hasil["peringatan"] is True            # tetapi udara sekarang tidak sehat
    assert "sudah tidak sehat" in hasil["saran"].lower()

def test_prediksi_negatif_dipotong_menjadi_nol(meta, buat_model, masukan):
    hasil = prakirakan(buat_model(-8.0), meta, masukan)

    assert hasil["prakiraan_pm25"] == 0.0
    assert hasil["kategori"] == "baik"
    assert hasil["peringatan"] is False
    assert hasil["saran"] == SARAN["baik"]


def test_hasil_dibulatkan_satu_desimal(meta, buat_model, masukan):
    assert prakirakan(buat_model(42.66), meta, masukan)["prakiraan_pm25"] == 42.7


def test_ada_catatan_bila_pm25_di_atas_rentang_latih(meta, buat_model, masukan):
    masukan["pm25"] = 200.0                      # masih <= 500, jadi lolos validasi
    hasil = prakirakan(buat_model(50.0), meta, masukan)

    assert hasil["catatan"] is not None
    assert "lebih tinggi" in hasil["catatan"]


def test_catatan_ketika_suhu_di_luar_rentang_latih(meta, buat_model, masukan):
    masukan["suhu"] = 38.0                       # lolos BATAS (<= 40), di luar RENTANG_LATIH (<= 31.9)
    hasil = prakirakan(buat_model(30.0), meta, masukan)

    assert hasil["catatan"] is not None
    assert "suhu" in hasil["catatan"].lower()


def test_kolom_dikirim_ke_model_sesuai_metadata(meta, buat_model, masukan):
    model = buat_model(30.0)

    prakirakan(model, meta, masukan)

    assert list(model.diterima.columns) == meta["fitur_masukan"] == FITUR


def test_masukan_tidak_valid_menolak_prediksi(meta, buat_model, masukan):
    masukan["stasiun"] = "Cimahi"
    with pytest.raises(ValueError):
        prakirakan(buat_model(30.0), meta, masukan)
