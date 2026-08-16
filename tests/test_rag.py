from pathlib import Path
from uuid import uuid4

import pytest

from app.repositories.knowledge import build_tsquery
from app.services.rag import (
    build_grounded_answer,
    chunk_document,
    format_telegram_rag_answer,
    parse_agronomy_question,
)

ROOT = Path(__file__).parents[1]


def test_parse_agronomy_question() -> None:
    assert parse_agronomy_question("/tanya kapan pemupukan sawit dilakukan?") == (
        "kapan pemupukan sawit dilakukan?"
    )


@pytest.mark.parametrize("command", ["/tanya", "/tanya x", "/help kapan pemupukan"])
def test_invalid_agronomy_question_is_rejected(command: str) -> None:
    with pytest.raises(ValueError):
        parse_agronomy_question(command)


def test_tsquery_removes_stopwords_and_uses_or_terms() -> None:
    assert build_tsquery("Bagaimana waktu pemupukan sawit yang baik?") == (
        "waktu | pemupukan | baik"
    )


def test_domain_words_do_not_make_every_oil_palm_chunk_relevant() -> None:
    assert build_tsquery("Kapan waktu pemupukan kelapa sawit?") == "waktu | pemupukan"


def test_chunk_document_is_bounded_and_overlapping() -> None:
    content = " ".join(f"kalimat-{index}." for index in range(400))
    chunks = chunk_document(content, max_chars=300, overlap_chars=40)

    assert len(chunks) > 2
    assert all(40 <= len(item) <= 300 for item in chunks)
    assert chunks[0][-20:] in chunks[1]


def test_insufficient_evidence_refuses_to_guess() -> None:
    answer = build_grounded_answer(
        "Berapa dosis pupuk untuk blok saya?",
        {"status": "insufficient_evidence", "chunks": []},
    )

    assert answer.status == "insufficient_evidence"
    assert "tidak akan menebak" in answer.answer
    assert answer.citations == []


def test_grounded_answer_contains_citation_and_safety_note() -> None:
    source_id = uuid4()
    chunk_id = uuid4()
    retrieval = {
        "status": "answered",
        "chunks": [
            {
                "chunk_id": chunk_id,
                "source_id": source_id,
                "section_title": "Pemupukan",
                "content": "Pemupukan dilakukan ketika tanah lembap dan tidak tergenang.",
                "score": 0.5,
                "title": "Pedoman Budidaya Sawit",
                "publisher": "Kementerian Pertanian",
                "source_url": "https://example.invalid/pedoman.pdf",
                "publication_year": 2020,
            }
        ],
    }

    answer = build_grounded_answer("Kapan pemupukan?", retrieval)
    telegram_text = format_telegram_rag_answer(answer)

    assert answer.status == "answered"
    assert answer.retrieved_chunk_ids == [chunk_id]
    assert "[S1]" in telegram_text
    assert "Kementerian Pertanian" in telegram_text
    assert "diverifikasi agronom/petugas" in telegram_text
    assert "https://" not in telegram_text
    assert ".pdf" not in telegram_text


def test_repository_filters_out_unverified_sources() -> None:
    repository_text = (ROOT / "app/repositories/knowledge.py").read_text(encoding="utf-8")

    assert "s.verification_status = 'verified'" in repository_text
    assert "pg_catalog.to_tsquery" in repository_text
