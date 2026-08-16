# Sprint 4 Handoff — Verified Agronomy RAG

## Definition of Done

- Revision database berada di `0006_rag_knowledge (head)`.
- Source menyimpan provenance, checksum, URL, dan verification status.
- Retrieval hanya membaca source `verified`.
- `/tanya` menampilkan evidence dan citation ringkas dari database tanpa URL/PDF preview.
- Sprint 5 v0.6.0 merutekan pertanyaan produksi berbasis blok ke konteks aktif dan
  `production_records`; pertanyaan agronomi umum tetap menggunakan RAG terverifikasi.
- Pertanyaan tanpa evidence menghasilkan `insufficient_evidence`, bukan tebakan.
- Tool call masuk `agent_audit_logs`; evidence masuk `rag_query_logs`.
- Ingestion umum selalu menghasilkan source `pending`.
- Source/chunk agronomy tidak digunakan untuk data aktual Farm/Block.

## Tabel Baru

| Tabel | Fungsi |
|---|---|
| `palm.knowledge_sources` | Provenance dan status verifikasi sumber |
| `palm.knowledge_chunks` | Chunk, full-text vector, dan slot embedding pgvector |
| `palm.rag_query_logs` | Evidence trace untuk evaluasi dan audit hallucination |

## Retrieval Saat Ini

- Active: PostgreSQL full-text search dengan konfigurasi `simple`.
- Ready but empty: `embedding extensions.vector(1536)`.
- Belum diklaim: semantic/hybrid retrieval dan generative answer.
- Jawaban Telegram bersifat extractive-grounded agar acceptance dapat diuji tanpa API key.

## Acceptance Test Windows

```powershell
python scripts\verify_source.py
python -m pytest
python -m ruff check app migrations scripts tests
python -m alembic upgrade head
python -m alembic current
python -m scripts.seed_rag_demo
```

Expected head:

```text
0006_rag_knowledge (head)
```

Jalankan polling dan uji:

```text
/help
/tanya kapan waktu pemupukan kelapa sawit?
/tanya bagaimana mengatur antena satelit di bulan?
```

## Security and Academic Integrity

- Tidak ada tool arbitrary SQL.
- Source `pending` dan `rejected` tidak dapat diretrieve.
- Citation berasal dari metadata database, bukan karangan model.
- Seed mencatat URL dokumen resmi untuk provenance/audit, tetapi URL tidak ditampilkan di
  Telegram. Isi knowledge menggunakan ringkasan/parafrasa terkurasi.
- Dosis/tindakan spesifik harus memakai kondisi blok dan verifikasi agronom.
- Corpus publik tidak boleh diklaim sebagai data internal SawitPRO.
