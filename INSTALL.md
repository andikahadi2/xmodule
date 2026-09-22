# Panduan Instalasi

Panduan ini untuk pembeli yang baru pertama kali menjalankan aplikasi ini di komputer/server
sendiri. Ikuti urutan di bawah — tidak perlu paham semua bagian kode untuk bisa menjalankannya.

Lisensi pemakaian ada di [LICENSE.txt](LICENSE.txt) — baca dulu sebelum pakai.

## 1. Yang perlu disiapkan dulu

Install program-program ini kalau belum ada di komputer Anda:

| Program | Untuk apa | Link download |
|---|---|---|
| **Python 3.11+** | Menjalankan aplikasi | [python.org/downloads](https://www.python.org/downloads/) |
| **PostgreSQL 14+** | Database | [postgresql.org/download](https://www.postgresql.org/download/) |
| **FFmpeg** | Proses video (potong, gabung, subtitle) | [ffmpeg.org/download](https://ffmpeg.org/download.html) |

Saat install PostgreSQL, **catat password** yang Anda buat untuk user `postgres` — akan dipakai di
langkah 3.

Saat install FFmpeg, catat juga lokasi file `ffmpeg.exe` (Windows) atau pastikan `ffmpeg` bisa
dipanggil langsung dari terminal (coba ketik `ffmpeg -version`, kalau muncul versi berarti sudah
benar).

## 2. Install aplikasi

Buka terminal (Command Prompt/PowerShell di Windows, Terminal di Mac/Linux) di folder aplikasi ini,
lalu jalankan:

```
python -m venv .venv
```

Aktifkan virtual environment:

- **Windows**: `.venv\Scripts\activate`
- **Mac/Linux**: `source .venv/bin/activate`

Install semua library yang dibutuhkan:

```
pip install -r requirements.txt
```

Proses ini butuh beberapa menit tergantung koneksi internet.

## 3. Buat database

Buka `psql` atau tool database favorit Anda (pgAdmin, DBeaver, dll), lalu buat database baru:

```sql
CREATE DATABASE affiliate_engine;
```

Nama database boleh diganti, asal nanti disesuaikan juga di langkah 4.

## 4. Isi konfigurasi (.env)

Copy file `.env.example` menjadi `.env` (file baru, jangan edit `.env.example` langsung):

- **Windows**: `copy .env.example .env`
- **Mac/Linux**: `cp .env.example .env`

Buka file `.env` dengan text editor, lalu isi bagian-bagian berikut:

### Wajib diisi

- **`DATABASE_URL`** — ganti `postgres:root` dengan username:password PostgreSQL Anda, dan
  `affiliate_engine` dengan nama database dari langkah 3 kalau Anda pakai nama lain. Contoh:
  ```
  DATABASE_URL=postgresql+psycopg://postgres:PASSWORD_ANDA@localhost:5432/affiliate_engine
  ```
- **`FFMPEG_PATH`** — kalau `ffmpeg -version` di terminal sudah jalan, biarkan `FFMPEG_PATH=ffmpeg`.
  Kalau tidak, isi path lengkap ke `ffmpeg.exe` (Windows) atau binary ffmpeg Anda.
- **`ADMIN_USERNAME`** dan **`ADMIN_PASSWORD`** — ini login untuk masuk ke aplikasi. **Wajib diisi
  dengan password yang kuat**, jangan pakai contoh bawaan. Kosongkan kalau Anda sengaja tidak mau
  ada halaman login sama sekali (tidak disarankan, lihat bagian Keamanan di bawah).

### Isi sesuai kebutuhan fitur yang mau dipakai

- **`PEXELS_API_KEY`** — untuk fitur cari foto/video stock otomatis (gambar produk, footage AI
  video). Daftar gratis di [pexels.com/api](https://www.pexels.com/api/).
- **`OPENROUTER_API_KEY`** — untuk generate ide konten & script pakai AI (lewat OpenRouter). Daftar
  di [openrouter.ai](https://openrouter.ai/). Kalau tidak mau pakai OpenRouter, set
  `AI_PROVIDER=ollama` dan jalankan [Ollama](https://ollama.com/) di komputer sendiri sebagai
  gantinya (gratis, tanpa API key, tapi butuh spek komputer lebih besar).
- **`TIKTOK_CLIENT_KEY`** / **`TIKTOK_CLIENT_SECRET`** — hanya kalau mau pakai fitur publish
  otomatis ke TikTok. Daftar aplikasi di [developers.tiktok.com](https://developers.tiktok.com/)
  (produk "Content Posting API"). Isi juga `APP_BASE_URL` dengan alamat publik server Anda —
  itu dipakai sebagai redirect URL yang harus didaftarkan sama persis di TikTok.

Fitur lain (Clipper — potong video sendiri, transkrip otomatis) tidak butuh API key tambahan,
langsung jalan setelah instalasi.

## 5. Jalankan migrasi database

Perintah ini membuat semua tabel yang dibutuhkan aplikasi:

```
alembic upgrade head
```

Kalau berhasil, tidak akan ada pesan error — hanya baris log migrasi yang dijalankan.

## 6. Jalankan aplikasi

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Buka browser ke `http://localhost:8000` — akan muncul halaman login. Masuk pakai
`ADMIN_USERNAME`/`ADMIN_PASSWORD` yang tadi diisi di `.env`.

Untuk berhenti, tekan `Ctrl+C` di terminal.

## 7. Menjalankan sebagai layanan permanen (opsional)

Kalau mau aplikasi ini tetap jalan setelah terminal ditutup atau server restart, gunakan salah satu:

- **Windows**: jadwalkan lewat Task Scheduler, atau pakai [NSSM](https://nssm.cc/) untuk membuatnya
  jadi Windows Service.
- **Linux**: buat systemd service, atau pakai `pm2`/`supervisor`.

Detail setup ini di luar cakupan panduan ini karena tergantung server yang Anda pakai — cari
"run uvicorn as a service [nama OS Anda]" kalau butuh contoh lengkap.

## Keamanan sebelum diakses publik (bukan cuma localhost)

Kalau aplikasi ini akan diakses dari internet (bukan cuma dari komputer sendiri), **wajib**
lakukan ini dulu:

1. Pastikan `ADMIN_USERNAME`/`ADMIN_PASSWORD` di `.env` sudah diisi dengan password kuat (bukan
   contoh bawaan).
2. Set `APP_DEBUG=false` di `.env`.
3. Set `APP_BASE_URL` ke domain publik pakai `https://` (bukan `http://`).
4. **Jangan** jalankan langsung dengan `--reload` — itu hanya untuk development.
5. Pasang di belakang reverse proxy (nginx atau Caddy) dengan sertifikat TLS/SSL — jangan expose
   `uvicorn` langsung ke internet tanpa HTTPS.

## Masalah umum

**"could not connect to server" / database error saat `alembic upgrade head`**
→ Pastikan PostgreSQL sedang berjalan, dan `DATABASE_URL` di `.env` sudah benar (username,
password, nama database).

**Video tidak bisa diproses / "FFmpegError"**
→ Jalankan `ffmpeg -version` di terminal. Kalau gagal, `FFMPEG_PATH` di `.env` belum benar atau
FFmpeg belum ter-install.

**Tidak bisa login / lupa password**
→ Buka `.env`, cek/ganti nilai `ADMIN_USERNAME` dan `ADMIN_PASSWORD`, lalu restart aplikasi
(matikan dengan `Ctrl+C`, jalankan ulang perintah di langkah 6).

**Fitur pencarian foto/video stock tidak jalan**
→ Cek `PEXELS_API_KEY` sudah diisi di `.env` dan masih berlaku (cek di dashboard pexels.com).

**Generate ide konten/script AI gagal**
→ Cek `OPENROUTER_API_KEY` masih berlaku dan ada kuota, atau kalau pakai Ollama pastikan Ollama
sedang berjalan (`ollama serve`) dan modelnya sudah di-download (`ollama pull llama3.2`).
