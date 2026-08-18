# Sprint 8 Handoff — Railway Deployment dan Telegram Webhook

**Status:** Selesai  
**Tanggal verifikasi:** 17–18 Agustus 2026  
**Versi:** `0.9.0`  
**Repository:** `https://github.com/aprizal543/palm-agronomy`

## 1. Outcome

- Railway terhubung ke repository GitHub dan branch `main`.
- Build, deploy, network healthcheck, dan post-deploy berhasil.
- Service Railway berstatus **Active**.
- Endpoint health lokal mengembalikan `alive 0.9.0` dan `ready 0.9.0`.
- Telegram Bot merespons setelah deployment cloud.
- Production diarahkan menggunakan Telegram webhook HTTPS.

## 2. Commit Penting

| Commit | Keterangan |
|---|---|
| `c37a562` | Menambahkan Railway deployment dan Telegram webhook |
| `6ad539ca` | Memperbaiki ekspansi Railway `$PORT` melalui shell |

Selalu verifikasi commit hash penuh melalui `git log` karena dokumen ini memakai short hash yang terlihat saat deployment.

## 3. Perbaikan Deployment

Deployment pertama gagal pada Network Healthcheck karena Uvicorn menerima string literal `$PORT`. Start command diperbaiki agar dijalankan melalui shell:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "deploy": {
    "preDeployCommand": ["python -m alembic upgrade head"],
    "startCommand": "sh -c 'python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT'",
    "healthcheckPath": "/api/v1/health/ready",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

Jangan mengubah command tersebut kembali ke bentuk yang membuat `$PORT` dibaca literal.

## 4. Komponen Sprint 8

Komponen yang diperkenalkan atau diperbarui mencakup:

- konfigurasi environment production;
- version metadata `0.9.0`;
- Telegram webhook service;
- automatic webhook registration;
- script pengelolaan webhook;
- Railway config-as-code;
- Docker/deployment configuration;
- deployment and webhook tests;
- dokumentasi deployment.

Gunakan repository `main` untuk melihat daftar file final karena isi dapat berkembang setelah handoff ini.

## 5. Variable Production

Pastikan Railway Variables menyediakan kelompok konfigurasi berikut tanpa menyalin nilainya ke dokumentasi:

```text
APP_ENV
APP_NAME
API_V1_PREFIX
DATABASE_URL
MIGRATION_DATABASE_URL
DB_POOL_SIZE
DB_MAX_OVERFLOW
SQL_ECHO
LOG_LEVEL
JSON_LOGS
READINESS_TIMEOUT_S
TELEGRAM_ENABLED
TELEGRAM_MODE
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
TELEGRAM_WEBHOOK_AUTO_REGISTER
TELEGRAM_WEBHOOK_MAX_CONNECTIONS
TELEGRAM_REQUEST_TIMEOUT_S
AGENT_PROVIDER
```

`TELEGRAM_BOT_TOKEN`, database credentials, dan `TELEGRAM_WEBHOOK_SECRET` adalah secret.

## 6. Smoke Test Production

Gunakan domain Railway aktual:

```text
https://<railway-domain>/api/v1/health/live
https://<railway-domain>/api/v1/health/ready
```

Expected:

- HTTP sukses;
- status `alive` pada live endpoint;
- status `ready` pada ready endpoint;
- version `0.9.0`.

Uji Telegram:

```text
/context
Bagaimana kondisi produksi blok saya?
Kapan waktu pemupukan kelapa sawit?
```

Expected:

- konteks aktif tampil;
- analisis produksi membaca production record dan luas blok;
- pertanyaan agronomi membaca source terverifikasi;
- tidak ada URL/PDF preview pada citation;
- Railway Deploy Logs tidak menunjukkan error webhook atau database.

## 7. Aturan Operasional Telegram

- Production: `TELEGRAM_MODE=webhook`.
- Local development: polling diperbolehkan hanya ketika webhook production dinonaktifkan/dikelola dengan sengaja.
- Jangan menjalankan `python -m scripts.run_telegram_polling` ketika webhook production aktif.
- Gunakan script webhook management untuk pemeriksaan terkontrol.
- Jangan memanggil API Telegram menggunakan token yang ditempel ke screenshot atau chat.

## 8. Known Limitation Setelah Sprint 8

Deployment dan webhook berhasil, tetapi conversation router belum memahami seluruh paraphrase bahasa Indonesia.

Hasil verifikasi:

- “Bagaimana kondisi produksi blok saya?” berhasil.
- “Bagaimana produksi kebun blok saya?” dapat menghasilkan fallback.

Root cause: pola intent belum mencakup makna semantik yang sama. Ini menjadi kandidat utama Sprint 9 dan bukan alasan untuk mengubah deployment Sprint 8.

## 9. Checklist Sebelum Sprint Berikutnya

- [ ] `git status --short` bersih.
- [ ] Railway deployment terbaru Active.
- [ ] live dan ready healthcheck berhasil.
- [ ] webhook production aktif.
- [ ] polling lokal berhenti.
- [ ] smoke test Telegram berhasil.
- [ ] tidak ada secret di commit/log/screenshot.
- [ ] baseline test suite lulus.
- [ ] Sprint 9 memiliki acceptance criteria sebelum coding.
