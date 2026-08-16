# Sprint 6 Handoff — Production Monitoring & Data Quality

## Definition of Done

- Versi aplikasi `0.7.1`.
- `/monitor [1-365]` membaca konteks blok aktif.
- Total dan rata-rata berasal dari `summarize_production`.
- Perubahan terbaru berasal dari `list_production_history`.
- Produktivitas dinormalisasi dengan luas blok PostGIS.
- Rata-rata berat/tandan hanya dihitung ketika jumlah tandan tersedia.
- Status data tidak menyamakan ringkasan deskriptif dengan prediksi.
- Seluruh tool call masuk audit log.
- Percakapan alami dirutekan ke handler yang sama dengan slash command.
- Pencatatan dari bahasa alami tetap membutuhkan konfirmasi manusia.
- Intent yang tidak dikenali tidak menjalankan tool apa pun.
- Tidak ada migration dan seed baru.

## Acceptance Test

```text
/context
/monitor 30
/monitor 7
/tanya bagaimana kondisi produksi blok saya?
Bagaimana monitoring produksi 30 hari terakhir?
Kapan waktu pemupukan kelapa sawit?
Catat panen 500 kg dan 30 tandan
```

Dengan data demo `1250 kg`, `85 tandan`, dan luas `1.2309 ha`, `/monitor 30`
harus menampilkan produktivitas `1.015,52 kg/ha`, berat rata-rata tandan
`14,71 kg`, dan status data `Terbatas`.

## Batas

Monitoring belum memasukkan cuaca, umur tanaman, rotasi panen, pemupukan, harga,
atau citra lapangan. Output adalah statistik deskriptif, bukan diagnosis atau prediksi.
