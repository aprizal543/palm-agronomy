# PalmAgronomy Backend — Sprint 1 v0.2

Fondasi Farm, Block, dan PostGIS untuk PalmAgronomy AI Agent. Database production-like
tetap PostgreSQL yang di-host Supabase; Docker Compose hanya disediakan sebagai opsi
pengujian lokal yang reproducible.

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

## Menjalankan dengan Supabase

1. Buat project Supabase dan ambil connection string database.
2. Salin `.env.example` menjadi `.env`; jangan commit file `.env`.
3. Isi `DATABASE_URL` dengan session pooler dan `MIGRATION_DATABASE_URL` dengan direct URL.
4. Jalankan:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
python -m scripts.seed_synthetic
uvicorn app.main:app --reload
```

Dokumentasi API tersedia di `http://127.0.0.1:8000/docs`.

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

Telegram adapter, produksi, cuaca, Agent tool calling, RAG, dan Vision belum diaktifkan.
Modul tersebut masuk sprint berikutnya setelah fondasi GIS lolos pada Supabase aktual.
