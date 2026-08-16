import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk, KnowledgeSource, RagQueryLog
from app.schemas.knowledge import KnowledgeSourceInput
from app.services.rag import content_hash

STOPWORDS_ID = {
    "ada",
    "agar",
    "apa",
    "apakah",
    "atau",
    "bagaimana",
    "berapa",
    "dan",
    "dari",
    "dengan",
    "di",
    "ini",
    "itu",
    "kapan",
    "ke",
    "kelapa",
    "kenapa",
    "mengapa",
    "pada",
    "saya",
    "sawit",
    "sebaiknya",
    "untuk",
    "yang",
    "tanaman",
}


def build_tsquery(question: str) -> str:
    tokens: list[str] = []
    for token in re.findall(r"[a-z0-9]+", question.lower()):
        if len(token) < 3 or token in STOPWORDS_ID or token in tokens:
            continue
        tokens.append(token)
        if len(tokens) == 12:
            break
    return " | ".join(tokens)


class KnowledgeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ingest(
        self,
        *,
        source_data: KnowledgeSourceInput,
        checksum_sha256: str,
        chunks: list[str],
    ) -> tuple[UUID, int]:
        existing = await self.session.scalar(
            select(KnowledgeSource).where(
                KnowledgeSource.checksum_sha256 == checksum_sha256
            )
        )
        if existing is not None:
            return existing.id, 0
        source = KnowledgeSource(
            title=source_data.title,
            publisher=source_data.publisher,
            source_type=source_data.source_type,
            source_url=str(source_data.source_url),
            publication_year=source_data.publication_year,
            language=source_data.language,
            version_label=source_data.version_label,
            license_label=source_data.license_label,
            checksum_sha256=checksum_sha256,
            origin_type=source_data.origin_type,
            verification_status=source_data.verification_status,
            verification_note=source_data.verification_note,
            verified_at=(
                datetime.now(UTC)
                if source_data.verification_status == "verified"
                else None
            ),
        )
        self.session.add(source)
        await self.session.flush()
        for index, chunk in enumerate(chunks):
            self.session.add(
                KnowledgeChunk(
                    source_id=source.id,
                    chunk_index=index,
                    section_title=None,
                    content=chunk,
                    content_hash=content_hash(chunk),
                    token_count=len(chunk.split()),
                )
            )
        await self.session.flush()
        return source.id, len(chunks)

    async def search(
        self,
        *,
        question: str,
        top_k: int,
        trace_id: UUID,
        channel: str,
        update_id: int | None = None,
        chat_id: int | None = None,
        telegram_user_id: int | None = None,
    ) -> dict[str, Any]:
        ts_query = build_tsquery(question)
        rows: list[dict[str, Any]] = []
        if ts_query:
            result = await self.session.execute(
                text(
                    """
                    select
                      c.id as chunk_id,
                      c.source_id,
                      c.section_title,
                      c.content,
                      pg_catalog.ts_rank_cd(
                        c.search_vector,
                        pg_catalog.to_tsquery('simple', :ts_query)
                      )::double precision as score,
                      s.title,
                      s.publisher,
                      s.source_url,
                      s.publication_year
                    from palm.knowledge_chunks c
                    join palm.knowledge_sources s on s.id = c.source_id
                    where s.verification_status = 'verified'
                      and c.search_vector @@ pg_catalog.to_tsquery('simple', :ts_query)
                    order by score desc, c.chunk_index asc
                    limit :top_k
                    """
                ),
                {"ts_query": ts_query, "top_k": top_k},
            )
            rows = [dict(item) for item in result.mappings()]

        status = "answered" if rows else "insufficient_evidence"
        chunk_ids = [item["chunk_id"] for item in rows]
        scores = [float(item["score"]) for item in rows]
        self.session.add(
            RagQueryLog(
                trace_id=trace_id,
                update_id=update_id,
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                channel=channel,
                query_text=question,
                retrieval_status=status,
                retrieved_chunk_ids=chunk_ids,
                retrieval_scores=scores,
                top_k=top_k,
            )
        )
        await self.session.flush()
        return {
            "status": status,
            "question": question,
            "chunks": rows,
            "retrieved_chunk_ids": [str(item) for item in chunk_ids],
        }
