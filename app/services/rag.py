import re
from hashlib import sha256
from typing import Any

from app.schemas.knowledge import RagAnswer, RagCitation


def parse_agronomy_question(command_text: str) -> str:
    parts = command_text.strip().split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() not in {"/tanya", "/ask"}:
        raise ValueError("Format: /tanya <pertanyaan agronomi>")
    question = re.sub(r"\s+", " ", parts[1]).strip()
    if len(question) < 5 or len(question) > 500:
        raise ValueError("Pertanyaan harus terdiri dari 5-500 karakter")
    return question


def chunk_document(text: str, max_chars: int = 900, overlap_chars: int = 120) -> list[str]:
    if max_chars < 200 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Konfigurasi chunk tidak valid")
    normalized = re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n")).strip()
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        if end < len(normalized):
            minimum_break = start + int(max_chars * 0.6)
            candidates = [
                normalized.rfind("\n\n", minimum_break, end),
                normalized.rfind(". ", minimum_break, end),
                normalized.rfind(" ", minimum_break, end),
            ]
            boundary = max(candidates)
            if boundary > start:
                end = boundary + (1 if normalized[boundary] == "." else 0)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(end - overlap_chars, start + 1)
    return chunks


def content_hash(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def build_grounded_answer(question: str, retrieval: dict[str, Any]) -> RagAnswer:
    chunks = retrieval.get("chunks", [])
    if not chunks:
        return RagAnswer(
            status="insufficient_evidence",
            question=question,
            answer=(
                "Saya belum menemukan bukti yang cukup dari sumber agronomi terverifikasi. "
                "Saya tidak akan menebak jawaban. Coba gunakan istilah yang lebih spesifik atau "
                "minta petugas menambahkan sumber yang relevan."
            ),
            citations=[],
            retrieved_chunk_ids=[],
        )

    citations: list[RagCitation] = []
    source_labels: dict[str, str] = {}
    evidence_lines: list[str] = []
    for item in chunks[:3]:
        source_key = str(item["source_id"])
        label = source_labels.get(source_key)
        if label is None:
            label = f"S{len(source_labels) + 1}"
            source_labels[source_key] = label
            citations.append(
                RagCitation(
                    label=label,
                    source_id=item["source_id"],
                    title=item["title"],
                    publisher=item["publisher"],
                    source_url=item["source_url"],
                    publication_year=item["publication_year"],
                )
            )
        excerpt = re.sub(r"\s+", " ", item["content"]).strip()[:750]
        evidence_lines.append(f"[{label}] {excerpt}")

    answer = "Berdasarkan sumber terverifikasi:\n\n" + "\n\n".join(evidence_lines)
    answer += (
        "\n\nCatatan: Informasi ini bersifat umum. Keputusan dosis atau tindakan lapangan "
        "harus disesuaikan dengan kondisi blok dan diverifikasi agronom/petugas."
    )
    return RagAnswer(
        status="answered",
        question=question,
        answer=answer,
        citations=citations,
        retrieved_chunk_ids=[item["chunk_id"] for item in chunks],
    )


def format_telegram_rag_answer(answer: RagAnswer) -> str:
    if answer.status == "insufficient_evidence":
        return answer.answer
    source_lines = []
    for citation in answer.citations:
        year = f" ({citation.publication_year})" if citation.publication_year else ""
        source_lines.append(f"[{citation.label}] {citation.title} — {citation.publisher}{year}")
    return f"{answer.answer}\n\nSumber:\n" + "\n".join(source_lines)
