from app.services.conversation_router import route_conversation


def test_monitoring_natural_language_maps_to_monitor_command() -> None:
    route = route_conversation("Bagaimana monitoring produksi 30 hari terakhir?")

    assert route is not None
    assert route.intent == "production_monitoring"
    assert route.command_text == "/monitor 30"


def test_production_question_maps_to_block_data() -> None:
    route = route_conversation("Bagaimana kondisi produksi blok saya?")

    assert route is not None
    assert route.intent == "production_question"


def test_agronomy_question_maps_to_verified_rag() -> None:
    route = route_conversation("Kapan waktu pemupukan kelapa sawit?")

    assert route is not None
    assert route.intent == "agronomy_question"
    assert route.command_text.startswith("/tanya ")


def test_natural_production_write_still_uses_confirmation_draft() -> None:
    route = route_conversation("Catat panen 500 kg dan 30 tandan pada 2026-08-16")

    assert route is not None
    assert route.intent == "prepare_production"
    assert route.command_text == "/produksi 500 30 2026-08-16"


def test_unknown_conversation_is_not_guessed() -> None:
    assert route_conversation("Tolong ceritakan film terbaru") is None
