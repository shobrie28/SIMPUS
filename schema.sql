-- =====================================================================
-- SIMPUS - Sistem Manajemen Perpustakaan Sekolah (Versi Revisi + Rak)
-- Skema PostgreSQL (>= 13). Jalankan: psql -U postgres -d simpus -f schema.sql
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS peminjaman, kunjungan, buku, rak, info_operasional, pengguna CASCADE;
DROP TYPE IF EXISTS role_pengguna, status_peminjaman CASCADE;

CREATE TYPE role_pengguna AS ENUM ('ADMIN', 'SISWA', 'TAMU');
CREATE TYPE status_peminjaman AS ENUM ('Dipinjam', 'Dikembalikan', 'Rusak');

-- Tabel Induk Pengguna (Menyatukan Admin, Siswa, dan Tamu)
CREATE TABLE pengguna (
    id_pengguna   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role          role_pengguna NOT NULL,
    identitas     VARCHAR(30)   UNIQUE,           -- NIP untuk Admin, NISN untuk Siswa, NULL untuk Tamu
    nama          VARCHAR(100)  NOT NULL,
    kelas         VARCHAR(20),                    -- Khusus Siswa
    asal_instansi VARCHAR(100),                   -- Khusus Tamu
    password_hash TEXT,                           -- NULL untuk Tamu (Guest Mode)
    CONSTRAINT chk_pengguna_role CHECK (
        (role = 'ADMIN' AND identitas ~ '^[0-9]{18}$' AND password_hash IS NOT NULL) OR
        (role = 'SISWA' AND identitas ~ '^[0-9]{10}$' AND kelas IS NOT NULL AND password_hash IS NOT NULL) OR
        (role = 'TAMU'  AND asal_instansi IS NOT NULL)
    )
);

-- Tabel Informasi Jam Operasional Perpustakaan
CREATE TABLE info_operasional (
    id_info          INT PRIMARY KEY DEFAULT 1,
    jam_operasional  VARCHAR(100) NOT NULL DEFAULT 'Senin - Kamis: 07.00 - 15.00 | Jumat: 07.00 - 11.30',
    pengumuman       TEXT         NOT NULL DEFAULT 'Perpustakaan buka sesuai jadwal reguler.',
    updated_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_single_info CHECK (id_info = 1)
);

-- Tabel Lokasi Rak Buku
CREATE TABLE rak (
    id_rak            INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nama_rak          VARCHAR(50)  UNIQUE NOT NULL,
    keterangan_lokasi VARCHAR(150) NOT NULL
);

-- Tabel Buku (Terhubung ke Tabel Rak)
CREATE TABLE buku (
    id_buku      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    judul        VARCHAR(200) NOT NULL,
    pengarang    VARCHAR(100) NOT NULL,
    penerbit     VARCHAR(100),
    tahun_terbit SMALLINT,
    id_rak       INT          NOT NULL,
    stok_total   INT          NOT NULL DEFAULT 0,
    CONSTRAINT chk_buku_stok  CHECK (stok_total >= 0),
    CONSTRAINT chk_buku_tahun CHECK (tahun_terbit IS NULL OR tahun_terbit BETWEEN 1000 AND 2100),
    CONSTRAINT fk_buku_rak    FOREIGN KEY (id_rak) REFERENCES rak (id_rak)
        ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE INDEX idx_buku_judul ON buku (LOWER(judul));

-- Tabel Kunjungan Terpadu (Siswa & Tamu) dengan Check-In, Check-Out & TIMESTAMP
CREATE TABLE kunjungan (
    id_kunjungan   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_pengguna    INT       NOT NULL,
    waktu_checkin  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    waktu_checkout TIMESTAMP,
    durasi_menit   INT,
    CONSTRAINT chk_waktu_kunjungan CHECK (waktu_checkout IS NULL OR waktu_checkout >= waktu_checkin),
    CONSTRAINT fk_kunjungan_pengguna FOREIGN KEY (id_pengguna) REFERENCES pengguna (id_pengguna)
        ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE INDEX idx_kunjungan_waktu ON kunjungan (waktu_checkin);

-- Tabel Peminjaman (Tanggal_Kembali wajib diisi, Denda default 0, Status ENUM)
CREATE TABLE peminjaman (
    id_pinjam            INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_pengguna          INT               NOT NULL,
    id_buku              INT               NOT NULL,
    tanggal_pinjam       TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tanggal_kembali      TIMESTAMP         NOT NULL,
    tanggal_dikembalikan TIMESTAMP,
    status               status_peminjaman NOT NULL DEFAULT 'Dipinjam',
    denda                INT               NOT NULL DEFAULT 0,
    keterangan_denda     TEXT,
    CONSTRAINT chk_pinjam_tanggal CHECK (tanggal_kembali >= tanggal_pinjam),
    CONSTRAINT chk_pinjam_denda   CHECK (denda >= 0),
    CONSTRAINT fk_pinjam_pengguna FOREIGN KEY (id_pengguna) REFERENCES pengguna (id_pengguna)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_pinjam_buku FOREIGN KEY (id_buku) REFERENCES buku (id_buku)
        ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE INDEX idx_pinjam_status ON peminjaman (status);