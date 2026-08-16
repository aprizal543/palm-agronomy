# Sprint 2 Handoff — Telegram Adapter & AI Agent Orchestration

## Definition of Done

- Revision database berada di `0004_telegram_agent (head)`.
- `python scripts/verify_source.py` lulus.
- `python -m pytest` lulus.
- `python -m ruff check app migrations scripts tests` lulus.
- Bot menjawab `/start` dan `/help`.
- Share Location menghasilkan salah satu dari `matched`, `confirmation_required`,
  `ambiguous`, atau `not_found` berdasarkan PostGIS.
- Tombol konfirmasi hanya dapat digunakan user pemilik pending action dan kedaluwarsa
  setelah 15 menit.
- Mengirim ulang Telegram `update_id` yang sama tidak menghasilkan efek kedua.
- `palm.agent_audit_logs` menyimpan intent, tool call, dan human confirmation.

## Tabel Baru

| Tabel | Fungsi |
|---|---|
| `palm.telegram_updates` | Ledger idempotency dan status pemrosesan update |
| `palm.conversations` | State serta farm/block context per chat |
| `palm.pending_actions` | Human confirmation dengan expiry |
| `palm.agent_audit_logs` | Audit trace untuk intent/tool/result |

## Alur Lokasi

1. Telegram Update divalidasi oleh schema Pydantic.
2. `update_id` diklaim dan di-commit sebelum external side effect.
3. User dan conversation di-upsert tanpa mengganti role yang telah ada.
4. Tool allow-list meneruskan longitude, latitude, dan accuracy ke PostGIS.
5. Hasil pasti langsung mengatur active block; hasil boundary/ambigu meminta konfirmasi.
6. Intent, tool call, latency, output, dan keputusan manusia masuk audit log.

## Acceptance Test Windows

```powershell
python scripts\verify_source.py
python -m pytest
python -m ruff check app migrations scripts tests
python -m alembic upgrade head
python -m alembic current
```

Expected head:

```text
0004_telegram_agent (head)
```

Untuk pengujian lokal, isi secret hanya di `.env`, set `TELEGRAM_MODE=polling`, lalu:

```powershell
python -m scripts.run_telegram_polling
```

## Security Boundary

- Bot token dan webhook secret hanya berasal dari environment.
- Webhook memakai constant-time comparison terhadap secret header Telegram.
- Agent hanya dapat mengeksekusi tool yang di-register; nama tool lain ditolak.
- Geometri, area, coverage, overlap, dan point lookup tetap diputuskan PostGIS.
- Tidak ada arbitrary SQL tool dan tidak ada LLM credential pada Sprint 2 foundation.
