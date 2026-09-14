# Affiliate Content Engine

Phase 1: project setup, PostgreSQL, Product CRUD, dashboard sederhana.
Phase 2: AI provider abstraction (OpenRouter, Ollama), Content Idea Generator, Script Generator.
Phase 3: Image provider (Pexels/local), TTS (Edge TTS), FFmpeg video generator, subtitle (SRT) —
menghasilkan video 9:16 lengkap dari product sampai file MP4.
Phase 5 (sebagian): TikTok Content Posting API (OAuth connect + publish ke Inbox/Draft, bukan
auto-publish) — lihat bagian "Connect TikTok" di bawah.

Module tambahan (`app/clipper/`, terpisah dari affiliate engine di atas): **Clipper** — upload video
sendiri, potong otomatis per durasi tetap, auto-caption (speech-to-text), opsional reformat ke 9:16.
Hanya menerima file upload manual — tidak ada fitur download dari URL/platform pihak ketiga mana pun
(lihat prinsip di poin 27 PDF: dilarang scraping/pakai asset tanpa izin).

## Menjalankan

1. Buat virtual environment dan install dependencies:

   ```
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```

2. Copy `.env.example` ke `.env` dan sesuaikan `DATABASE_URL` dengan PostgreSQL yang tersedia.
   Isi `OPENROUTER_API_KEY` jika ingin pakai OpenRouter (`AI_PROVIDER=openrouter`), atau jalankan
   Ollama lokal dan set `AI_PROVIDER=ollama`. Isi `PEXELS_API_KEY` untuk image provider (gratis di
   pexels.com/api). Pastikan `ffmpeg`/`ffprobe` ada di PATH atau set `FFMPEG_PATH` ke lokasi
   `ffmpeg.exe`. Untuk module Clipper: model faster-whisper "small" ter-download otomatis saat
   pertama kali dipakai (butuh koneksi internet sekali di awal, lalu tersimpan di cache lokal).
   Untuk Connect TikTok: daftar app di developers.tiktok.com (produk "Content Posting API"), isi
   `TIKTOK_CLIENT_KEY`/`TIKTOK_CLIENT_SECRET`, dan set `APP_BASE_URL` ke URL publik server ini
   (redirect URI yang didaftarkan di TikTok = `{APP_BASE_URL}/api/social/tiktok/callback`).

3. Buat database (jika belum ada), lalu jalankan migration:

   ```
   .venv\Scripts\alembic upgrade head
   ```

4. Jalankan server:

   ```
   .venv\Scripts\uvicorn app.main:app --reload
   ```

   - Dashboard: http://localhost:8000/
   - API: http://localhost:8000/api/products (docs: http://localhost:8000/docs)
   - Generate ide konten dari produk: `POST /api/contents/generate-ideas/{product_id}`
   - Generate script dari ide terpilih: `POST /api/contents/{content_id}/generate-script`
   - Generate media (gambar): `POST /api/contents/{content_id}/generate-media`
   - Generate audio (voice-over): `POST /api/contents/{content_id}/generate-audio`
   - Generate video final (MP4 9:16), berjalan async di background: `POST /api/contents/{content_id}/generate-video`
     — response langsung (202) berisi video row berstatus `processing`; poll `GET /api/contents/{content_id}`
     atau video endpoint sampai status jadi `ready` (atau `failed` + `error`).
   - Lihat konten: `GET /api/contents`, `GET /api/contents/{content_id}`

   Urutan pipeline penuh: `generate-ideas` → `generate-script` → `generate-media` →
   `generate-audio` → `generate-video`. Hasil video tersimpan di `storage/videos/`.

   **Connect TikTok & publish** (halaman `/affiliate`, tombol "Connect TikTok"):
   - `GET /api/social/tiktok/connect` — redirect user ke halaman consent TikTok
   - `GET /api/social/tiktok/callback` — dipanggil TikTok setelah user setuju, simpan token
   - `GET /api/social/accounts` — daftar akun terhubung
   - `DELETE /api/social/accounts/{id}` — putuskan koneksi
   - `POST /api/contents/videos/{video_id}/approve` — approve video (wajib sebelum publish,
     video harus berstatus `ready`)
   - `POST /api/contents/videos/{video_id}/publish/{account_id}` — kirim video ke Inbox/Draft
     TikTok akun tsb (bukan auto-publish — user tetap harus buka app TikTok untuk post akhir)

   **Clipper module** (upload & potong video sendiri):
   - Upload + proses (async di background): `POST /api/clipper/jobs` (multipart form-data:
     `file`, `segment_seconds` default 120, `reformat_vertical` default false, `auto_caption`
     default true)
   - Cek status & hasil: `GET /api/clipper/jobs/{job_id}`, `GET /api/clipper/jobs`
   - Hasil klip tersimpan di `storage/clips/`, subtitle di `storage/temp/`

## Test

```
.venv\Scripts\pytest
```

## Struktur

- `app/models` — SQLAlchemy models
- `app/schemas` — Pydantic schemas
- `app/services` — business logic (product CRUD)
- `app/api/routes` — FastAPI routes (JSON API + HTMX dashboard)
- `app/providers/ai` — AI provider abstraction (`OpenRouterProvider`, `OllamaProvider`); ganti lewat
  `AI_PROVIDER` di `.env`, jangan hard-code provider di business logic
- `app/providers/image` — image provider abstraction (`LocalImageProvider` pakai `image_url` produk,
  `PexelsProvider` fallback)
- `app/providers/tts` — TTS abstraction (`CloudTTSProvider` pakai Edge TTS gratis; `LocalTTSProvider`
  belum diimplementasi)
- `app/providers/social` — social media provider abstraction (`TikTokProvider` pakai OAuth v2 +
  Content Posting API Inbox mode — publish ke draft, bukan langsung live)
- `app/utils/ffmpeg.py` — pembungkus subprocess FFmpeg (video generator + probe durasi + extract
  segment, dipakai affiliate engine maupun clipper)
- `app/utils/subtitle.py` — generate SRT dari script + durasi audio
- `app/templates` — Jinja2 templates
- `app/clipper/` — module terpisah: model (`ClipJob`, `Clip`), service (`clip_service`,
  `caption_service` pakai faster-whisper), route (`/api/clipper/*`)
- `alembic/` — database migrations

Provider affiliate, social media, scheduler, dan job queue belum dibuat — menyusul di phase
berikutnya sesuai roadmap di `Automated Affiliate Content Engine.pdf`.
