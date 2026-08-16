import json
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.block import GeometryValidationResult
from app.schemas.common import PolygonGeoJSON


class GISService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def validate_polygon(self, polygon: PolygonGeoJSON) -> GeometryValidationResult:
        statement = text(
            """
            with candidate as (
              select extensions.st_setsrid(
                extensions.st_geomfromgeojson(:geojson), 4326
              ) as geom
            )
            select extensions.st_isvalid(geom) as valid,
                   extensions.st_isvalidreason(geom) as reason,
                   case when extensions.st_isvalid(geom)
                     then round(extensions.st_area(geom::extensions.geography)::numeric, 2)
                   end as area_m2
            from candidate
            """
        )
        row = (
            await self.session.execute(
                statement, {"geojson": json.dumps(polygon.model_dump(mode="json"))}
            )
        ).one()
        area_m2 = row.area_m2
        return GeometryValidationResult(
            valid=row.valid,
            reason=row.reason,
            area_m2=area_m2,
            area_ha=(Decimal(area_m2) / Decimal(10000)).quantize(Decimal("0.0001"))
            if area_m2 is not None
            else None,
        )
