from decimal import Decimal, InvalidOperation
from typing import Any


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Nilai monitoring produksi tidak valid") from exc


def _format_id(value: Decimal, decimals: int = 2) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def format_production_monitoring_answer(
    context: dict[str, Any],
    summary: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    if context.get("status") != "ready":
        return "Belum ada blok aktif. Kirim Location Telegram terlebih dahulu."
    if summary.get("status") != "ready":
        return "Ringkasan produksi belum dapat diakses untuk blok aktif."

    record_count = int(summary.get("record_count", 0))
    area = _decimal(context["area_ha"])
    if area <= 0:
        raise ValueError("Luas blok harus lebih besar dari nol")
    total_weight = _decimal(summary.get("total_ffb_kg", 0))
    total_bunches = int(summary.get("total_bunches", 0) or 0)
    average_per_record = _decimal(summary.get("average_ffb_kg_per_record", 0))
    productivity = total_weight / area

    if total_bunches > 0:
        bunch_average = f"{_format_id(total_weight / total_bunches)} kg"
    else:
        bunch_average = "tidak tersedia"

    lines = [
        f"Monitor {summary['days']} hari — Blok {context['block_code']}:",
        "",
        f"Jumlah catatan: {record_count}",
        f"Total TBS: {_format_id(total_weight)} kg",
        f"Total tandan: {total_bunches}",
        f"Produktivitas tercatat: {_format_id(productivity)} kg/ha",
        f"Rata-rata/catatan: {_format_id(average_per_record)} kg",
        f"Rata-rata berat/tandan: {bunch_average}",
    ]

    if record_count == 0:
        status = "Belum tersedia"
        note = "Belum ada data pada periode ini sehingga kondisi produksi belum dapat dinilai."
    elif record_count == 1:
        status = "Terbatas"
        note = "Satu catatan belum cukup untuk menentukan tren produksi."
    else:
        status = "Deskriptif"
        note = (
            "Ringkasan ini menggambarkan catatan yang tersedia dan bukan prediksi produksi."
        )
        if len(records) >= 2:
            latest = _decimal(records[0]["ffb_weight_kg"])
            previous = _decimal(records[1]["ffb_weight_kg"])
            if previous > 0:
                change = ((latest - previous) / previous) * Decimal(100)
                direction = "naik" if change >= 0 else "turun"
                lines.append(
                    f"Perubahan dua catatan terbaru: {direction} "
                    f"{_format_id(abs(change))}%"
                )

    lines.extend(["", f"Status data: {status}", note])
    return "\n".join(lines)
