# PalmAgronomy AI Agent — Roadmap

**Status diperbarui:** 18 Agustus 2026  
**Versi production:** `0.9.0`

## 1. Status Sprint

| Sprint | Fokus | Status | Hasil utama |
|---|---|---|---|
| 1 | Farm, Block, PostGIS | Selesai | Spatial backbone, membership, validasi dan lookup blok |
| 2 | Telegram Agent | Selesai | Profil Telegram, conversation context, command dasar |
| 3 | Production records | Selesai | Draft, konfirmasi Simpan/Batalkan, riwayat dan ringkasan |
| 4 | Verified agronomy RAG | Selesai | Source/chunk terverifikasi, citation, audit, insufficient evidence |
| 5 | Contextual production insight | Selesai | Analisis produksi berdasarkan blok aktif dan data aktual |
| 6 | Conversational monitoring | Selesai | Pertanyaan produksi tanpa command untuk pola yang dikenali |
| 7 | Deployment readiness | Selesai | Healthcheck, observability, Docker/deployment readiness, versi `0.8.0` |
| 8 | Railway + Telegram webhook | Selesai | Deployment cloud, webhook HTTPS, versi `0.9.0` |

Status **Selesai** berarti fitur inti dan pengujian milestone sudah berhasil. Perbaikan kualitas dapat tetap dilakukan tanpa membuka ulang seluruh sprint.

## 2. Sprint 9 yang Direkomendasikan

### Natural-Language Intent Routing dengan Guardrail

Tujuan: pengguna dapat memakai variasi bahasa Indonesia yang alami tanpa menghafal kalimat atau command tertentu.

Contoh kalimat yang harus mengarah ke intent yang sama:

- Bagaimana kondisi produksi blok saya?
- Bagaimana produksi kebun saya?
- Produktivitas A01 bagaimana?
- Berapa hasil panen terakhir?
- Tampilkan performa blok aktif.

Ruang lingkup:

1. text normalization;
2. synonym dan phrase mapping;
3. intent taxonomy yang eksplisit;
4. semantic/LLM fallback dengan structured output;
5. confidence threshold;
6. clarification untuk input ambigu;
7. deterministic tool authorization;
8. audit hasil routing;
9. regression tests untuk variasi bahasa dan typo umum.

Acceptance criteria:

- sekurangnya 30 paraphrase produksi diuji;
- variasi kapitalisasi dan typo ringan tetap dikenali;
- pertanyaan di luar domain ditolak dengan sopan;
- intent ambigu meminta klarifikasi, bukan menebak;
- write operation tetap memerlukan konfirmasi;
- user tidak dapat mengakses Farm/Block tanpa hak;
- latency dan error fallback tercatat;
- seluruh test lama tetap lulus.

Yang tidak termasuk Sprint 9:

- chatbot pengetahuan umum tanpa batas;
- LLM yang langsung menulis database;
- rekomendasi dosis agronomi tanpa evidence;
- perubahan skema Farm/Block yang tidak diperlukan.

## 3. Kandidat Sprint Setelah Sprint 9

Urutan berikut adalah **proposal** dan belum dikunci. Validasi ulang terhadap dokumen konsep awal serta kebutuhan pengguna sebelum implementasi.

| Prioritas | Kandidat | Tujuan |
|---|---|---|
| 1 | Conversational onboarding | Membuat/memutakhirkan profil, memilih kebun dan blok secara terpandu |
| 2 | Agronomy activity records | Mencatat pemupukan, penyiangan, pruning, hama/penyakit, dan observasi |
| 3 | Weather integration | Menggunakan data cuaca untuk konteks operasional, bukan sebagai satu-satunya dasar keputusan |
| 4 | Map/GIS workflow | Import/validasi geometri dan tampilan peta yang lebih mudah digunakan |
| 5 | Production trend & anomaly | Analisis multi-periode setelah data historis mencukupi |
| 6 | Satellite/NDVI | Monitoring vegetasi dengan data spasial dan temporal yang tervalidasi |
| 7 | Optional vision | Analisis gambar lapangan jika dataset dan use case telah dikunci |
| 8 | Voice/WhatsApp | Kanal tambahan setelah Telegram stabil |
| 9 | Evaluation & UAT | Evaluasi akademik, usability, reliability, dan dokumentasi hasil |

## 4. Quality Gates Setiap Sprint

Sebuah sprint tidak dinyatakan selesai sebelum:

- acceptance criteria terpenuhi;
- unit/integration/contract tests lulus;
- migration aman dan dapat diulang jika ada perubahan schema;
- tidak ada secret di repository;
- dokumentasi dan `.env.example` diperbarui;
- deployment healthcheck berhasil;
- smoke test Telegram berhasil;
- rollback atau recovery path dipahami;
- perubahan dicatat pada handoff.

## 5. Risiko yang Harus Dijaga

| Risiko | Guardrail |
|---|---|
| Intent salah | Confidence threshold dan clarification |
| Write tidak disengaja | Pending action dan human confirmation |
| Kebocoran data lintas kebun | Membership/access check pada setiap tool |
| Halusinasi agronomi | Verified evidence atau `insufficient_evidence` |
| Konflik webhook/polling | Hanya satu mode Telegram aktif |
| Secret ter-commit | `.gitignore`, source verification, secret scan |
| Deployment gagal | Healthcheck, logs, restart policy, rollback commit |
