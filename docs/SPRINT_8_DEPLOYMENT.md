# Sprint 8 — Railway Deployment & Telegram Webhook

## Definition of Done

- Versi aplikasi `0.9.0`.
- Railway menjalankan migration sebelum setiap deployment.
- Uvicorn bind ke `0.0.0.0:$PORT`.
- Health check menggunakan `/api/v1/health/ready`.
- Telegram menggunakan webhook HTTPS dengan secret header.
- Webhook dapat didaftarkan otomatis setelah public domain tersedia.
- Token bot, database password, dan webhook secret hanya berada di Railway Variables.
- Polling lokal tidak berjalan bersamaan dengan webhook production.
- Deployment dapat restart otomatis ketika proses gagal.

## Mengapa Railway

Railway dapat membaca Dockerfile dari repository, menyediakan public domain, menjalankan
pre-deploy migration, memeriksa readiness endpoint, dan mengatur restart policy melalui
`railway.json`. Supabase tetap menjadi database utama; Railway hanya menjalankan API.

## Tahap 1 — Deployment Awal

1. Push source Sprint 8 ke GitHub.
2. Pada Railway pilih **New Project → Deploy from GitHub Repo**.
3. Pilih repository `aprizal543/palm-agronomy`.
4. Isi Railway Variables berikut. Jangan menyalin nilai secret ke dokumentasi atau screenshot.

```env
APP_ENV=production
DATABASE_URL=postgresql+asyncpg://...
MIGRATION_DATABASE_URL=postgresql+asyncpg://...
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
SQL_ECHO=false
LOG_LEVEL=INFO
JSON_LOGS=true
READINESS_TIMEOUT_S=10
TELEGRAM_ENABLED=true
TELEGRAM_MODE=webhook
TELEGRAM_BOT_TOKEN=...
TELEGRAM_WEBHOOK_SECRET=...
TELEGRAM_WEBHOOK_AUTO_REGISTER=false
TELEGRAM_WEBHOOK_MAX_CONNECTIONS=40
TELEGRAM_REQUEST_TIMEOUT_S=15
```

Secret yang kompatibel dengan Telegram dapat dibuat secara lokal:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Simpan hasilnya langsung sebagai Railway Variable `TELEGRAM_WEBHOOK_SECRET`.

## Tahap 2 — Public Domain dan Webhook

1. Buka service Railway → **Settings → Networking → Generate Domain**.
2. Pastikan URL berikut memberikan status `200`:

```text
https://<domain-railway>/api/v1/health/live
https://<domain-railway>/api/v1/health/ready
```

3. Railway menyediakan `RAILWAY_PUBLIC_DOMAIN`. Ubah:

```env
TELEGRAM_WEBHOOK_AUTO_REGISTER=true
```

4. Redeploy. Startup akan mendaftarkan URL berikut tanpa mencetak token/secret:

```text
https://<domain-railway>/api/v1/telegram/webhook
```

Jika `RAILWAY_PUBLIC_DOMAIN` tidak tersedia, isi origin secara eksplisit:

```env
PUBLIC_BASE_URL=https://<domain-railway>
```

`PUBLIC_BASE_URL` tidak boleh mengandung path, query, credential, atau memakai HTTP.

## Verifikasi

Periksa log Railway. Harus terdapat event:

```text
telegram_webhook_registered host=<domain> path=/api/v1/telegram/webhook
```

Dengan Railway CLI dan variables service yang aktif, status dapat diperiksa tanpa menaruh
token pada command line:

```powershell
railway run python -m scripts.manage_telegram_webhook info
```

Kemudian kirim ke bot:

```text
/context
Bagaimana kondisi produksi blok saya?
Kapan waktu pemupukan kelapa sawit?
```

Matikan seluruh proses `scripts.run_telegram_polling` lokal. Menjalankan polling akan
menghapus webhook production karena Telegram hanya mengizinkan salah satu transport.

## Rollback Aman

1. Pilih deployment terakhir yang sehat pada Railway dan lakukan rollback/redeploy.
2. Jangan rollback migration dengan menghapus tabel production.
3. Jika webhook harus dihentikan sementara:

```powershell
railway run python -m scripts.manage_telegram_webhook delete
```

Perintah tersebut mempertahankan pending updates kecuali opsi
`--drop-pending-updates` diberikan secara eksplisit.

## Batas Sprint

Sprint 8 tidak menambahkan tabel, seed, weather, satellite, ML, vision, voice, atau WhatsApp.
Fokusnya hanya membuat API dan Telegram bot dapat berjalan melalui webhook cloud.
