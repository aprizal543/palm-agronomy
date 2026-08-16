# Sprint 3 Handoff — Database Tools & Production Data

## Definition of Done

- Revision database berada di `0005_production_records (head)`.
- Verifikasi source, pytest, dan Ruff lulus.
- `/context` menampilkan farm/block aktif dan hak akses.
- `/produksi` hanya membuat draft dan meminta konfirmasi.
- Tombol **Simpan** membuat tepat satu production record.
- Tombol **Batalkan** tidak membuat production record.
- `/riwayat` dan `/ringkasan` hanya membaca blok aktif yang dapat diakses.
- Actor tanpa role owner/editor/validator ditolak sebelum write.
- Setiap tool call dan keputusan manusia tersimpan di audit log.

## Tabel Baru

| Tabel | Fungsi |
|---|---|
| `palm.production_records` | Catatan panen TBS terkonfirmasi per farm dan block |

## Tool Allow-list

| Tool | Sifat |
|---|---|
| `resolve_block_by_location` | Read spatial context dari PostGIS |
| `get_farm_block_context` | Read active farm/block dan access role |
| `record_production` | Write setelah human confirmation |
| `list_production_history` | Read riwayat blok aktif |
| `summarize_production` | Agregasi deterministic dari PostgreSQL |

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
0005_production_records (head)
```

Jalankan polling dan uji berurutan:

```text
/context
/produksi 1250 80
klik Simpan
/riwayat 5
/ringkasan 30
```

## Security Boundary

- Production write memerlukan conversation user, active confirmed block, dan write membership.
- Database trigger mengulang validasi block-farm, actor authorization, dan tanggal panen.
- Draft tidak sama dengan record; hanya callback pemilik draft yang dapat mengonfirmasi.
- Unique confirmation action menjaga idempotensi write.
- Agent tidak menerima connection, ORM session, atau arbitrary SQL tool.
