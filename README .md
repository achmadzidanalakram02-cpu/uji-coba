# MAMMOUTH 6.0 "Aurora Clinical"

**M**y **A**ssistant In **M**outh **H**ealth — asisten skrining kesehatan mulut berbasis AI (Streamlit).

## Menjalankan

```bash
pip install -r requirements.txt
streamlit run mammouth_app.py
```

Aplikasi akan membuat `mammouth.db` (SQLite) secara otomatis di folder yang sama saat pertama kali dijalankan.

## Model AI (opsional)

Untuk mengaktifkan deteksi otomatis, letakkan bobot YOLO pada folder yang sama dengan `mammouth_app.py`:

| Arsitektur | Nama berkas |
|---|---|
| YOLOv8  | `best.pt` |
| YOLOv11 | `yolov11_best.pt` |
| YOLOv12 | `yolov12_best.pt` |

Tanpa berkas model, aplikasi tetap berjalan penuh dalam **Mode Manual** — klinisi memilih temuan lesi secara langsung, dan seluruh fitur lain (anamnesis, pasien, EMR, analitik, ekspor) tetap aktif.

## Akun pertama

Akun pertama yang mendaftar melalui tab **"Buat Akun"** otomatis menjadi **Administrator**, dengan akses tambahan ke panel admin (ringkasan seluruh klinisi) di menu *Pengaturan Sistem* dan *Analitik Data*.

## Yang baru di versi 6.0

- Manajemen pasien (bukan cuma isolasi per-klinisi) dengan riwayat per pasien
- Hash password ber-*salt* (PBKDF2), bukan SHA-256 polos
- Live preview citra dengan penyesuaian brightness/contrast/sharpness
- Alur hibrida AI + konfirmasi manual sebelum data tersimpan ke EMR
- Anotasi bounding box otomatis pada citra saat deteksi AI aktif
- Riwayat EMR: pencarian, filter tanggal/status, ubah status, catatan, hapus
- Ekspor CSV, Excel, dan laporan PDF per pemeriksaan (jika `fpdf2` terpasang)
- Dashboard analitik: tren harian, frekuensi lesi, distribusi status, mode admin
- Ensiklopedia lesi dengan pencarian & filter kategori
- Pengaturan: profil, ubah password, preferensi threshold default, backup database, hapus data
- Desain ulang penuh ("Aurora Clinical": navy + koral) dengan halaman login dua-panel
