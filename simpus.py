#!/usr/bin/env python3
"""SIMPUS - Sistem Manajemen Perpustakaan Sekolah (CLI, Python + PostgreSQL)."""
import configparser
import getpass
import os
import shutil
import sys
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BATAS_PINJAM_HARI = 7
KUOTA_KUNJUNGAN_MENIT = 60
DENDA_PER_HARI = 1000
MAX_PERCOBAAN_LOGIN = 3
STATUS_OPSI = {
    "1": "Dipinjam",
    "2": "Dikembalikan",
    "3": "Rusak",
}

HEADER_ASCII = r"""
═══════════════════════════════════════════════════════════════════════════════

  ██████  ██████  ██   ██  █████   ██  ██  ██████       _______   _______      
  ██        ██    ███ ███  ██  ██  ██  ██  ██          /      /\ /\      \     
  ██████    ██    ██ █ ██  █████   ██  ██  ██████     / ──── /  V  \ ──── \    
      ██    ██    ██   ██  ██      ██  ██      ██    / ──── /   │   \ ──── \   
  ██████  ██████  ██   ██  ██       ████   ██████   /______/    │    \______\  
  ───────────────────────────────────────────────   \______\    │    /______/  
           Sistem Informasi Perpustakaan             \______\___│___/______/   
  ───────────────────────────────────────────────     └─────────┴─────────┘    

═══════════════════════════════════════════════════════════════════════════════
"""


# ------------------------------------------------------------------ util & os
def bersihkan_layar():
    """Membersihkan layar terminal menggunakan library os lintas platform."""
    os.system("cls" if os.name == "nt" else "clear")


def jeda():
    """Menahan tampilan layar sebelum kembali ke menu."""
    input("\nTekan [Enter] untuk melanjutkan...")


