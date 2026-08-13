"""SourceRecord [MVP] -- voir docs/DATA_MODEL.md et docs/ARCHITECTURE.md §4."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base_mixins import UUIDPKMixin
from app.models.enums import ReliabilityEnum


class SourceRecord(UUIDPKMixin, Base):
    __tablename__ = "source_records"

    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reliability: Mapped[ReliabilityEnum] = mapped_column(
        Enum(ReliabilityEnum, name="reliability_enum"), nullable=False, default=ReliabilityEnum.OFFICIAL
    )
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
