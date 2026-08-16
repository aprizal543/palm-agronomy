from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

Longitude = Annotated[float, Field(ge=-180, le=180)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Position = tuple[Longitude, Latitude]


class PointGeoJSON(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: Position


class PolygonGeoJSON(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[Position]]

    @model_validator(mode="after")
    def validate_rings(self):
        if not self.coordinates:
            raise ValueError("Polygon minimal memiliki satu ring")
        for ring in self.coordinates:
            if len(ring) < 4:
                raise ValueError("Setiap ring polygon minimal memiliki empat posisi")
            if ring[0] != ring[-1]:
                raise ValueError("Ring polygon harus tertutup: posisi awal dan akhir harus sama")
        return self


class MultiPolygonGeoJSON(BaseModel):
    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: list[list[list[Position]]]

    @model_validator(mode="after")
    def validate_polygons(self):
        if not self.coordinates:
            raise ValueError("MultiPolygon minimal memiliki satu polygon")
        for polygon in self.coordinates:
            PolygonGeoJSON(coordinates=polygon)
        return self


FarmBoundary = PolygonGeoJSON | MultiPolygonGeoJSON


class SpatialValidationDecision(BaseModel):
    actor_user_id: UUID
    decision: Literal["confirmed", "rejected"]
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def rejection_needs_notes(self):
        if self.decision == "rejected" and not (self.notes or "").strip():
            raise ValueError("notes wajib diisi ketika polygon ditolak")
        return self