def koneksi():
    """Membaca config.ini menggunakan os.path & os.environ jika tersedia."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.ini")
    example_path = os.path.join(base_dir, "config.ini.example")

    if not os.path.exists(config_path):
        if os.path.exists(example_path):
            shutil.copyfile(example_path, config_path)
            print("File config.ini dibuat otomatis dari config.ini.example.")
        else:
            sys.exit("File config.ini tidak ditemukan.")

    cfg = configparser.ConfigParser()
    cfg.read(config_path, encoding="utf-8")
    c = cfg["postgresql"]

    return psycopg2.connect(
        host=os.getenv("SIMPUS_DB_HOST", c["host"]),
        port=os.getenv("SIMPUS_DB_PORT", c["port"]),
        dbname=os.getenv("SIMPUS_DB_NAME", c["dbname"]),
        user=os.getenv("SIMPUS_DB_USER", c["user"]),
        password=os.getenv("SIMPUS_DB_PASS", c["password"]),
    )


def lebar_terminal():
    return min(max(shutil.get_terminal_size((100, 24)).columns, 84), 125)


def garis(karakter="="):
    print(karakter * lebar_terminal())


def tampilkan_header():
    """Menampilkan header ASCII SIMPUS di bagian atas setiap halaman."""
    w = lebar_terminal()
    for baris in HEADER_ASCII.strip("\n").splitlines():
        print(baris.center(w) if baris else "")


def judul(teks, info_user=None):
    bersihkan_layar()
    w = lebar_terminal()
    tampilkan_header()
    print(teks.center(w))
    if info_user:
        print(info_user.center(w))
    garis("=")


def tabel(rows, kolom):
    """Mencetak list of dict sebagai tabel CLI yang rapi."""
    if not rows:
        print("  (tidak ada data)")
        return
    lebar = []
    for k, h in kolom:
        lebar.append(max(len(h), *(len(str(r[k] if r[k] is not None else "-")) for r in rows)))
    print(" | ".join(h.ljust(w) for (k, h), w in zip(kolom, lebar)))
    print("-+-".join("-" * w for w in lebar))
    for r in rows:
        print(" | ".join(str(r[k] if r[k] is not None else "-").ljust(w) for (k, h), w in zip(kolom, lebar)))
    print(f"Total: {len(rows)} data")


def input_int(prompt, minimal=None, wajib=True):
    while True:
        s = input(prompt).strip()
        if not s and not wajib:
            return None
        try:
            v = int(s)
        except ValueError:
            print("Masukkan angka yang valid.")
            continue
        if minimal is not None and v < minimal:
            print(f"Nilai minimal adalah {minimal}.")
            continue
        return v


def jalankan(conn, sql, params=None, fetch=True):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or ())
        return cur.fetchall() if fetch else cur.rowcount


def tampilkan_info_operasional(conn):
    rows = jalankan(conn, "SELECT jam_operasional, pengumuman, updated_at FROM info_operasional WHERE id_info = 1")
    if rows:
        r = rows[0]
        print(f"Jam Operasional : {r['jam_operasional']}")
        print(f"Info Terkini    : {r['pengumuman']}")
        garis("-")


# --------------------------------------------------------------- katalog & rak
def tampilkan_daftar_rak(conn):
    rows = jalankan(conn, "SELECT id_rak, nama_rak, keterangan_lokasi FROM rak ORDER BY id_rak ASC")
    print("\nDaftar Lokasi Rak:")
    tabel(rows, [
        ("id_rak", "ID Rak"),
        ("nama_rak", "Kategori / Rak"),
        ("keterangan_lokasi", "Lokasi"),
    ])
    return rows


def lihat_katalog(conn, info_user=None):
    judul("KATALOG BUKU & LOKASI RAK PERPUSTAKAAN", info_user)
    kata = input("Cari judul/pengarang/rak/lokasi (kosong = semua): ").strip()
    rows = jalankan(conn, """
        SELECT b.id_buku,
               b.judul,
               b.pengarang,
               COALESCE(b.penerbit, '-') AS penerbit,
               COALESCE(b.tahun_terbit::text, '-') AS tahun,
               r.nama_rak AS kategori,
               r.keterangan_lokasi AS lokasi_rak,
               b.stok_total,
               (b.stok_total - COUNT(p.id_pinjam)) AS stok_tersedia
        FROM buku b
        JOIN rak r ON r.id_rak = b.id_rak
        LEFT JOIN peminjaman p
               ON p.id_buku = b.id_buku AND p.status = 'Dipinjam'
        WHERE b.judul ILIKE %s
           OR b.pengarang ILIKE %s
           OR r.nama_rak ILIKE %s
           OR r.keterangan_lokasi ILIKE %s
        GROUP BY b.id_buku, r.nama_rak, r.keterangan_lokasi
        ORDER BY b.id_buku ASC
    """, (f"%{kata}%", f"%{kata}%", f"%{kata}%", f"%{kata}%"))
    print()
    tabel(rows, [
        ("id_buku", "ID"),
        ("judul", "Judul Buku"),
        ("pengarang", "Pengarang"),
        ("tahun", "Tahun"),
        ("kategori", "Rak"),
        ("lokasi_rak", "Lokasi Rak"),
        ("stok_total", "Total"),
        ("stok_tersedia", "Tersedia"),
    ])


# --------------------------------------------------------------- kunjungan terpadu
def proses_checkin(conn, id_pengguna, nama):
    aktif = jalankan(conn, """
        SELECT id_kunjungan, waktu_checkin
        FROM kunjungan
        WHERE id_pengguna = %s AND waktu_checkout IS NULL
        ORDER BY waktu_checkin DESC LIMIT 1
    """, (id_pengguna,))
    if aktif:
        ck = aktif[0]["waktu_checkin"].strftime("%Y-%m-%d %H:%M:%S")
        print(f"Anda sudah Check-In sejak {ck} (belum Check-Out).")
        return aktif[0]["id_kunjungan"]

    sekarang = datetime.now().replace(microsecond=0)
    with conn:
        rows = jalankan(conn, """
            INSERT INTO kunjungan (id_pengguna, waktu_checkin)
            VALUES (%s, %s)
            RETURNING id_kunjungan, waktu_checkin
        """, (id_pengguna, sekarang))
    idk = rows[0]["id_kunjungan"]
    print(f"Check-In berhasil untuk {nama} pada {sekarang.strftime('%Y-%m-%d %H:%M:%S')}.")
    print(f"Catatan: Kuota maksimal kunjungan adalah {KUOTA_KUNJUNGAN_MENIT} menit (1 jam).")
    return idk


def proses_checkout(conn, id_pengguna, nama):
    aktif = jalankan(conn, """
        SELECT id_kunjungan, waktu_checkin
        FROM kunjungan
        WHERE id_pengguna = %s AND waktu_checkout IS NULL
        ORDER BY waktu_checkin DESC LIMIT 1
    """, (id_pengguna,))
    if not aktif:
        print("Tidak ada sesi kunjungan aktif yang perlu di-Check-Out.")
        return False

    idk = aktif[0]["id_kunjungan"]
    checkin_dt = aktif[0]["waktu_checkin"]
    checkout_dt = datetime.now().replace(microsecond=0)
    durasi = max(1, int((checkout_dt - checkin_dt).total_seconds() // 60))

    with conn:
        jalankan(conn, """
            UPDATE kunjungan
            SET waktu_checkout = %s, durasi_menit = %s
            WHERE id_kunjungan = %s
        """, (checkout_dt, durasi, idk), fetch=False)

    print(f"Check-Out berhasil untuk {nama} pada {checkout_dt.strftime('%Y-%m-%d %H:%M:%S')}.")
    print(f"Durasi kunjungan: {durasi} menit.")
    if durasi > KUOTA_KUNJUNGAN_MENIT:
        lebih = durasi - KUOTA_KUNJUNGAN_MENIT
        print(f"[PERINGATAN KUOTA] Durasi kunjungan melebihi batas maksimal 1 jam (+{lebih} menit).")
    else:
        print("Durasi kunjungan sesuai batas kuota maksimal 1 jam.")
    return True


# --------------------------------------------------------------- role tamu
def menu_tamu(conn):
    judul("MODE TAMU (GUEST ACCESS)")
    tampilkan_info_operasional(conn)
    nama = input("Masukkan Nama Lengkap : ").strip()
    instansi = input("Masukkan Asal Instansi: ").strip()
    if not nama or not instansi:
        print("Nama dan Asal Instansi wajib diisi.")
        jeda()
        return

    try:
        with conn:
            existing = jalankan(conn, """
                SELECT id_pengguna FROM pengguna
                WHERE role = 'TAMU'
                  AND LOWER(nama) = LOWER(%s)
                  AND LOWER(asal_instansi) = LOWER(%s)
                LIMIT 1
            """, (nama, instansi))

            if existing:
                id_pengguna = existing[0]["id_pengguna"]
            else:
                rows = jalankan(conn, """
                    INSERT INTO pengguna (role, nama, asal_instansi)
                    VALUES ('TAMU', %s, %s)
                    RETURNING id_pengguna
                """, (nama, instansi))
                id_pengguna = rows[0]["id_pengguna"]
        proses_checkin(conn, id_pengguna, f"{nama} ({instansi})")
    except psycopg2.Error as e:
        conn.rollback()
        print("Gagal mencatat kunjungan tamu:", e.pgerror or str(e))
        jeda()
        return

    jeda()
    info_tamu = f"Tamu: {nama} | Instansi: {instansi}"
    while True:
        judul("MENU TAMU (AKSES TERBATAS)", info_tamu)
        tampilkan_info_operasional(conn)
        print("1. Lihat Katalog Buku & Lokasi Rak")
        print("2. Check-In Kunjungan")
        print("3. Check-Out Kunjungan & Keluar")
        print("0. Logout / Keluar")
        garis("-")
        p = input("Pilih menu: ").strip()
        if p == "1":
            lihat_katalog(conn, info_tamu)
            jeda()
        elif p == "2":
            proses_checkin(conn, id_pengguna, nama)
            jeda()
        elif p == "3":
            proses_checkout(conn, id_pengguna, nama)
            jeda()
            return
        elif p == "0":
            print("Terima kasih atas kunjungan Anda.")
            jeda()
            return
        else:
            print("Pilihan tidak valid.")
            jeda()


# --------------------------------------------------------------- role siswa
def login_siswa(conn):
    s = None
    for sisa in range(MAX_PERCOBAAN_LOGIN, 0, -1):
        judul("LOGIN SISWA")
        nisn = input("NISN     : ").strip()
        pw = getpass.getpass("Password : ")
        rows = jalankan(conn, """
            SELECT id_pengguna, identitas, nama, kelas
            FROM pengguna
            WHERE role = 'SISWA' AND identitas = %s AND password_hash = crypt(%s, password_hash)
        """, (nisn, pw))
        if rows:
            s = rows[0]
            break
        print(f"NISN atau password salah. Sisa percobaan: {sisa - 1}")
        jeda()

    if not s:
        return

    info_siswa = f"Siswa: {s['nama']} | NISN: {s['identitas']} | Kelas: {s['kelas']}"
    proses_checkin(conn, s["id_pengguna"], s["nama"])
    jeda()

    while True:
        judul("DASHBOARD SISWA", info_siswa)
        tampilkan_info_operasional(conn)
        print("1. Rekap Peminjaman & Status Denda Saya")
        print("2. Lihat Katalog Buku & Lokasi Rak")
        print("3. Ajukan Peminjaman Buku (Maks. 7 Hari)")
        print("4. Pengembalian Buku")
        print("5. Check-In Kunjungan")
        print("6. Check-Out Kunjungan")
        print("0. Logout")
        garis("-")
        p = input("Pilih menu: ").strip()
        if p == "1":
            riwayat_dan_denda_siswa(conn, s["id_pengguna"], info_siswa)
            jeda()
        elif p == "2":
            lihat_katalog(conn, info_siswa)
            jeda()
        elif p == "3":
            ajukan_pinjam_siswa(conn, s["id_pengguna"], info_siswa)
            jeda()
        elif p == "4":
            kembalikan_buku_siswa(conn, s["id_pengguna"], info_siswa)
            jeda()
        elif p == "5":
            proses_checkin(conn, s["id_pengguna"], s["nama"])
            jeda()
        elif p == "6":
            proses_checkout(conn, s["id_pengguna"], s["nama"])
            jeda()
        elif p == "0":
            print("Logout berhasil.")
            jeda()
            return
        else:
            print("Pilihan tidak valid.")
            jeda()


def hitung_estimasi_denda(tgl_kembali, tgl_acuan=None):
    acuan = tgl_acuan or datetime.now()
    if acuan.date() > tgl_kembali.date():
        hari_telat = (acuan.date() - tgl_kembali.date()).days
        return hari_telat * DENDA_PER_HARI
    return 0


def riwayat_dan_denda_siswa(conn, id_pengguna, info_siswa):
    judul("REKAP PEMINJAMAN & STATUS DENDA", info_siswa)
    rows = jalankan(conn, """
        SELECT p.id_pinjam,
               b.judul,
               to_char(p.tanggal_pinjam, 'YYYY-MM-DD HH24:MI') AS tgl_pinjam,
               to_char(p.tanggal_kembali, 'YYYY-MM-DD') AS batas_kembali,
               COALESCE(to_char(p.tanggal_dikembalikan, 'YYYY-MM-DD HH24:MI'), '-') AS tgl_kembali,
               p.status,
               p.denda,
               p.tanggal_kembali AS raw_batas
        FROM peminjaman p
        JOIN buku b ON b.id_buku = p.id_buku
        WHERE p.id_pengguna = %s
        ORDER BY p.id_pinjam DESC
    """, (id_pengguna,))

    total_denda = 0
    for r in rows:
        if r["status"] == "Dipinjam":
            est = hitung_estimasi_denda(r["raw_batas"])
            r["denda_tampil"] = f"Rp {est:,} (berjalan)" if est > 0 else "Rp 0"
            total_denda += est
        else:
            r["denda_tampil"] = f"Rp {r['denda']:,}"
            total_denda += r["denda"]

    tabel(rows, [
        ("id_pinjam", "ID"),
        ("judul", "Judul Buku"),
        ("tgl_pinjam", "Tgl Pinjam"),
        ("batas_kembali", "Batas Kembali"),
        ("tgl_kembali", "Dikembalikan"),
        ("status", "Status"),
        ("denda_tampil", "Denda"),
    ])
    print(f"Total Akumulasi Denda: Rp {total_denda:,}")


def ajukan_pinjam_siswa(conn, id_pengguna, info_siswa):
    judul("PENGAJUAN PEMINJAMAN BUKU", info_siswa)
    rows = jalankan(conn, """
        SELECT b.id_buku,
               b.judul,
               b.pengarang,
               r.nama_rak AS kategori,
               r.keterangan_lokasi AS lokasi_rak,
               (b.stok_total - COUNT(p.id_pinjam)) AS stok_tersedia
        FROM buku b
        JOIN rak r ON r.id_rak = b.id_rak
        LEFT JOIN peminjaman p
               ON p.id_buku = b.id_buku AND p.status = 'Dipinjam'
        GROUP BY b.id_buku, r.nama_rak, r.keterangan_lokasi
        HAVING (b.stok_total - COUNT(p.id_pinjam)) > 0
        ORDER BY b.id_buku ASC
    """)
    tabel(rows, [
        ("id_buku", "ID"),
        ("judul", "Judul Buku"),
        ("pengarang", "Pengarang"),
        ("kategori", "Rak"),
        ("lokasi_rak", "Lokasi Rak"),
        ("stok_tersedia", "Tersedia"),
    ])
    if not rows:
        return

    id_buku = input_int("\nMasukkan ID Buku yang akan dipinjam (0 = batal): ", 0)
    if id_buku == 0:
        return

    tgl_pinjam = datetime.now().replace(microsecond=0)
    tgl_kembali = tgl_pinjam + timedelta(days=BATAS_PINJAM_HARI)

    with conn:
        buku_lock = jalankan(conn, """
            SELECT b.id_buku, b.judul, b.stok_total, r.keterangan_lokasi
            FROM buku b
            JOIN rak r ON r.id_rak = b.id_rak
            WHERE b.id_buku = %s
            FOR UPDATE OF b
        """, (id_buku,))
        if not buku_lock:
            print("ID buku tidak ditemukan.")
            return

        dipinjam = jalankan(conn, """
            SELECT COUNT(*) AS jml
            FROM peminjaman
            WHERE id_buku = %s AND status = 'Dipinjam'
        """, (id_buku,))[0]["jml"]

        if (buku_lock[0]["stok_total"] - dipinjam) <= 0:
            print("Stok buku sedang habis atau baru saja dipinjam siswa lain.")
            return

        duplikat = jalankan(conn, """
            SELECT 1 FROM peminjaman
            WHERE id_pengguna = %s AND id_buku = %s AND status = 'Dipinjam'
        """, (id_pengguna, id_buku))
        if duplikat:
            print("Anda masih meminjam buku yang sama dan belum mengembalikannya.")
            return

        jalankan(conn, """
            INSERT INTO peminjaman (id_pengguna, id_buku, tanggal_pinjam, tanggal_kembali, status, denda)
            VALUES (%s, %s, %s, %s, 'Dipinjam', 0)
        """, (id_pengguna, id_buku, tgl_pinjam, tgl_kembali), fetch=False)

    print(f"Berhasil meminjam '{buku_lock[0]['judul']}' (Lokasi: {buku_lock[0]['keterangan_lokasi']}).")
    print(f"Tanggal Pinjam        : {tgl_pinjam.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Batas Tanggal Kembali : {tgl_kembali.strftime('%Y-%m-%d %H:%M:%S')} (Otomatis +7 hari)")
    print("Denda Awal            : Rp 0")


def kembalikan_buku_siswa(conn, id_pengguna, info_siswa):
    judul("PENGEMBALIAN BUKU", info_siswa)
    rows = jalankan(conn, """
        SELECT p.id_pinjam,
               b.judul,
               r.keterangan_lokasi AS lokasi_rak,
               to_char(p.tanggal_pinjam, 'YYYY-MM-DD HH24:MI') AS tgl_pinjam,
               to_char(p.tanggal_kembali, 'YYYY-MM-DD') AS batas_kembali,
               p.tanggal_kembali AS raw_batas
        FROM peminjaman p
        JOIN buku b ON b.id_buku = p.id_buku
        JOIN rak r ON r.id_rak = b.id_rak
        WHERE p.id_pengguna = %s AND p.status = 'Dipinjam'
        ORDER BY p.tanggal_pinjam
    """, (id_pengguna,))
    tabel(rows, [
        ("id_pinjam", "ID Pinjam"),
        ("judul", "Judul Buku"),
        ("lokasi_rak", "Lokasi Rak"),
        ("tgl_pinjam", "Tgl Pinjam"),
        ("batas_kembali", "Batas Kembali"),
    ])
    if not rows:
        return

    idp = input_int("\nMasukkan ID Pinjam yang dikembalikan (0 = batal): ", 0)
    if idp == 0:
        return

    target = [r for r in rows if r["id_pinjam"] == idp]
    if not target:
        print("ID Pinjam tidak valid.")
        return

    sekarang = datetime.now().replace(microsecond=0)
    denda = hitung_estimasi_denda(target[0]["raw_batas"], sekarang)

    with conn:
        jalankan(conn, """
            UPDATE peminjaman
            SET status = 'Dikembalikan',
                tanggal_dikembalikan = %s,
                denda = %s
            WHERE id_pinjam = %s AND id_pengguna = %s
        """, (sekarang, denda, idp, id_pengguna), fetch=False)

    print(f"Buku '{target[0]['judul']}' telah dikembalikan pada {sekarang.strftime('%Y-%m-%d %H:%M:%S')}.")
    print(f"Silakan kembalikan fisik buku ke: {target[0]['lokasi_rak']}.")
    print(f"Status Denda: Rp {denda:,}" + (" (Dapat diajukan pembebasan ke Admin jika ada alasan valid)" if denda > 0 else ""))


# --------------------------------------------------------------- role admin
def login_admin(conn):
    a = None
    for sisa in range(MAX_PERCOBAAN_LOGIN, 0, -1):
        judul("LOGIN ADMIN")
        nip = input("NIP      : ").strip()
        pw = getpass.getpass("Password : ")
        rows = jalankan(conn, """
            SELECT id_pengguna, identitas, nama
            FROM pengguna
            WHERE role = 'ADMIN' AND identitas = %s AND password_hash = crypt(%s, password_hash)
        """, (nip, pw))
        if rows:
            a = rows[0]
            break
        print(f"NIP atau password salah. Sisa percobaan: {sisa - 1}")
        jeda()

    if not a:
        return

    info_admin = f"Admin: {a['nama']} | NIP: {a['identitas']}"
    while True:
        judul("DASHBOARD ADMIN PERPUSTAKAAN", info_admin)
        tampilkan_info_operasional(conn)
        print("1. Rekap Laporan (Kunjungan & Peminjaman)")
        print("2. Kelola Data Katalog Buku & Lokasi Rak")
        print("3. Pembaruan Informasi Jam Operasional")
        print("4. Konfirmasi Transaksi Peminjaman, Pengembalian & Validasi Denda")
        print("0. Logout")
        garis("-")
        p = input("Pilih menu: ").strip()
        if p == "1":
            rekap_laporan_admin(conn, info_admin)
            jeda()
        elif p == "2":
            kelola_buku_admin(conn, info_admin)
        elif p == "3":
            update_operasional_admin(conn, info_admin)
            jeda()
        elif p == "4":
            konfirmasi_transaksi_admin(conn, info_admin)
            jeda()
        elif p == "0":
            print("Anda telah logout dari sesi Admin.")
            jeda()
            return
        else:
            print("Pilihan tidak valid.")
            jeda()


def rekap_laporan_admin(conn, info_admin):
    judul("REKAP LAPORAN KUNJUNGAN & PEMINJAMAN", info_admin)
    print("[A. REKAP KUNJUNGAN TERBARU (SISWA & TAMU)]")
    kunj = jalankan(conn, """
        SELECT k.id_kunjungan,
               u.role,
               COALESCE(u.identitas, '-') AS identitas,
               u.nama,
               COALESCE(u.kelas, u.asal_instansi, '-') AS ket,
               to_char(k.waktu_checkin, 'YYYY-MM-DD HH24:MI') AS checkin,
               COALESCE(to_char(k.waktu_checkout, 'YYYY-MM-DD HH24:MI'), 'Aktif') AS checkout,
               COALESCE(k.durasi_menit::text || ' mnt', '-') AS durasi
        FROM kunjungan k
        JOIN pengguna u ON u.id_pengguna = k.id_pengguna
        ORDER BY k.waktu_checkin DESC
        LIMIT 15
    """)
    tabel(kunj, [
        ("id_kunjungan", "ID"),
        ("role", "Role"),
        ("identitas", "NISN/NIP"),
        ("nama", "Nama"),
        ("ket", "Kelas/Instansi"),
        ("checkin", "Check-In"),
        ("checkout", "Check-Out"),
        ("durasi", "Durasi"),
    ])

    print("\n[B. REKAP TRANSAKSI PEMINJAMAN]")
    pinjam = jalankan(conn, """
        SELECT p.id_pinjam,
               u.nama AS peminjam,
               b.judul,
               to_char(p.tanggal_pinjam, 'YYYY-MM-DD') AS tgl_pinjam,
               to_char(p.tanggal_kembali, 'YYYY-MM-DD') AS batas_kembali,
               p.status,
               'Rp ' || p.denda::text AS denda
        FROM peminjaman p
        JOIN pengguna u ON u.id_pengguna = p.id_pengguna
        JOIN buku b ON b.id_buku = p.id_buku
        ORDER BY p.id_pinjam DESC
        LIMIT 15
    """)
    tabel(pinjam, [
        ("id_pinjam", "ID"),
        ("peminjam", "Siswa"),
        ("judul", "Judul Buku"),
        ("tgl_pinjam", "Pinjam"),
        ("batas_kembali", "Batas Kembali"),
        ("status", "Status"),
        ("denda", "Denda"),
    ])


def kelola_buku_admin(conn, info_admin):
    while True:
        judul("KELOLA DATA KATALOG BUKU & LOKASI RAK", info_admin)
        print("1. Lihat Semua Katalog Buku & Lokasi Rak")
        print("2. Tambah Buku / Modul / LKS Baru")
        print("3. Ubah Data Buku")
        print("4. Hapus Buku")
        print("5. Kelola Daftar Lokasi Rak")
        print("0. Kembali ke Menu Utama")
        garis("-")
        p = input("Pilih menu: ").strip()
        try:
            if p == "1":
                lihat_katalog(conn, info_admin)
                jeda()
            elif p == "2":
                print("\n--- Tambah Data Buku Baru ---")
                j = input("Judul Buku                       : ").strip()
                pg = input("Pengarang                        : ").strip()
                if not j or not pg:
                    print("Judul dan Pengarang wajib diisi.")
                    jeda()
                    continue
                pn = input("Penerbit (kosongkan jika NULL)   : ").strip() or None
                th = input_int("Tahun Terbit (kosongkan jika NULL): ", 1000, wajib=False)
                if th is not None and th > 2100:
                    print("Tahun terbit maksimal adalah 2100.")
                    jeda()
                    continue

                daftar_rak = tampilkan_daftar_rak(conn)
                if not daftar_rak:
                    print("Belum ada data rak. Tambahkan rak terlebih dahulu.")
                    jeda()
                    continue
                id_rak = input_int("\nPilih ID Rak                     : ", 1)
                if not any(r["id_rak"] == id_rak for r in daftar_rak):
                    print("ID Rak tidak ditemukan.")
                    jeda()
                    continue

                st = input_int("Stok Total                       : ", 0)
                with conn:
                    jalankan(conn, """
                        INSERT INTO buku (judul, pengarang, penerbit, tahun_terbit, id_rak, stok_total)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (j, pg, pn, th, id_rak, st), fetch=False)
                print("Buku baru berhasil ditambahkan ke katalog.")
                jeda()
            elif p == "3":
                lihat_katalog(conn, info_admin)
                idb = input_int("\nID Buku yang akan diubah (0 = batal): ", 0)
                if idb == 0:
                    continue
                j = input("Judul baru (kosong = tetap)       : ").strip()
                pg = input("Pengarang baru (kosong = tetap)   : ").strip()
                pn = input("Penerbit baru (kosong = tetap, '-' = set NULL): ").strip()
                th = input("Tahun baru (kosong = tetap, '-' = set NULL)   : ").strip()

                daftar_rak = tampilkan_daftar_rak(conn)
                rak_in = input("\nID Rak baru (kosong = tetap)      : ").strip()
                if rak_in == "":
                    val_rak = None
                elif rak_in.isdigit() and any(r["id_rak"] == int(rak_in) for r in daftar_rak):
                    val_rak = int(rak_in)
                else:
                    print("ID Rak tidak valid.")
                    jeda()
                    continue

                st = input_int("Stok Total baru (kosong = tetap)  : ", 0, wajib=False)

                if pn == "-":
                    sql_pn, val_pn = "NULL", None
                elif pn == "":
                    sql_pn, val_pn = "penerbit", None
                else:
                    sql_pn, val_pn = "%s", pn

                if th == "-":
                    sql_th, val_th = "NULL", None
                elif th == "":
                    sql_th, val_th = "tahun_terbit", None
                elif th.isdigit() and 1000 <= int(th) <= 2100:
                    sql_th, val_th = "%s::smallint", int(th)
                else:
                    print("Tahun terbit tidak valid (harus angka 1000-2100 atau '-').")
                    jeda()
                    continue

                params = []
                if val_pn is not None:
                    params.append(val_pn)
                if val_th is not None:
                    params.append(val_th)
                params.extend([j, pg, val_rak, st, idb])

                with conn:
                    n = jalankan(conn, f"""
                        UPDATE buku
                        SET penerbit = {sql_pn},
                            tahun_terbit = {sql_th},
                            judul = COALESCE(NULLIF(%s, ''), judul),
                            pengarang = COALESCE(NULLIF(%s, ''), pengarang),
                            id_rak = COALESCE(%s, id_rak),
                            stok_total = COALESCE(%s, stok_total)
                        WHERE id_buku = %s
                    """, tuple(params), fetch=False)
                print("Data buku berhasil diperbarui." if n else "ID buku tidak ditemukan.")
                jeda()
            elif p == "4":
                lihat_katalog(conn, info_admin)
                idb = input_int("\nID Buku yang dihapus (0 = batal): ", 0)
                if idb == 0:
                    continue
                with conn:
                    n = jalankan(conn, "DELETE FROM buku WHERE id_buku = %s", (idb,), fetch=False)
                print("Buku berhasil dihapus." if n else "ID buku tidak ditemukan.")
                jeda()
            elif p == "5":
                tampilkan_daftar_rak(conn)
                print("\n1. Tambah Rak Baru | 2. Ubah Lokasi Rak | 0. Kembali")
                sub = input("Pilih aksi: ").strip()
                if sub == "1":
                    nama_r = input("Nama Kategori/Rak baru : ").strip()
                    lok_r = input("Keterangan Lokasi      : ").strip()
                    if not nama_r or not lok_r:
                        print("Nama rak dan lokasi wajib diisi.")
                    else:
                        with conn:
                            jalankan(conn, """
                                INSERT INTO rak (nama_rak, keterangan_lokasi)
                                VALUES (%s, %s)
                            """, (nama_r, lok_r), fetch=False)
                        print("Rak baru berhasil ditambahkan.")
                elif sub == "2":
                    idr = input_int("ID Rak yang diubah (0 = batal): ", 0)
                    if idr != 0:
                        nama_r = input("Nama Rak baru (kosong = tetap)  : ").strip()
                        lok_r = input("Lokasi baru (kosong = tetap)    : ").strip()
                        with conn:
                            n = jalankan(conn, """
                                UPDATE rak
                                SET nama_rak = COALESCE(NULLIF(%s, ''), nama_rak),
                                    keterangan_lokasi = COALESCE(NULLIF(%s, ''), keterangan_lokasi)
                                WHERE id_rak = %s
                            """, (nama_r, lok_r, idr), fetch=False)
                        print("Data rak diperbarui." if n else "ID Rak tidak ditemukan.")
                jeda()
            elif p == "0":
                return
            else:
                print("Pilihan tidak valid.")
                jeda()
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            print("Gagal: Nama rak sudah terdaftar.")
            jeda()
        except psycopg2.errors.ForeignKeyViolation:
            conn.rollback()
            print("Gagal: Data tidak dapat dihapus karena masih digunakan pada riwayat/katalog.")
            jeda()
        except psycopg2.Error as e:
            conn.rollback()
            print("Kesalahan database:", e.diag.message_primary or str(e))
            jeda()


