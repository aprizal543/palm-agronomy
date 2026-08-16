from app.services.production_monitoring import format_production_monitoring_answer

CONTEXT = {"status": "ready", "block_code": "A01", "area_ha": "1.2309"}


def test_monitoring_formats_productivity_and_bunch_average() -> None:
    summary = {
        "status": "ready",
        "days": 30,
        "record_count": 1,
        "total_ffb_kg": "1250.00",
        "total_bunches": 85,
        "average_ffb_kg_per_record": "1250.00",
    }

    answer = format_production_monitoring_answer(CONTEXT, summary, [])

    assert "Monitor 30 hari — Blok A01" in answer
    assert "Produktivitas tercatat: 1.015,52 kg/ha" in answer
    assert "Rata-rata berat/tandan: 14,71 kg" in answer
    assert "Status data: Terbatas" in answer
    assert "belum cukup untuk menentukan tren" in answer


def test_monitoring_reports_change_for_multiple_records() -> None:
    summary = {
        "status": "ready",
        "days": 30,
        "record_count": 2,
        "total_ffb_kg": "2250.00",
        "total_bunches": 150,
        "average_ffb_kg_per_record": "1125.00",
    }
    records = [
        {"ffb_weight_kg": "1250.00"},
        {"ffb_weight_kg": "1000.00"},
    ]

    answer = format_production_monitoring_answer(CONTEXT, summary, records)

    assert "Perubahan dua catatan terbaru: naik 25,00%" in answer
    assert "Status data: Deskriptif" in answer


def test_monitoring_handles_empty_period_without_claiming_a_trend() -> None:
    summary = {
        "status": "ready",
        "days": 7,
        "record_count": 0,
        "total_ffb_kg": "0.00",
        "total_bunches": 0,
        "average_ffb_kg_per_record": "0.00",
    }

    answer = format_production_monitoring_answer(CONTEXT, summary, [])

    assert "Status data: Belum tersedia" in answer
    assert "belum dapat dinilai" in answer
    assert "Rata-rata berat/tandan: tidak tersedia" in answer
