from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.blocks import BlockRepository
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
        self._tools = {
            "resolve_block_by_location": AgentTool(
                name="resolve_block_by_location",
                description="Resolve GPS point and accuracy against confirmed PostGIS blocks.",
                handler=self.resolve_block_by_location,
            )
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
