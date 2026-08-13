"""Building et ParcelBuilding [MVP] -- voir docs/DATA_MODEL.md."""
from __future__ import annotations

import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base_mixins import UUIDPKMixin


class Building(UUIDPKMixin, Base):
    __tablename__ = "buildings"

    geometry: Mapped[str] = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=2154), nullable=False)
    footprint_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    building_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    building_type_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_records.id"), nullable=True
    )


class ParcelBuilding(Base):
    """Table d'association gerant le chevauchement bati/parcelle."""

    __tablename__ = "parcel_buildings"

    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), primary_key=True
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("buildings.id"), primary_key=True
    )
    overlap_area: Mapped[float | None] = mapped_column(Float, nullable=True)
