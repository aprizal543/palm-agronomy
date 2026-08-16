from app.services.production_insight import (
    format_production_context_answer,
    is_production_context_question,
)


def test_block_production_question_is_routed_to_operational_data() -> None:
    assert is_production_context_question("bagaimana kondisi produksi blok saya?")
    assert is_production_context_question("berapa produksi terakhir blok saya?")


def test_general_agronomy_question_remains_in_rag() -> None:
    assert not is_production_context_question("kapan waktu pemupukan kelapa sawit?")
    assert not is_production_context_question("apakah gulma memengaruhi produksi kelapa sawit?")
    assert not is_production_context_question("apa pupuk yang sesuai untuk blok saya?")


def test_single_record_production_answer_has_context_and_insufficient_trend_note() -> None:
    context = {
        "status": "ready",
        "block_code": "A01",
        "area_ha": "1.2309",
    }
    records = [
        {
            "harvest_date": "2026-08-16",
            "ffb_weight_kg": "1250.00",
            "bunch_count": 85,
        }
    ]

    answer = format_production_context_answer(context, records)

    assert "Analisis Blok A01" in answer
    assert "Produksi terakhir: 1.250,00 kg" in answer
    assert "Jumlah tandan: 85" in answer
    assert "Luas blok: 1,2309 ha" in answer
    assert "Estimasi hasil: 1.015,52 kg/ha" in answer
    assert "belum cukup untuk menentukan tren produksi" in answer
