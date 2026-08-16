# Sprint 1 Handoff — Farm, Block, dan PostGIS

## Status

Implementasi kode: **selesai**. Validasi pada Supabase aktual: **menunggu connection string project**.

## Hasil terhadap acceptance criteria

| ID | Status | Implementasi |
|---|---|---|
| DB-01 | Siap diuji DB | Unique Telegram ID + endpoint registrasi |
| DB-02 | Siap diuji DB | Unique index `(owner_id, lower(name))` |
| GIS-01 | Siap diuji DB | Trigger menghitung m² dan ha |
| GIS-02 | Siap diuji DB | `ST_IsValid` + alasan invalid |
| GIS-03 | Siap diuji DB | `ST_CoveredBy(block, farm)` |
| GIS-04 | Siap diuji DB | Overlap hanya ditolak jika irisan >1 m² |
| GIS-05 | Siap diuji DB | Intersection geography + advisory lock |
| GIS-06 | Siap diuji DB | Function `resolve_blocks_by_location` |
| GIS-07 | Siap diuji DB | `ST_Covers` + GPS accuracy + jarak ke boundary |
| SEC-01 | Siap diuji DB | Owner atau member editor/validator |
| DATA-01 | Selesai | Seed diberi `data_origin='synthetic'` |

## Endpoint

| Method | Path | Tujuan |
|---|---|---|
| GET | `/api/v1/health` | Liveness aplikasi |
| GET | `/api/v1/health/database` | Konektivitas database |
| POST | `/api/v1/users` | Registrasi pengguna |
| GET | `/api/v1/users/telegram/{id}` | Resolusi identitas Telegram |
| POST | `/api/v1/farms` | Membuat kebun |
| GET | `/api/v1/farms/{id}` | Membaca kebun + GeoJSON |
| PATCH | `/api/v1/farms/{id}/boundary` | Map/import farm polygon |
| PATCH | `/api/v1/farms/{id}/validation` | Human approve/reject farm polygon |
| POST | `/api/v1/blocks` | Membuat blok dengan otorisasi |
| GET | `/api/v1/blocks/{id}` | Membaca blok + luas PostGIS |
| PATCH | `/api/v1/blocks/{id}/validation` | Human approve/reject block polygon |
| POST | `/api/v1/blocks/validate-geometry` | Pra-validasi polygon |
| GET | `/api/v1/blocks/by-location` | Resolusi GPS point ke block dengan uncertainty |

## Knowledge update Farm & Block

- Share Location hanya disimpan sebagai point; tidak membuat farm boundary.
- `declared_area_ha` adalah pernyataan user dan tetap unverified.
- `verified_area_m2/ha` hanya dihitung trigger PostGIS dari polygon.
- Polygon menyimpan provenance: `map_draw`, `gps_track`, `gis_import`, atau `ai_candidate`.
- AI candidate tidak pernah otomatis menjadi source of truth; status tetap membutuhkan validasi manusia.
- `accuracy_m` dan jarak titik ke boundary menentukan apakah hasil dapat dipakai langsung,
  perlu konfirmasi, ambigu, atau tidak ditemukan.

## Langkah yang membutuhkan akun Supabase

1. Buat project Supabase Free.
2. Catat direct database URL dan session pooler URL.
3. Masukkan keduanya hanya ke `.env` lokal/server.
4. Jalankan `alembic upgrade head`.
5. Jalankan seed, lalu tes skenario pada `tests/fixtures/gis_cases.json`.
6. Simpan bukti hasil migration dan test untuk penutupan Sprint 1.

Secret tidak perlu dikirim melalui chat atau dimasukkan ke repository.

## Gate menuju Sprint 2

Sprint 2 boleh dimulai setelah migration berhasil pada Supabase dan minimal GIS-01 sampai
GIS-07 lulus. Sprint 2 akan menambahkan produksi, pending confirmation, audit log,
idempotensi Telegram, dan Telegram adapter tanpa mengubah fondasi Farm/Block.
