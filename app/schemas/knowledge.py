from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class KnowledgeSourceInput(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    publisher: str = Field(min_length=2, max_length=200)
    source_type: Literal["guideline", "regulation", "manual", "article", "research"]
    source_url: HttpUrl
    publication_year: int | None = Field(default=None, ge=1900, le=2100)
    language: str = Field(default="id", min_length=2, max_length=10)
    version_label: str | None = Field(default=None, max_length=100)
    license_label: str | None = Field(default=None, max_length=150)
    origin_type: Literal["public_document", "user_supplied", "synthetic"]
    verification_status: Literal["pending", "verified", "rejected"] = "pending"
    verification_note: str | None = Field(default=None, max_length=500)


class KnowledgeChunkResult(BaseModel):
    chunk_id: UUID
    source_id: UUID
    section_title: str | None
    content: str
    score: float
    title: str
    publisher: str
    source_url: str
    publication_year: int | None


class RagCitation(BaseModel):
    label: str
    source_id: UUID
    title: str
    publisher: str
    source_url: str
    publication_year: int | None


class RagAnswer(BaseModel):
    status: Literal["answered", "insufficient_evidence"]
    question: str
    answer: str
    citations: list[RagCitation]
    retrieved_chunk_ids: list[UUID]