def update_operasional_admin(conn, info_admin):
    judul("PEMBARUAN INFORMASI JAM OPERASIONAL", info_admin)
    tampilkan_info_operasional(conn)
    jam_baru = input("Jam Operasional baru (kosong = tetap): ").strip()
    pengumuman_baru = input("Pengumuman layanan baru (misal: Jumat tutup lebih awal, kosong = tetap): ").strip()
    if not jam_baru and not pengumuman_baru:
        print("Tidak ada perubahan yang disimpan.")
        return

    sekarang = datetime.now().replace(microsecond=0)
    with conn:
        jalankan(conn, """
            UPDATE info_operasional
            SET jam_operasional = COALESCE(NULLIF(%s, ''), jam_operasional),
                pengumuman = COALESCE(NULLIF(%s, ''), pengumuman),
                updated_at = %s
            WHERE id_info = 1
        """, (jam_baru, pengumuman_baru, sekarang), fetch=False)
    print("Informasi jam operasional berhasil diperbarui.")


def konfirmasi_transaksi_admin(conn, info_admin):
    judul("KONFIRMASI TRANSAKSI & VALIDASI DENDA", info_admin)
    rows = jalankan(conn, """
        SELECT p.id_pinjam,
               u.identitas AS nisn,
               u.nama AS siswa,
               b.judul,
               to_char(p.tanggal_pinjam, 'YYYY-MM-DD') AS tgl_pinjam,
               to_char(p.tanggal_kembali, 'YYYY-MM-DD') AS batas_kembali,
               p.tanggal_dikembalikan,
               p.status,
               p.denda,
               COALESCE(p.keterangan_denda, '-') AS ket_denda,
               p.tanggal_kembali AS raw_batas
        FROM peminjaman p
        JOIN pengguna u ON u.id_pengguna = p.id_pengguna
        JOIN buku b ON b.id_buku = p.id_buku
        ORDER BY p.id_pinjam DESC
    """)
    tabel(rows, [
        ("id_pinjam", "ID"),
        ("nisn", "NISN"),
        ("siswa", "Nama Siswa"),
        ("judul", "Judul Buku"),
        ("tgl_pinjam", "Pinjam"),
        ("batas_kembali", "Batas"),
        ("status", "Status"),
        ("denda", "Denda"),
        ("ket_denda", "Ket. Denda"),
    ])
    if not rows:
        return

    idp = input_int("\nPilih ID Pinjam yang akan dikonfirmasi/divalidasi (0 = batal): ", 0)
    if idp == 0:
        return

    target = [r for r in rows if r["id_pinjam"] == idp]
    if not target:
        print("ID Pinjam tidak ditemukan.")
        return

    t = target[0]
    print(f"\nTransaksi #{idp} | {t['siswa']} - '{t['judul']}' (Status saat ini: {t['status']})")
    print("Pilih Status Baru (ENUM Database):")
    print("  1. Dipinjam")
    print("  2. Dikembalikan")
    print("  3. Rusak")
    pilih_st = input("Pilihan status (1/2/3): ").strip()
    if pilih_st not in STATUS_OPSI:
        print("Pilihan status tidak valid.")
        return

    status_baru = STATUS_OPSI[pilih_st]
    sekarang = datetime.now().replace(microsecond=0)

    if status_baru == "Dipinjam":
        tgl_dikembalikan = None
        denda_final = 0
        ket_denda = None
    else:
        tgl_dikembalikan = t["tanggal_dikembalikan"] or sekarang
        denda_otomatis = hitung_estimasi_denda(t["raw_batas"], tgl_dikembalikan)
        denda_final = max(t["denda"], denda_otomatis)
        ket_denda = None

        if status_baru == "Rusak":
            denda_rusak = input_int("Masukkan nominal denda kerusakan buku (Rp): ", 0)
            denda_final += denda_rusak

        print(f"Nominal denda terhitung: Rp {denda_final:,}")
        if denda_final > 0:
            bebas = input("Apakah siswa memiliki alasan valid (misal: sakit) untuk pembebasan denda menjadi 0? (y/N): ").strip().lower()
            if bebas == "y":
                alasan = input("Masukkan alasan pembebasan denda: ").strip() or "Alasan valid terverifikasi Admin"
                denda_final = 0
                ket_denda = f"Dibebaskan (Rp 0): {alasan}"
            else:
                ket_denda = "Denda tervalidasi Admin"

    with conn:
        jalankan(conn, """
            UPDATE peminjaman
            SET status = %s::status_peminjaman,
                tanggal_dikembalikan = %s,
                denda = %s,
                keterangan_denda = %s
            WHERE id_pinjam = %s
        """, (status_baru, tgl_dikembalikan, denda_final, ket_denda, idp), fetch=False)

    print(f"Transaksi #{idp} diperbarui -> Status: {status_baru} | Denda Final: Rp {denda_final:,}.")


# --------------------------------------------------------------- main
def main():
    try:
        conn = koneksi()
    except psycopg2.Error as e:
        sys.exit(f"Gagal terhubung ke database PostgreSQL: {e}")

    try:
        while True:
            judul("SIMPUS - SISTEM MANAJEMEN PERPUSTAKAAN SEKOLAH")
            tampilkan_info_operasional(conn)
            print("1. Login Admin")
            print("2. Login Siswa (NISN)")
            print("3. Masuk sebagai Tamu (Guest Mode)")
            print("0. Keluar Aplikasi")
            garis("-")
            p = input("Pilih peran akses: ").strip()
            if p == "1":
                login_admin(conn)
            elif p == "2":
                login_siswa(conn)
            elif p == "3":
                menu_tamu(conn)
            elif p == "0":
                bersihkan_layar()
                tampilkan_header()
                print("Terima kasih telah menggunakan SIMPUS.".center(lebar_terminal()))
                garis("=")
                break
            else:
                print("Pilihan tidak valid.")
                jeda()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram dihentikan.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
    