"""ParcelScore [MVP simplifie], ScoringWeights [MVP] -- voir docs/DATA_MODEL.md et docs/SCORING_ENGINE.md."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base_mixins import UUIDPKMixin


class ScoringWeights(UUIDPKMixin, Base):
    __tablename__ = "scoring_weights"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    penalties: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ParcelScore(UUIDPKMixin, Base):
    __tablename__ = "parcel_scores"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcel_analyses.id"), nullable=False, index=True
    )
    score_urbanisme: Mapped[float] = mapped_column(Float, nullable=False)
    score_geometrie: Mapped[float] = mapped_column(Float, nullable=False)
    score_surface: Mapped[float] = mapped_column(Float, nullable=False)
    score_acces: Mapped[float] = mapped_column(Float, nullable=False)
    score_reseaux: Mapped[float] = mapped_column(Float, nullable=False)
    score_risques: Mapped[float] = mapped_column(Float, nullable=False)
    score_densification: Mapped[float] = mapped_column(Float, nullable=False)
    score_complexite: Mapped[float] = mapped_column(Float, nullable=False)
    score_qualite_donnees: Mapped[float] = mapped_column(Float, nullable=False)
    score_global: Mapped[float] = mapped_column(Float, nullable=False)
    explanation_text: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    weights_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scoring_weights.id"), nullable=True
    )
