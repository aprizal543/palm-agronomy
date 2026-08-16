# PalmAgronomy Backend — Sprint 5 v0.6.0

Fondasi Farm, Block, dan PostGIS untuk PalmAgronomy AI Agent. Database production-like
tetap PostgreSQL yang di-host Supabase; Docker Compose hanya disediakan sebagai opsi
pengujian lokal yang reproducible.

Sprint 2 menambahkan adapter Telegram dan orchestration layer di atas fondasi GIS.
PostGIS tetap menjadi source of truth; agent hanya boleh memanggil tool yang terdaftar.

Sprint 3 menambahkan konteks Farm/Block dan pencatatan produksi TBS yang wajib dikonfirmasi
manusia. PostgreSQL memvalidasi relasi farm-block serta hak tulis actor.

Sprint 4 menambahkan RAG agronomy yang hanya mengambil chunk dari sumber terverifikasi,
menampilkan citation, menolak menjawab saat evidence tidak cukup, dan menyimpan trace retrieval.

## Fitur Sprint 1

- FastAPI async + SQLAlchemy 2 + asyncpg.
- Schema privat `palm` dan PostGIS di schema `extensions`.
- Tiga migration Alembic: extension/enums, users/farms, blocks/spatial.
- Luas farm dan block dihitung oleh PostGIS, bukan dari client.
- Validasi polygon, cakupan block di dalam farm, dan toleransi overlap 1 m².
- `ST_Covers` untuk pencarian lokasi, termasuk titik tepat di batas polygon.
- Share Location disimpan sebagai GPS point + accuracy; tidak pernah diubah menjadi boundary.
- Resolusi lokasi mengembalikan `confirmation_required`/`ambiguous` ketika dekat batas.
- Luas pernyataan petani (`declared_area_ha`) dipisahkan dari luas PostGIS
  (`verified_area_m2`/`verified_area_ha`).
- Asal boundary diaudit sebagai map drawing, GPS track, GIS import, atau AI candidate.
- Otorisasi owner/member pada service layer.
- Seed sintetis kecil untuk demo dan fixture GIS untuk kasus invalid/overlap.
- Endpoint health, users, farms, blocks, validasi GeoJSON, dan pencarian lokasi.
- Endpoint mapping dan human validation terpisah untuk farm/block polygon.

## Fitur Sprint 2

- Parser payload Telegram untuk message, Location, dan callback query.
- Idempotency berdasarkan `update_id`, termasuk retry untuk proses gagal atau stale.
- Auto-onboarding Telegram user tanpa mengubah role user yang sudah ada.
- Conversation state dan active block context per chat.
- Pending confirmation 15 menit dengan inline keyboard untuk lokasi dekat batas/ambigu.
- Audit log ber-`trace_id` untuk intent, tool call, hasil, latency, dan human confirmation.
- Allow-list tool `resolve_block_by_location`; agent tidak menerima SQL/database handle.
- GPS `horizontal_accuracy` diteruskan apa adanya ke query PostGIS.
- Dua transport: polling untuk development lokal dan webhook ber-secret untuk deployment.
- Provider agent default `deterministic`; integrasi hosted LLM belum diperlukan untuk uji ini.

## Fitur Sprint 3

- Tabel `production_records` untuk berat TBS, jumlah tandan, tanggal panen, dan provenance.
- Invariant database memastikan block confirmed, block milik farm, dan actor memiliki hak tulis.
- Tool allow-list untuk konteks aktif, simpan produksi, riwayat, dan ringkasan.
- Perintah Telegram `/context`, `/produksi`, `/riwayat`, dan `/ringkasan`.
- Draft produksi kedaluwarsa setelah 15 menit dan tidak disimpan tanpa tombol **Simpan**.
- `confirmation_action_id` unik mencegah double-submit dari callback Telegram.
- Audit tool call dan human confirmation tanpa membuka SQL kepada Agent.

## Fitur Sprint 4

- Tabel source, chunk, dan query log pada schema privat `palm`.
- Metadata sumber wajib: judul, penerbit, URL, checksum, origin, dan status verifikasi.
- Hanya sumber `verified` yang dapat masuk hasil retrieval.
- PostgreSQL full-text search sebagai baseline retrieval deterministik berbahasa Indonesia.
- Stopword domain mencegah kata umum `kelapa/sawit/tanaman` menarik chunk tak relevan.
- Extension `pgvector` dan kolom embedding 1536 dimensi disiapkan untuk semantic retrieval.
- Tool allow-list `retrieve_agronomy_knowledge`; Agent tetap tidak memiliki raw SQL.
- `/tanya <pertanyaan>` mengembalikan evidence, citation ringkas, dan safety note.
- URL sumber tetap tersimpan untuk provenance/audit dan respons API, tetapi tidak ditampilkan
  di Telegram agar tautan serta pratinjau PDF tidak memenuhi percakapan.
- Jawaban `insufficient_evidence` menolak menebak ketika tidak ada sumber yang cocok.
- Endpoint read-only `GET /api/v1/knowledge/search` untuk evaluasi retrieval.
- Generic ingestion selalu berstatus `pending` hingga ditinjau curator.

## Fitur Sprint 5

- Router deterministik memisahkan pertanyaan operasional dan pertanyaan agronomi.
- Pertanyaan `/tanya` tentang kondisi produksi membaca blok aktif dan `production_records`.
- Analisis menampilkan produksi terakhir, tandan, luas PostGIS, hasil kg/ha, dan tanggal.
- Satu catatan tidak dinyatakan sebagai tren; bot menyampaikan keterbatasan evidence.
- Pertanyaan agronomi seperti pemupukan atau gulma tetap menggunakan RAG terverifikasi.
- Seluruh pemanggilan tool konteks dan riwayat tetap masuk audit log ber-`trace_id`.

