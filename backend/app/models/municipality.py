"""Municipality [MVP] -- voir docs/DATA_MODEL.md."""
from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base_mixins import UUIDPKMixin


class Municipality(UUIDPKMixin, Base):
    __tablename__ = "municipalities"

    insee_code: Mapped[str] = mapped_column(String(5), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    department_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    region_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    geometry: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=2154), nullable=True
    )
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    parcels: Mapped[list["Parcel"]] = relationship(back_populates="municipality")  # noqa: F821
