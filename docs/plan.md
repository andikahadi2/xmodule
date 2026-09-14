# Plan: Import Produk TikTok Shop ke Modul Affiliate

## Ringkasan temuan riset (dasar plan ini)

| Hal | Status |
|---|---|
| Endpoint pencarian produk | Ada: `POST /affiliate_creator/202405/open_collaboration/products/search` |
| Butuh akun seller? | Tidak — jalur `affiliate_creator` cukup |
| Generate affiliate link via API | Ada: `POST /affiliate_creator/202405/links/general/generate` |
| Ranking "paling laris" | **Tidak ada** — hanya filter kategori & rate komisi |
| Tersedia di Indonesia | **Belum terkonfirmasi** — portal terpisah `partner.tokopedia.com` |
| Gate creator | 1.000 follower |

Auth TikTok Shop **berbeda total** dari Content Posting API yang sudah ada (`app_key` bukan `client_key`, host lain, wajib HMAC-SHA256 signing tiap request) — jadi provider baru, bukan perluasan `app/providers/social/tiktok.py`.

Endpoint yang tersedia mengembalikan produk *open collaboration* (produk yang membuka kerja sama afiliasi), **bukan ranking "paling laris"**. Bisa filter/sort berdasar kategori dan rate komisi, tapi "barang yang sering dibeli" dalam arti ranking GMV/penjualan bukan konsep yang ada di API ini. Kalau yang dibutuhkan benar-benar data trending, itu ranah EchoTik (API resmi, tapi enterprise-priced) — bukan scraping, karena melanggar ToS TikTok dan prinsip proyek ini (lihat README poin soal PDF poin 27).

---

## Fase 0 — Verifikasi akses (blocking, sebelum kode ditulis)

Jangan lanjut Fase 2+ sebelum ini jelas.

1. Buka `partner.tokopedia.com` (untuk ID) atau `partner.tiktokshop.com` — cek apakah bisa daftar app developer.
2. Cek apakah akun TikTok sudah punya status **affiliate creator** (butuh 1.000 follower).
3. Kalau bisa daftar app: catat `app_key` + `app_secret`, cek apakah scope `affiliate_creator` tersedia di daftar permission.
4. Konfirmasi endpoint `open_collaboration/products/search` muncul di dokumentasi portal versi Indonesia.

**Hasil yang mungkin:**
- Semua tersedia → lanjut Fase 1–5 penuh.
- Indonesia tidak didukung / tidak eligible → Fase 1, 3, 4 tetap berguna, sumber datanya diganti (import CSV manual atau EchoTik). Arsitekturnya sengaja dibuat provider-agnostic untuk ini.

---

## Fase 1 — Fondasi: abstraksi sumber produk `[aman dikerjakan sekarang]`

Tidak bergantung hasil Fase 0. Bisa dikerjakan paralel.

**File baru:**
- `app/providers/product_source/base.py` — `ProductSourceProvider` ABC dengan `search(query, category, min_commission, limit) -> list[ProductCandidate]`, plus `ProductSourceError`. Mengikuti pola `app/providers/ai/base.py` yang sudah ada.
- `app/providers/product_source/manual.py` — provider CSV/list. Ini yang bikin Fase 0 tidak memblokir semuanya.

**Kenapa ini duluan:** kalau TikTok Shop ID ternyata tertutup, tetap ada jalur import yang jalan, tinggal tukar provider.

**Perubahan model:** tidak ada tabel baru. `Product` sudah punya `source`, `commission`, `rating`, `sales_count`. Cukup tambah kolom `external_id: str | None` + unique constraint `(source, external_id)` untuk dedup — satu migrasi Alembic kecil.

---

## Fase 2 — Provider TikTok Shop `[gated Fase 0]`

**File baru:** `app/providers/product_source/tiktok_shop.py`

Yang harus benar di sini, karena ini sumber bug tersembunyi:
- **Signing HMAC-SHA256**: sort param (kecuali `sign`/`access_token`) → concat `{key}{value}` → prepend path → append raw body bytes → bungkus `app_secret + str + app_secret`. Kalau body di-serialize ulang, urutan key berubah dan signature gagal.
- **Cek `code === 0` di JSON**, bukan HTTP status — TikTok Shop balas HTTP 200 untuk error.
- **Token**: access ~7 hari, refresh ~365 hari. Baca dari response, jangan hardcode.
- **Rate limit dinamis** (leaky bucket, tidak ada API untuk cek kuota) → wajib backoff saat 429, pola sama seperti retry backoff di provider lain.

**Config baru:** `tiktok_shop_app_key`, `tiktok_shop_app_secret` — terpisah dari `tiktok_client_key/secret` yang sudah ada. Jangan dicampur, beda app.

---

## Fase 3 — Scoring produk `[aman dikerjakan sekarang]`

**File baru:** `app/services/product_score.py` — fungsi murni, mudah dites.

Karena API tidak kasih ranking terlaris, skor dihitung lokal dari data yang ada:

```
score = (commission_rate × bobot) + (rating × bobot) + (log(sales_count) × bobot)
```

Satu fungsi, tanpa kelas, tanpa config eksternal. Bobot sebagai konstanta modul yang bisa di-tune — titik kalibrasi wajar untuk dibiarkan terbuka karena "produk bagus" itu subjektif dan perlu di-tuning dari hasil nyata.

Ditampilkan sebagai kolom urut di daftar produk, bukan tabel terpisah.

---

## Fase 4 — Import + dedup `[aman dikerjakan sekarang]`

**File baru:** `app/services/product_import.py`
**Route baru:** `POST /api/products/import` (body: daftar kandidat atau parameter pencarian + nama provider)

- Dedup via `(source, external_id)` — insert pakai `ON CONFLICT DO UPDATE` supaya import berulang me-refresh harga/komisi, bukan bikin duplikat.
- Untuk provider manual: terima CSV.
- Import besar → jalankan sebagai `BackgroundTask`, pola sama dengan `generate-video`.

---

## Fase 5 — UI `[aman dikerjakan sekarang]`

Tambah section di `app/templates/products.html`: form pencarian/import + tabel kandidat diurutkan skor, tombol "Import terpilih". HTMX, konsisten dengan dashboard yang ada.

---

## Testing

| Fase | Test |
|---|---|
| 2 | Signing HMAC terhadap vektor uji yang diketahui (paling rawan salah, wajib dites) |
| 2 | `code != 0` di JSON → lempar `ProductSourceError` |
| 3 | Scoring: urutan relatif benar, tahan `None` |
| 4 | Import dua kali → tidak duplikat, field ter-update |

---

## Urutan kerja yang disarankan

1. Verifikasi Fase 0 — ini menentukan apakah Fase 2 layak dibangun.
2. Sementara menunggu, Fase 1 + 3 + 4 bisa dikerjakan (abstraksi, scoring, import manual + dedup). Semuanya berguna terlepas dari hasil Fase 0.
3. Fase 2 dan 5 menyusul setelah akses terkonfirmasi.

**Catatan penting:** kalau yang benar-benar dibutuhkan adalah data "paling laris" (bukan sekadar produk yang buka afiliasi), TikTok Shop API bukan jawabannya — EchoTik yang punya data ranking penjualan, tapi harganya enterprise. Lebih baik dipastikan sebelum Fase 2 dibangun.