## Menjalankan dengan Supabase

1. Buat project Supabase dan ambil connection string database.
2. Salin `.env.example` menjadi `.env`; jangan commit file `.env`.
3. Isi `DATABASE_URL` dengan session pooler dan `MIGRATION_DATABASE_URL` dengan direct URL.
4. Jalankan:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m alembic upgrade head
python -m scripts.seed_synthetic
python -m scripts.seed_rag_demo
python -m uvicorn app.main:app --reload
```

Dokumentasi API tersedia di `http://127.0.0.1:8000/docs`.

## Menjalankan Telegram secara lokal (polling)

1. Buat bot melalui `@BotFather`, lalu simpan token hanya di `.env`.
2. Tambahkan/ubah nilai berikut:

```env
TELEGRAM_ENABLED=true
TELEGRAM_MODE=polling
TELEGRAM_BOT_TOKEN=token_dari_botfather
TELEGRAM_WEBHOOK_SECRET=secret_acak_untuk_nanti
```

3. Terapkan migration dan jalankan polling:

```powershell
python -m alembic upgrade head
python -m alembic current
python -m scripts.run_telegram_polling
```

Jangan jalankan Uvicorn webhook dan polling secara bersamaan. Script polling menghapus
registrasi webhook lama tanpa membuang pending updates, karena Telegram tidak mengizinkan
`getUpdates` saat webhook aktif.

Jika pemrosesan sebuah update gagal sementara (misalnya koneksi database terputus), polling
tidak langsung mengakuinya. Update yang sama dicoba kembali hingga tiga kali sebelum dilewati
sebagai failed/poison update; detail aman tetap tersedia pada tabel audit.

## Menjalankan Telegram via webhook

Set `TELEGRAM_MODE=webhook`, deploy API pada URL HTTPS publik, lalu daftarkan:

```text
POST https://api.telegram.org/bot<TOKEN>/setWebhook
url=https://<HOST>/api/v1/telegram/webhook
secret_token=<TELEGRAM_WEBHOOK_SECRET>
allowed_updates=["message","callback_query"]
```

Endpoint memverifikasi header `X-Telegram-Bot-Api-Secret-Token`. Jangan menaruh token bot,
database password, atau webhook secret di source, screenshot, log, maupun GitHub.

## Perintah produksi Telegram

Pilih blok aktif terlebih dahulu dengan mengirim Location dari area blok. Akun juga harus
merupakan owner atau member farm dengan role `editor`/`validator`.

```text
/context
/produksi 1250 80
/produksi 900 - 2026-08-15
/riwayat 5
/ringkasan 30
/tanya bagaimana kondisi produksi blok saya?
/tanya kapan waktu pemupukan kelapa sawit?
```

Format `/produksi` adalah berat TBS dalam kg, jumlah tandan opsional (`-` jika kosong), dan
tanggal opsional berformat ISO. Data baru masuk `production_records` setelah pengguna menekan
tombol **Simpan**.

## RAG Agronomy

Seed acceptance memakai ringkasan terkurasi dari dokumen resmi Kementerian Pertanian:

```powershell
python -m scripts.seed_rag_demo
python -m scripts.run_telegram_polling
```

Uji evidence tersedia dan evidence tidak tersedia:

```text
/tanya kapan waktu pemupukan kelapa sawit?
/tanya bagaimana mengatur antena satelit di bulan?
```

Jawaban pertama harus menyertakan citation tanpa URL/PDF preview. Jawaban kedua harus
menyatakan evidence tidak cukup dan tidak boleh membuat rekomendasi. Seed bersifat idempotent.

Untuk memasukkan dokumen sendiri, salin `docs/knowledge_ingest.example.json`, lalu jalankan:

```powershell
python -m scripts.ingest_knowledge_json docs\knowledge_ingest.example.json
```

Dokumen umum selalu masuk sebagai `pending`; chunk belum dapat diambil sampai metadata dan
isinya ditinjau lalu status source diubah menjadi `verified` oleh curator. Full-text retrieval
aktif pada Sprint 4. Kolom pgvector tersedia, tetapi embedding belum dihasilkan sampai provider
embedding dipilih dan dievaluasi pada corpus nyata.

## Pengujian lokal dengan PostGIS

```bash
docker compose up -d db
cp .env.example .env
# Ubah URL ke postgresql+asyncpg://palm:palm@localhost:5432/palm
alembic upgrade head
pytest
```

Untuk menjalankan integration test, set `TEST_DATABASE_URL` ke database PostGIS khusus tes.
Jangan menunjuk ke database berisi data penting karena fixture membuat dan menghapus record.

## Kontrak GeoJSON dan GPS

Boundary farm menerima `Polygon` atau `MultiPolygon`; boundary block hanya menerima
`Polygon`. Koordinat selalu berurutan `[longitude, latitude]` pada EPSG:4326.
Nilai `area_m2` dan `area_ha` pada respons berasal dari trigger PostGIS.

`location_point` adalah titik `[longitude, latitude]`, bukan polygon. Sertakan
`location_accuracy_m` dari Telegram/smartphone bila tersedia. Endpoint pencarian lokasi
tidak menebak satu blok ketika radius akurasi menyentuh batas atau lebih dari satu kandidat.

## Batas Sprint

Hosted generative LLM, semantic embedding pipeline, rekomendasi tindakan spesifik blok,
cuaca, ML, Vision, dan deployment production belum diaktifkan. Sprint 5 memberikan analisis
produksi kontekstual deterministik serta extractive-grounded
answer dari corpus terverifikasi; sistem belum boleh disebut semantic RAG sebelum embedding
provider dan retrieval evaluation diselesaikan.
