"""Idempotent verified public-document seed for Sprint 4 RAG acceptance tests."""

import asyncio
from hashlib import sha256

from app.db.session import SessionLocal
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeSourceInput

SOURCE = KnowledgeSourceInput(
    title="Budidaya Kelapa Sawit & Varietas Kelapa Sawit",
    publisher="Kementerian Pertanian Republik Indonesia",
    source_type="manual",
    source_url=(
        "https://repository.pertanian.go.id/bitstreams/"
        "5314fefe-5bbe-4ad8-8e6a-4934d6d74f8d/download"
    ),
    publication_year=2020,
    language="id",
    origin_type="public_document",
    verification_status="verified",
    verification_note="Dokumen resmi Kementerian Pertanian; ringkasan demo dikurasi.",
)

# Paraphrased for the prototype. Avoid universal prescriptions or context-free dosage advice.
CHUNKS = [
    (
        "Pemupukan kelapa sawit sebaiknya dilakukan ketika tanah lembap pada musim hujan, "
        "namun bukan saat lahan tergenang. Jenis dan dosis pupuk tidak boleh ditentukan hanya "
        "dari jawaban umum; umur tanaman, kondisi tanah, analisis daun, dan rekomendasi agronom "
        "perlu dipertimbangkan."
    ),
    (
        "Gulma di sekitar tanaman kelapa sawit dapat bersaing mendapatkan air, unsur hara, "
        "cahaya, dan ruang tumbuh sehingga berpotensi mengganggu pertumbuhan serta produksi. "
        "Metode pengendalian perlu dipilih sesuai kondisi kebun dan prinsip keselamatan kerja."
    ),
    (
        "Pemeliharaan kelapa sawit mencakup pemangkasan pelepah yang tidak produktif atau "
        "menumpuk, pengamatan hama dan penyakit, serta panen yang teratur. Temuan lapangan "
        "harus dicatat dan diverifikasi sebelum tindakan korektif dilakukan."
    ),
]


async def main() -> None:
    checksum = sha256("\n\n".join(CHUNKS).encode("utf-8")).hexdigest()
    async with SessionLocal() as session:
        try:
            source_id, inserted_chunks = await KnowledgeRepository(session).ingest(
                source_data=SOURCE,
                checksum_sha256=checksum,
                chunks=CHUNKS,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    print(
        f"RAG demo source siap: source_id={source_id}, chunks_baru={inserted_chunks}."
    )


if __name__ == "__main__":
    asyncio.run(main())
