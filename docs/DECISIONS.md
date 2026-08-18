# PalmAgronomy AI Agent — Architecture Decision Log

**Status diperbarui:** 18 Agustus 2026

Dokumen ini mencatat keputusan yang sudah dibuat. Perubahan terhadap keputusan berstatus **Diterima** harus mempunyai alasan teknis, dampak, test plan, dan migration/rollback plan jika relevan.

## ADR-001 — PostgreSQL/PostGIS sebagai Spatial Backbone

**Status:** Diterima  
**Keputusan:** Farm dan Block beserta operasi spasial disimpan dan divalidasi melalui PostgreSQL/PostGIS di Supabase.  
**Alasan:** penentuan konteks blok harus deterministik, dapat diaudit, dan tidak diserahkan pada tebakan AI.

## ADR-002 — Supabase Free sebagai Database Utama

**Status:** Diterima  
**Keputusan:** menggunakan Supabase PostgreSQL sebagai database managed untuk prototype.  
**Konsekuensi:** koneksi async aplikasi menggunakan `asyncpg`; migration tetap dikelola oleh Alembic.

## ADR-003 — Telegram sebagai Kanal Pertama

**Status:** Diterima  
**Keputusan:** Telegram adalah UI percakapan utama pada fase prototype.  
**Alasan:** implementasi cepat, mendukung location dan inline button, serta cocok untuk validasi alur lapangan.

## ADR-004 — Human Confirmation untuk Operasi Write

**Status:** Diterima  
**Keputusan:** pencatatan produksi menggunakan draft/pending action dan tombol Simpan/Batalkan.  
**Alasan:** mencegah data operasional tersimpan akibat salah parsing atau salah tekan.

## ADR-005 — Verified Evidence untuk Jawaban Agronomi

**Status:** Diterima  
**Keputusan:** retrieval agronomi hanya membaca source terverifikasi. Evidence tidak cukup menghasilkan respons aman, bukan jawaban spekulatif.  
**Konsekuensi:** provenance, checksum, status verifikasi, audit tool, dan query log harus dipertahankan.

## ADR-006 — Pisahkan Knowledge dan Data Operasional

**Status:** Diterima  
**Keputusan:** knowledge source/chunk digunakan untuk pengetahuan agronomi umum. Kondisi aktual Farm, Block, produksi, dan aktivitas dibaca dari tabel operasional.  
**Alasan:** mencegah RAG menyajikan data kebun yang stale atau tertukar.

## ADR-007 — Citation Ringkas di Telegram

**Status:** Diterima  
**Keputusan:** jawaban Telegram menampilkan judul/publisher/tahun sumber, tetapi tidak menampilkan URL langsung atau preview PDF. Provenance lengkap tetap disimpan internal.  
**Alasan:** menjaga jawaban ringkas dan menghindari preview file yang mengganggu antarmuka.

## ADR-008 — Router Hybrid, Bukan Chatbot Bebas

**Status:** Diterima sebagai arah Sprint 9  
**Keputusan:** intent berisiko dan pemanggilan tool tetap deterministik. Semantic/LLM classifier hanya membantu memahami variasi bahasa dan harus menghasilkan output terstruktur dengan confidence.  
**Alasan:** fleksibilitas bahasa diperlukan, tetapi authorization, validasi data, dan konfirmasi tidak boleh bergantung pada generasi bebas LLM.

## ADR-009 — Railway sebagai Runtime Production Prototype

**Status:** Diterima  
**Keputusan:** API dideploy dari GitHub branch `main` ke Railway.  
**Konfigurasi:** Docker/build, Alembic pre-deploy, healthcheck readiness, restart policy, dan `$PORT` runtime.

## ADR-010 — Webhook untuk Telegram Production

**Status:** Diterima  
**Keputusan:** production menggunakan Telegram webhook HTTPS; long polling hanya untuk development lokal.  
**Konsekuensi:** proses polling lokal harus dihentikan saat webhook production aktif.

## ADR-011 — Secrets Tidak Masuk Repository

**Status:** Diterima  
**Keputusan:** token, password, database URL, dan webhook secret hanya berada di `.env` lokal atau Railway Variables. `.env.example` hanya berisi nama variable dan nilai contoh aman.

## ADR-012 — Software-First Scope

**Status:** Diterima  
**Keputusan:** PalmAgronomy tetap berupa sistem software agronomi dengan Telegram/WhatsApp sebagai kanal. IoT tidak menjadi kebutuhan inti.  
**Alasan:** menjaga kesesuaian dengan konsep awal dan ruang lingkup prototype akademik.

## Template Keputusan Baru

```markdown
## ADR-XXX — Judul

**Status:** Proposed | Accepted | Superseded | Rejected
**Konteks:** masalah yang perlu diselesaikan.
**Keputusan:** pilihan yang diambil.
**Alasan:** alasan teknis dan produk.
**Konsekuensi:** dampak positif, trade-off, risiko.
**Validasi:** tests, metric, atau acceptance criteria.
**Rollback:** cara kembali jika keputusan gagal.
```
