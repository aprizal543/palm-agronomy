import pytest

from app.agent.tools import AgronomyToolRegistry


def test_tool_registry_is_allow_listed() -> None:
    registry = AgronomyToolRegistry(session=None)
    assert registry.names == (
        "get_farm_block_context",
        "list_production_history",
        "record_production",
        "resolve_block_by_location",
        "retrieve_agronomy_knowledge",
        "summarize_production",
    )


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected_without_database_access() -> None:
    registry = AgronomyToolRegistry(session=None)
    with pytest.raises(ValueError, match="Tool tidak diizinkan"):
        await registry.execute("execute_sql", sql="drop table palm.blocks")
