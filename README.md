# SIMPUS - Sistem Manajemen Perpustakaan Sekolah (CLI - Revisi)

Sistem Informasi Perpustakaan berbasis Command Line Interface (Python 3 + PostgreSQL >= 13) yang telah dirampingkan dan dilengkapi integrasi modul `os` untuk manajemen tampilan terminal dan file konfigurasi.

## Fitur Utama
1. **Perampingan Struktur & Database**:
   - Penyatuan entitas pengguna ke tabel induk `pengguna` (`ADMIN`, `SISWA`, `TAMU`) dan pencatatan presensi ke tabel `kunjungan`.
   - Perhitungan stok dinamis (`stok_total` dikurangi buku yang berstatus `'Dipinjam'`).
   - Kolom `penerbit` dan `tahun_terbit` bersifat opsional (`NULL`) untuk kebutuhan pendataan modul/LKS sekolah.
2. **Hak Akses & Alur Role**:
   - **Admin**: Rekap Laporan & Peminjaman (menu paling atas), Kelola Katalog Buku, Pembaruan Jam Operasional, Konfirmasi Pengembalian & Validasi/Pembebasan Denda, dan Logout (menu paling bawah).
   - **Siswa**: Login menggunakan NISN, Check-In & Check-Out kunjungan (kuota maksimal 60 menit / 1 jam), Pengajuan Peminjaman (otomatis +7 hari, denda awal 0), Pengembalian Buku, dan Cek Status Denda.
   - **Tamu (Guest Mode)**: Masuk tanpa akun/password cukup dengan input **Nama** dan **Asal Instansi**, hanya memiliki akses Check-In, Check-Out, dan Lihat Katalog (menu peminjaman diblokir).

## Instalasi & Menjalankan Program
```bash
createdb -U postgres simpus
psql -U postgres -d simpus -f schema.sql
psql -U postgres -d simpus -f seed.sql
pip install -r requirements.txt
python simpus.py
```

## Akun Contoh
- **Admin**: NIP `198501012010011001` | Password `admin123`
- **Siswa**: NISN `0081234501` s.d. `0081234505` | Password `siswa123`
- **Tamu**: Tanpa password (input Nama & Asal Instansi)
