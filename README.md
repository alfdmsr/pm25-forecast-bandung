# Prakiraan PM2.5 Bandung · Tim Alif-Tyas

**Kasus:** 06 Prakiraan PM2.5 Bandung · **Aplikasi:** (https://pm25-bandung.streamlit.app/) · **Video:** [tautan video]

| Anggota | NIM | Bagian yang dikerjakan |
|---|---|---|
| Muhammad Alif Dhiyaumasrur | 2400723 | Setup project, API, aplikasi Streamlit, pengujian, deploy, Laporan |
| Tyas Panggih Adi Putro | 2406264 | EDA, pembersihan data, Fitur, pelatihan model, evaluasi, dan threshold |

## Masalah dan pengguna

Tim kesehatan lingkungan dinas kota ingin memberi peringatan kepada warga sebelum udara memburuk. Model ini
memprakirakan PM2.5 tiga jam ke depan di lima stasiun (Dago, Soekarno-Hatta, Cibeureum, Antapani, Ujungberung)
dari kondisi udara dan cuaca saat ini. Pengguna langsung aplikasi adalah petugas dinas, yang memasukkan kondisi
terkini satu stasiun lalu membaca prakiraan tiga jam ke depan; penerima manfaat akhirnya adalah warga, khususnya
penderita asma, anak, dan lansia. Kesalahan yang tidak setara menjadi dasar pemilihan metrik: peringatan yang
terlewat lebih merugikan daripada alarm palsu, sehingga selain MAE dipantau juga recall pada jam tidak sehat.

## Data dan pembersihan

Data: 87.650 baris per jam dari Juli 2024 sampai Juni 2026, lima stasiun. Setelah dibersihkan tersisa 87.252 baris.

| Masalah yang ditemukan | Jumlah baris | Cara menangani |
|---|---|---|
| Nama stasiun ditulis dengan 16 variasi (spasi, huruf besar, "SOETTA") | 2.635 | disatukan ke 5 nama baku |
| Baris duplikat persis | 398 | dihapus dengan `drop_duplicates` |
| Waktu Soekarno-Hatta Juli-September 2025 tercatat dalam UTC, bukan WIB | 2.196 | digeser +7 jam |
| PM2.5 berisi kode -999 (sensor gagal baca) | 172 | diubah ke NaN |
| PM2.5 tepat 0 di antara nilai normal | 87 | diubah ke NaN |
| Kecepatan angin kosong | 875 | dibiarkan, diisi nilai terakhir (maksimal 2 jam) saat membuat fitur |
| Jam yang hilang (64-77 per stasiun) | 348 | tidak diinterpolasi, target dicocokkan dengan waktu tepat |

Periode UTC ditemukan dari jam puncak suhu harian: di semua stasiun suhu tertinggi sekitar pukul 14-15, kecuali
Soekarno-Hatta Juli-September 2025 yang puncaknya pukul 07-08, tepat 7 jam lebih awal.

## Hasil

Data dibagi berdasarkan waktu target: train sampai Februari 2026, validation Maret-April 2026, test Mei-Juni 2026.

| Model | MAE *validation* (µg/m³) | MAE *test* (µg/m³) |
|---|---|---|
| *Baseline*: persistence (tiga jam lagi sama dengan sekarang) | 6,24 | 6,51 |
| Ridge, fitur kondisi saat ini | 4,98 | |
| HistGradientBoosting, fitur kondisi saat ini (final) | 4,67 | 4,60 |

Model final 29% lebih baik daripada baseline di data test dan lebih baik di kelima stasiun. Peringatan jam tidak
sehat (PM2.5 di atas 55 µg/m³) di data test: model menangkap 94% (224 dari 239 jam), persistence 30%.

*Threshold* yang dipakai: 39 µg/m³, karena bagi warga dengan asma peringatan yang terlewat lebih merugikan daripada
alarm palsu. Angka ini adalah ambang terbesar yang masih menangkap minimal 70% jam tidak sehat di data validation.

## Cara menjalankan

Butuh Python 3.11–3.13 (disarankan 3.12). Jalankan semua perintah dari folder utama repo.

```bash
pip install -r requirements.txt
uvicorn app.api.main:app --reload       # API, dokumentasi di http://127.0.0.1:8000/docs
streamlit run app/ui/streamlit_app.py   # aplikasi, terbuka di http://localhost:8501
```

Di Windows, jika perintah `streamlit` atau `uvicorn` tidak dikenali, pakai `python -m streamlit run ...` dan
`python -m uvicorn ...`.

Aplikasi dan API mengunduh `artifacts/model.joblib` dan `artifacts/metadata.json` dari repo ini saat dijalankan,
jadi butuh koneksi internet dan repo yang publik.
Secara bawaan aplikasi Streamlit menghitung prakiraan sendiri. Agar aplikasi meminta prakiraan ke API, jalankan API
lalu isi variabel lingkungan `PM25_API_URL`:

```bash
set PM25_API_URL=http://127.0.0.1:8000        # Windows (Command Prompt)
export PM25_API_URL=http://127.0.0.1:8000     # macOS / Linux
streamlit run app/ui/streamlit_app.py
```

Menjalankan tes:

```bash
python -m pytest -q   # 47 lulus, 4 dilewati (tes Docker opsional)
```

Versi container (satu image, dua peran):

```bash
docker build -t pm25-bandung .
docker run -p 7860:7860 -e LAYANAN=ui pm25-bandung    # aplikasi Streamlit
docker run -p 7860:7860 -e LAYANAN=api pm25-bandung   # API saja, dokumentasi di /docs
```

Contoh permintaan ke API:

```bash
curl -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" -d "{\"stasiun\": \"Soekarno-Hatta\", \"waktu\": \"2026-06-10T15:00:00\", \"pm25\": 42, \"suhu\": 27, \"kelembaban\": 70, \"kecepatan_angin\": 1.0, \"arah_angin\": 90, \"curah_hujan\": 0}"
```

Balasan:

```json
{"prakiraan_pm25": 45.7, "kategori": "sedang", "peringatan": true,
 "saran": "Udara berpotensi tidak sehat. Penderita asma sebaiknya menyiapkan masker.", "catatan": null}
```

### Melatih ulang model

Notebook membaca data dan `src/features.py` langsung dari repo ini di GitHub, jadi bisa dijalankan di Colab
tanpa menyalin file.

1. Jalankan `notebooks/Hasil_EDA_PM25_Bandung.ipynb`. Notebook membaca `data/raw.csv` dan menghasilkan
   `data/clean.csv`. Upload file ini ke repo.
2. Jalankan `notebooks/02_modeling.ipynb`. Notebook membaca `data/clean.csv` dan `src/features.py`, lalu
   menyimpan `artifacts/model.joblib` dan `artifacts/metadata.json`. Upload folder `artifacts/` ke repo.

Model disimpan dengan scikit-learn 1.9.1, sedangkan `requirements.txt` memakai 1.7.2. Perbedaan ini hanya
memunculkan peringatan `InconsistentVersionWarning` saat model dimuat dan tidak memengaruhi hasil (MAE test
4,602 vs 4,599). Jika model dilatih ulang dengan versi lain, samakan versi di `requirements.txt`.

## Struktur repositori

```
notebooks/
  Hasil_EDA_PM25_Bandung.ipynb   EDA, pembersihan data, target, pembagian data, baseline
  02_modeling.ipynb              fitur, perbandingan model, threshold, evaluasi test, penyimpanan model
data/
  raw.csv                        data mentah dari klien
  clean.csv                      data bersih hasil notebook EDA
src/
  features.py                    fungsi pembuat fitur, dipakai saat pelatihan dan saat prediksi
  predict.py                     memuat model, mengecek masukan, dan membuat prakiraan (dipakai API dan aplikasi)
artifacts/
  model.joblib                   model final
  metadata.json                  versi model, fitur masukan, threshold, dan metrik
app/
  api/main.py                    API (FastAPI): /, /metadata, /health, /predict
  ui/streamlit_app.py            antarmuka (Streamlit)
tests/                           tes fitur, predict, API, /health, artefak, dan Docker
Dockerfile                       dua mode: LAYANAN=ui atau LAYANAN=api
start.sh                         menjalankan API/UI di dalam container
.streamlit/config.toml           warna tema aplikasi
requirements.txt
```

## Keterbatasan

- Puncak PM2.5 yang tinggi cenderung diprakirakan terlalu rendah. Rata-rata selisih di jam dengan PM2.5 di atas 55
  sekitar 17 µg/m³, jauh di atas rata-rata keseluruhan 4,6 µg/m³. Kategori dan peringatannya biasanya tetap benar.
- Lonjakan mendadak (misalnya dari 23 ke 67 µg/m³ dalam tiga jam) tidak bisa ditebak dari kondisi saat ini.
- Ambang peringatan dipilih di periode validation (musim hujan, sedikit jam tidak sehat). Di musim kemarau ambang ini
  menghasilkan banyak peringatan: 1.095 dalam dua bulan data test, dengan sekitar 20% yang benar.
- Data hanya dua tahun dan bersifat sintetis. Model belum pernah melihat kejadian khusus seperti kebakaran atau
  perubahan lalu lintas besar.
- Fitur riwayat PM2.5 dan PM2.5 stasiun lain sudah dicoba, tetapi hanya memperbaiki MAE validation sekitar 1%,
  sehingga tidak dipakai agar masukan aplikasi tetap sederhana.
- Aplikasi bukan pemantauan waktu nyata: kondisi terkini diisi manual petugas, dan cuaca hari ini belum tersedia
  dari sumber otomatis.

Jika dipakai sungguhan, MAE mingguan dan ketepatan peringatan perlu dipantau, dan model dilatih ulang secara berkala.
