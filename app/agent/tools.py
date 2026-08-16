from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.blocks import BlockRepository
from app.repositories.production import ProductionRepository
from app.schemas.block import LocationResolution

ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    handler: ToolHandler


class AgronomyToolRegistry:
    """Strict tool allow-list. An LLM never receives SQL or a database connection."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._tools: dict[str, AgentTool] = {
            "resolve_block_by_location": AgentTool(
                name="resolve_block_by_location",
                description="Resolve GPS point and accuracy against confirmed PostGIS blocks.",
                handler=self.resolve_block_by_location,
            ),
            "get_farm_block_context": AgentTool(
                name="get_farm_block_context",
                description="Read the confirmed active farm/block context for a Telegram chat.",
                handler=self.get_farm_block_context,
            ),
            "record_production": AgentTool(
                name="record_production",
                description="Store one human-confirmed FFB production record for the active block.",
                handler=self.record_production,
            ),
            "list_production_history": AgentTool(
                name="list_production_history",
                description="List recent confirmed production records for the active block.",
                handler=self.list_production_history,
            ),
            "summarize_production": AgentTool(
                name="summarize_production",
                description="Aggregate confirmed production for the active block and date window.",
                handler=self.summarize_production,
            ),
        }

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    async def execute(self, name: str, **arguments: Any) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Tool tidak diizinkan: {name}")
        return await tool.handler(**arguments)

    async def resolve_block_by_location(
        self, *, longitude: float, latitude: float, accuracy_m: float
    ) -> dict[str, Any]:
        matches = await BlockRepository(self.session).find_by_location(
            longitude, latitude, accuracy_m
        )
        if not matches:
            resolution_status = "not_found"
        elif len(matches) > 1:
            resolution_status = "ambiguous"
        elif not matches[0]["contains_point"] or matches[0]["distance_to_boundary_m"] <= accuracy_m:
            resolution_status = "confirmation_required"
        else:
            resolution_status = "matched"
        return LocationResolution(
            status=resolution_status,
            accuracy_m=accuracy_m,
            candidates=matches,
        ).model_dump(mode="json")

    async def get_farm_block_context(
        self, *, chat_id: int, telegram_user_id: int
    ) -> dict[str, Any]:
        return await ProductionRepository(self.session).get_active_context(
            chat_id, telegram_user_id
        )

    async def record_production(self, **arguments: Any) -> dict[str, Any]:
        return await ProductionRepository(self.session).record_confirmed(**arguments)

    async def list_production_history(
        self, *, chat_id: int, telegram_user_id: int, limit: int
    ) -> dict[str, Any]:
        return await ProductionRepository(self.session).history(
            chat_id=chat_id, telegram_user_id=telegram_user_id, limit=limit
        )

    async def summarize_production(
        self, *, chat_id: int, telegram_user_id: int, days: int
    ) -> dict[str, Any]:
        return await ProductionRepository(self.session).summary(
            chat_id=chat_id, telegram_user_id=telegram_user_id, days=days
        )
