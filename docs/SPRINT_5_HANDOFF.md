# Sprint 5 Handoff — Contextual Production Analysis

## Definition of Done

- Versi aplikasi `0.6.0`.
- `/tanya bagaimana kondisi produksi blok saya?` membaca blok aktif.
- Data produksi berasal dari tool allow-list `list_production_history`.
- Luas blok berasal dari konteks PostGIS, bukan input pengguna.
- Jawaban menghitung kg/ha menggunakan `produksi_terakhir / area_ha`.
- Satu catatan tidak dianggap cukup untuk menyimpulkan tren.
- Pertanyaan pemupukan/gulma tetap diarahkan ke RAG terverifikasi.
- Tool context dan history tetap dicatat pada audit log.
- Tidak ada migration dan tidak ada seed baru.

## Acceptance Test Telegram

```text
/context
/tanya bagaimana kondisi produksi blok saya?
/tanya kapan waktu pemupukan kelapa sawit?
```

Dengan fixture Blok A01 seluas `1.2309 ha` dan produksi terakhir `1250 kg`, jawaban
pertanyaan produksi harus memuat `1.015,52 kg/ha`. Pertanyaan pemupukan harus tetap
menampilkan evidence dan citation knowledge tanpa URL/PDF preview.

## Batas Analisis

Hasil kg/ha adalah normalisasi satu catatan terhadap luas blok, bukan prediksi hasil panen
bulanan atau tahunan. Analisis belum memasukkan umur tanaman, rotasi panen, curah hujan,
pupuk, kondisi tanah, atau citra lapangan.
