import re
from dataclasses import dataclass

from app.services.production_insight import is_production_context_question


@dataclass(frozen=True)
class ConversationRoute:
    intent: str
    command_text: str


_AGRONOMY_TERMS = {
    "sawit",
    "kelapa sawit",
    "pupuk",
    "pemupukan",
    "gulma",
    "hama",
    "penyakit",
    "tanah",
    "pelepah",
    "agronomi",
    "tbs",
}


def _period_days(text: str, default: int) -> int:
    match = re.search(r"\b(\d{1,3})\s*hari\b", text)
    return int(match.group(1)) if match else default


def _production_draft_route(text: str) -> ConversationRoute | None:
    if not re.search(r"\b(?:catat|input|rekam|simpan)\b", text):
        return None
    weight_match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(?:kg|kilogram)\b", text)
    if weight_match is None:
        return None
    bunch_match = re.search(r"\b(\d+)\s*tandan\b", text)
    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    bunches = bunch_match.group(1) if bunch_match else "-"
    command = f"/produksi {weight_match.group(1)} {bunches}"
    if date_match:
        command += f" {date_match.group(1)}"
    return ConversationRoute(intent="prepare_production", command_text=command)


def route_conversation(message_text: str) -> ConversationRoute | None:
    """Map supported Indonesian conversation to existing audited command handlers."""
    normalized = re.sub(r"\s+", " ", message_text.casefold()).strip()
    if not normalized or normalized.startswith("/"):
        return None

    production_draft = _production_draft_route(normalized)
    if production_draft is not None:
        return production_draft

    if re.search(r"\b(?:konteks|blok aktif)\b", normalized):
        return ConversationRoute(intent="get_context", command_text="/context")

    if re.search(r"\bmonitor(?:ing)?\b", normalized):
        days = _period_days(normalized, 30)
        return ConversationRoute(intent="production_monitoring", command_text=f"/monitor {days}")

    if re.search(r"\b(?:riwayat|catatan terakhir)\b", normalized):
        limit_match = re.search(r"\b(\d{1,2})\b", normalized)
        limit = int(limit_match.group(1)) if limit_match else 5
        return ConversationRoute(intent="production_history", command_text=f"/riwayat {limit}")

    if re.search(r"\bringkasan\b", normalized) and re.search(
        r"\b(?:produksi|panen|tbs)\b", normalized
    ):
        days = _period_days(normalized, 30)
        return ConversationRoute(intent="production_summary", command_text=f"/ringkasan {days}")

    if is_production_context_question(normalized):
        return ConversationRoute(intent="production_question", command_text=normalized)

    if any(term in normalized for term in _AGRONOMY_TERMS):
        return ConversationRoute(intent="agronomy_question", command_text=f"/tanya {normalized}")

    return None
