"""Risk [MVP simplifie : niveau commune uniquement] -- voir docs/DATA_MODEL.md."""
from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base_mixins import UUIDPKMixin
from app.models.enums import RiskLevelEnum, RiskTypeEnum


class Risk(UUIDPKMixin, Base):
    __tablename__ = "risks"

    municipality_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("municipalities.id"), nullable=False, index=True
    )
    risk_type: Mapped[RiskTypeEnum] = mapped_column(
        Enum(RiskTypeEnum, name="risk_type_enum"), nullable=False
    )
    level: Mapped[RiskLevelEnum] = mapped_column(
        Enum(RiskLevelEnum, name="risk_level_enum"), nullable=False, default=RiskLevelEnum.UNKNOWN
    )
    geometry: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=2154), nullable=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_records.id"), nullable=True
    )
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
