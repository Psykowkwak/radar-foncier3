"""ParcelAnalysis, AnalysisJob, AnalysisWarning [MVP] -- voir docs/DATA_MODEL.md."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base_mixins import UUIDPKMixin
from app.models.enums import AnalysisJobStatusEnum, BuiltCategoryEnum, ConstructibilityStatusEnum, SeverityEnum


class AnalysisJob(UUIDPKMixin, Base):
    __tablename__ = "analysis_jobs"

    municipality_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("municipalities.id"), nullable=False, index=True
    )
    status: Mapped[AnalysisJobStatusEnum] = mapped_column(
        Enum(AnalysisJobStatusEnum, name="analysis_job_status_enum"),
        nullable=False,
        default=AnalysisJobStatusEnum.PENDING,
    )
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parcels_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parcels_selected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parcels_excluded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exclusion_reasons: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_log: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ParcelAnalysis(UUIDPKMixin, Base):
    __tablename__ = "parcel_analyses"

    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_jobs.id"), nullable=True, index=True
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    parcel_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    building_footprint_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    building_coverage_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    unbuilt_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    largest_contiguous_unbuilt_area: Mapped[float | None] = mapped_column(Float, nullable=True)

    width_estimated: Mapped[float | None] = mapped_column(Float, nullable=True)
    depth_estimated: Mapped[float | None] = mapped_column(Float, nullable=True)
    road_frontage_length: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    built_category: Mapped[BuiltCategoryEnum | None] = mapped_column(
        Enum(BuiltCategoryEnum, name="built_category_enum"), nullable=True
    )
    constructibility_status: Mapped[ConstructibilityStatusEnum] = mapped_column(
        Enum(ConstructibilityStatusEnum, name="constructibility_status_enum"),
        nullable=False,
        default=ConstructibilityStatusEnum.DONNEES_INSUFFISANTES,
    )
    urbanism_confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggested_operations: Mapped[list | None] = mapped_column(JSONB, nullable=True)


class AnalysisWarning(UUIDPKMixin, Base):
    __tablename__ = "analysis_warnings"

    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_jobs.id"), nullable=True, index=True
    )
    parcel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True, index=True
    )
    severity: Mapped[SeverityEnum] = mapped_column(Enum(SeverityEnum, name="severity_enum"), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_records.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
