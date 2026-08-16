"""Ingest a local JSON agronomy document as pending human verification."""

import argparse
import asyncio
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, Field

from app.db.session import SessionLocal
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeSourceInput
from app.services.rag import chunk_document


class IngestPayload(BaseModel):
    source: KnowledgeSourceInput
    content: str = Field(min_length=40)


async def ingest(path: Path) -> None:
    payload = IngestPayload.model_validate_json(path.read_text(encoding="utf-8"))
    # Generic ingestion cannot self-verify. A curator must review it in the database.
    source_data = payload.source.model_copy(update={"verification_status": "pending"})
    chunks = chunk_document(payload.content)
    checksum = sha256(payload.content.encode("utf-8")).hexdigest()
    async with SessionLocal() as session:
        try:
            source_id, inserted_chunks = await KnowledgeRepository(session).ingest(
                source_data=source_data,
                checksum_sha256=checksum,
                chunks=chunks,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    print(
        f"Dokumen masuk sebagai pending: source_id={source_id}, chunks_baru={inserted_chunks}."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", type=Path)
    args = parser.parse_args()
    asyncio.run(ingest(args.json_path))


if __name__ == "__main__":
    main()
