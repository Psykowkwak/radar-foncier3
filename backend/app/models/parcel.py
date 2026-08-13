"""Parcel [MVP] -- voir docs/DATA_MODEL.md."""
from __future__ import annotations

import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base_mixins import UUIDPKMixin


class Parcel(UUIDPKMixin, Base):
    __tablename__ = "parcels"

    municipality_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("municipalities.id"), nullable=False, index=True
    )
    section: Mapped[str | None] = mapped_column(String(10), nullable=True)
    numero: Mapped[str | None] = mapped_column(String(10), nullable=True)
    com_abs: Mapped[str | None] = mapped_column(String(10), nullable=True)
    prefixe: Mapped[str | None] = mapped_column(String(10), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(30), index=True, nullable=True)
    geometry: Mapped[str] = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=2154), nullable=False)
    area_official: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_computed: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_records.id"), nullable=True
    )

    municipality: Mapped["Municipality"] = relationship(back_populates="parcels")  # noqa: F821
