# Sprint 7 — Deployment Readiness & Observability

## Definition of Done

- Versi aplikasi `0.8.0` berasal dari satu konstanta.
- `/api/v1/health/live` memeriksa proses aplikasi tanpa database.
- `/api/v1/health/ready` memeriksa database dengan timeout.
- Konfigurasi Telegram yang tidak lengkap menghentikan startup lebih awal.
- `SQL_ECHO=true` ditolak pada environment production.
- Log JSON dapat diaktifkan untuk collector platform.
- Image container tidak membawa `.env` dan berjalan sebagai non-root.
- Tidak ada migration atau seed baru.

## Verifikasi Lokal

```powershell
python scripts\verify_source.py
python -m uvicorn app.main:app --reload
```

```text
GET http://127.0.0.1:8000/api/v1/health/live
GET http://127.0.0.1:8000/api/v1/health/ready
```

## Verifikasi Container

```powershell
docker build -t palm-agronomy:0.8.0 .
docker run --rm -p 8000:8000 --env-file .env palm-agronomy:0.8.0
```

Jalankan migration sebagai release command terpisah sebelum mengalihkan traffic:

```text
python -m alembic upgrade head
```

Untuk production Telegram gunakan `TELEGRAM_MODE=webhook`, URL HTTPS publik, dan
`TELEGRAM_WEBHOOK_SECRET` yang acak. Jangan menjalankan polling dan webhook bersamaan.

## Batas Sprint

Sprint ini menyiapkan artifact deployment tetapi tidak memilih atau membuat akun pada
platform hosting. Pemilihan Render, Railway, Cloud Run, atau platform lain dilakukan setelah
biaya, region, sleep policy, secret management, dan dukungan release command dibandingkan.
