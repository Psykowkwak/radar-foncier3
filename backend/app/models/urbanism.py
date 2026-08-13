"""UrbanismZone [MVP simplifie] -- voir docs/DATA_MODEL.md.

UrbanismDocument, UrbanismRuleSet, UrbanismConstraint sont V1 (non implementes ici).
Au MVP, UrbanismZone est alimentee directement par les attributs GeoJSON de
zone-urba (API Carto IGN GPU), sans resolution de document ni regle textuelle.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base_mixins import UUIDPKMixin


class UrbanismZone(UUIDPKMixin, Base):
    __tablename__ = "urbanism_zones"

    municipality_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("municipalities.id"), nullable=False, index=True
    )
    libelle: Mapped[str | None] = mapped_column(String(50), nullable=True)
    libelong: Mapped[str | None] = mapped_column(String(500), nullable=True)
    typezone: Mapped[str | None] = mapped_column(String(10), nullable=True)
    geometry: Mapped[str] = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=2154), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
