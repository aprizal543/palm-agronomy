import re
from decimal import Decimal, InvalidOperation
from typing import Any

_PRODUCTION_CONTEXT_PATTERNS = (
    r"\bproduksi\s+(?:terakhir|blok|saya)\b",
    r"\b(?:kondisi|ringkasan|analisis)\s+produksi\b",
    r"\b(?:hasil|data|catatan)\s+(?:panen|produksi)\s+(?:blok|saya)\b",
    r"\bproduktivitas\s+(?:blok|kebun|saya)\b",
    r"\bberapa\b.*\b(?:produksi|tbs|tandan)\b",
)


def is_production_context_question(question: str) -> bool:
    """Route block-specific operational questions away from document RAG."""
    normalized = re.sub(r"\s+", " ", question.casefold()).strip()
    return any(re.search(pattern, normalized) for pattern in _PRODUCTION_CONTEXT_PATTERNS)


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Nilai produksi tidak valid") from exc


def _format_id(value: Decimal, decimals: int) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def format_production_context_answer(
    context: dict[str, Any], records: list[dict[str, Any]]
) -> str:
    if context.get("status") != "ready":
        return "Belum ada blok aktif. Kirim Location Telegram terlebih dahulu."
    if not records:
        return f"Belum ada catatan produksi untuk Blok {context['block_code']}."

    latest = records[0]
    weight = _decimal(latest["ffb_weight_kg"])
    area = _decimal(context["area_ha"])
    if area <= 0:
        raise ValueError("Luas blok harus lebih besar dari nol")
    yield_per_ha = weight / area
    bunch_count = latest.get("bunch_count")
    bunch_text = str(bunch_count) if bunch_count is not None else "tidak dicatat"

    lines = [
        f"Analisis Blok {context['block_code']}:",
        "",
        f"Produksi terakhir: {_format_id(weight, 2)} kg",
        f"Jumlah tandan: {bunch_text}",
        f"Luas blok: {_format_id(area, 4)} ha",
        f"Estimasi hasil: {_format_id(yield_per_ha, 2)} kg/ha",
        f"Tanggal pencatatan: {latest['harvest_date']}",
    ]

    if len(records) == 1:
        note = (
            "Data baru berasal dari satu pencatatan sehingga belum cukup "
            "untuk menentukan tren produksi."
        )
    else:
        previous = _decimal(records[1]["ffb_weight_kg"])
        if previous > 0:
            change = ((weight - previous) / previous) * Decimal(100)
            direction = "naik" if change >= 0 else "turun"
            lines.extend(
                [
                    (
                        f"Perubahan dari catatan sebelumnya: {direction} "
                        f"{_format_id(abs(change), 2)}%"
                    ),
                ]
            )
        note = (
            "Perbandingan ini hanya berdasarkan catatan yang tersedia dan belum "
            "memperhitungkan umur tanaman, cuaca, rotasi panen, atau input agronomi."
        )

    lines.extend(["", "Catatan:", note])
    return "\n".join(lines)
