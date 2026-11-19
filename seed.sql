-- Data contoh SIMPUS (Versi Revisi). Jalankan setelah schema.sql.
-- Password contoh: admin = admin123, siswa = siswa123

INSERT INTO info_operasional (id_info, jam_operasional, pengumuman) VALUES
(1, 'Senin - Kamis: 07.00 - 15.00 | Jumat: 07.00 - 11.30', 'Hari Jumat tutup lebih awal pukul 11.30 WIB untuk persiapan Sholat Jumat.');

INSERT INTO pengguna (role, identitas, nama, kelas, asal_instansi, password_hash) VALUES
('ADMIN', '198501012010011001', 'Dra. Dora Indriana, S.Pd., M.Pd', NULL, NULL, crypt('admin123', gen_salt('bf'))),
('ADMIN', '199602152015031002', 'Radhitya Dwi Nanda, S.Pd',   NULL, NULL, crypt('admin123', gen_salt('bf'))),
('SISWA', '0081234501', 'Aditya Pratama',       'XI IPA 1',  NULL, crypt('siswa123', gen_salt('bf'))),
('SISWA', '0081234502', 'Bunga Citra Lestari',  'XI IPS 1',  NULL, crypt('siswa123', gen_salt('bf'))),
('SISWA', '0081234503', 'Dimas Saputra',        'X-2',       NULL, crypt('siswa123', gen_salt('bf'))),
('SISWA', '0081234504', 'Eka Putri Wulandari',  'XII IPA 2', NULL, crypt('siswa123', gen_salt('bf'))),
('SISWA', '0081234505', 'Fajar Nugroho',        'XII IPS 2', NULL, crypt('siswa123', gen_salt('bf'))),
('TAMU',  NULL,         'Budi Santoso',         NULL, 'Dinas Pendidikan Kab. Jember', NULL),
('TAMU',  NULL,         'Maya Anggraini',       NULL, 'SMA Negeri 2 Jember',          NULL);

INSERT INTO rak (nama_rak, keterangan_lokasi) VALUES
('IPA',       'Lantai 1 - Rak A (dekat pintu masuk)'),
('IPS',       'Lantai 1 - Rak B'),
('Fiksi',     'Lantai 1 - Rak C (area baca santai)'),
('Non-Fiksi', 'Lantai 2 - Rak D'),
('Referensi', 'Lantai 2 - Rak E (hanya baca di tempat)'),
('Teknologi', 'Lantai 2 - Rak F'),
('Modul/LKS', 'Lantai 1 - Rak G (koleksi sekolah)');

INSERT INTO buku (judul, pengarang, penerbit, tahun_terbit, id_rak, stok_total) VALUES
('Fisika Dasar untuk SMA',   'Marthen Kanginan',      'Erlangga',        2016, 1, 5),
('Biologi Kelas XI',         'Irnaningtyas',          'Erlangga',        2017, 1, 4),
('Kimia Kelas X',            'Unggul Sudarmo',        'Erlangga',        2016, 1, 5),
('Sejarah Indonesia',        'Kemendikbud',           'Kemendikbud',     2018, 2, 6),
('Laskar Pelangi',           'Andrea Hirata',         'Bentang Pustaka', 2005, 3, 4),
('Atomic Habits',            'James Clear',           'Gramedia',        2019, 4, 3),
('Dasar Pemrograman Python', 'Budi Raharjo',          'Informatika',     2020, 6, 3),
('Modul Praktikum Jaringan', 'Tim MGMP RPL',          NULL,              NULL, 7, 10),
('LKS Matematika Wajib XII', 'Tim Penyusun Sekolah',  NULL,              NULL, 7, 15);

INSERT INTO kunjungan (id_pengguna, waktu_checkin, waktu_checkout, durasi_menit) VALUES
(3, '2026-11-16 07:15:00', '2026-11-16 08:00:00', 45),
(4, '2026-11-16 09:00:00', '2026-11-16 09:50:00', 50),
(8, '2026-11-16 10:10:00', '2026-11-16 10:55:00', 45);

INSERT INTO peminjaman (id_pengguna, id_buku, tanggal_pinjam, tanggal_kembali, tanggal_dikembalikan, status, denda, keterangan_denda) VALUES
(3, 5, '2026-11-01 08:00:00', '2026-11-08 08:00:00', '2026-11-07 10:00:00', 'Dikembalikan', 0, NULL),
(4, 1, '2026-11-12 09:30:00', '2026-11-19 09:30:00', NULL,                  'Dipinjam',     0, NULL),
(5, 6, '2026-11-05 10:00:00', '2026-11-12 10:00:00', NULL,                  'Dipinjam',     0, NULL);