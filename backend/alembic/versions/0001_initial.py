"""Migration initiale -- toutes les tables MVP (voir docs/DATA_MODEL.md), extensions
postgis + pgcrypto, index GIST sur les colonnes geometrie.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-13
"""
from __future__ import annotations

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    reliability_enum = sa.Enum("OFFICIAL", "DERIVED", "USER_IMPORTED", name="reliability_enum")
    severity_enum = sa.Enum("BLOQUANT", "IMPORTANT", "INFORMATION", name="severity_enum")
    built_category_enum = sa.Enum(
        "VACANT_LAND",
        "LIGHTLY_BUILT",
        "PARTIALLY_BUILT",
        "HEAVILY_BUILT",
        "FULLY_DEVELOPED",
        "REDEVELOPMENT_POTENTIAL",
        name="built_category_enum",
    )
    constructibility_status_enum = sa.Enum(
        "FAVORABLE",
        "FAVORABLE_SOUS_CONDITIONS",
        "COMPLEXE",
        "DEFAVORABLE",
        "A_PRIORI_NON_CONSTRUCTIBLE",
        "DONNEES_INSUFFISANTES",
        name="constructibility_status_enum",
    )
    analysis_job_status_enum = sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", name="analysis_job_status_enum")
    risk_type_enum = sa.Enum("RGA", "CAVITE", "PPR", "AUTRE", name="risk_type_enum")
    risk_level_enum = sa.Enum("FAIBLE", "MOYEN", "FORT", "UNKNOWN", name="risk_level_enum")

    # --- source_records ---
    op.create_table(
        "source_records",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dataset_version", sa.String(100), nullable=True),
        sa.Column("reliability", reliability_enum, nullable=False, server_default="OFFICIAL"),
        sa.Column("checksum", sa.String(128), nullable=True),
    )

    # --- municipalities ---
    op.create_table(
        "municipalities",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("insee_code", sa.String(5), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("department_code", sa.String(3), nullable=True),
        sa.Column("region_code", sa.String(3), nullable=True),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=2154), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_municipalities_insee_code", "municipalities", ["insee_code"])
    op.create_index("ix_municipalities_insee_code", "municipalities", ["insee_code"])
    op.create_index("ix_municipalities_geometry", "municipalities", ["geometry"], postgresql_using="gist")

    # --- parcels ---
    op.create_table(
        "parcels",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("municipality_id", pg.UUID(as_uuid=True), sa.ForeignKey("municipalities.id"), nullable=False),
        sa.Column("section", sa.String(10), nullable=True),
        sa.Column("numero", sa.String(10), nullable=True),
        sa.Column("com_abs", sa.String(10), nullable=True),
        sa.Column("prefixe", sa.String(10), nullable=True),
        sa.Column("reference", sa.String(30), nullable=True),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=2154), nullable=False),
        sa.Column("area_official", sa.Float(), nullable=True),
        sa.Column("area_computed", sa.Float(), nullable=True),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("source_records.id"), nullable=True),
    )
    op.create_index("ix_parcels_municipality_id", "parcels", ["municipality_id"])
    op.create_index("ix_parcels_reference", "parcels", ["reference"])
    op.create_index("ix_parcels_geometry", "parcels", ["geometry"], postgresql_using="gist")

    # --- buildings ---
    op.create_table(
        "buildings",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=2154), nullable=False),
        sa.Column("footprint_area", sa.Float(), nullable=True),
        sa.Column("building_type", sa.String(100), nullable=True),
        sa.Column("building_type_confidence", sa.Float(), nullable=True),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("source_records.id"), nullable=True),
    )
    op.create_index("ix_buildings_geometry", "buildings", ["geometry"], postgresql_using="gist")

    # --- parcel_buildings ---
    op.create_table(
        "parcel_buildings",
        sa.Column("parcel_id", pg.UUID(as_uuid=True), sa.ForeignKey("parcels.id"), primary_key=True),
        sa.Column("building_id", pg.UUID(as_uuid=True), sa.ForeignKey("buildings.id"), primary_key=True),
        sa.Column("overlap_area", sa.Float(), nullable=True),
    )

    # --- urbanism_zones ---
    op.create_table(
        "urbanism_zones",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("municipality_id", pg.UUID(as_uuid=True), sa.ForeignKey("municipalities.id"), nullable=False),
        sa.Column("libelle", sa.String(50), nullable=True),
        sa.Column("libelong", sa.String(500), nullable=True),
        sa.Column("typezone", sa.String(10), nullable=True),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=2154), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_urbanism_zones_municipality_id", "urbanism_zones", ["municipality_id"])
    op.create_index("ix_urbanism_zones_geometry", "urbanism_zones", ["geometry"], postgresql_using="gist")

    # --- risks ---
    op.create_table(
        "risks",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("municipality_id", pg.UUID(as_uuid=True), sa.ForeignKey("municipalities.id"), nullable=False),
        sa.Column("risk_type", risk_type_enum, nullable=False),
        sa.Column("level", risk_level_enum, nullable=False, server_default="UNKNOWN"),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=2154), nullable=True),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("source_records.id"), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_risks_municipality_id", "risks", ["municipality_id"])
    op.create_index("ix_risks_geometry", "risks", ["geometry"], postgresql_using="gist")

    # --- analysis_jobs ---
    op.create_table(
        "analysis_jobs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("municipality_id", pg.UUID(as_uuid=True), sa.ForeignKey("municipalities.id"), nullable=False),
        sa.Column("status", analysis_job_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_step", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parcels_total", sa.Integer(), nullable=True),
        sa.Column("parcels_selected", sa.Integer(), nullable=True),
        sa.Column("parcels_excluded", sa.Integer(), nullable=True),
        sa.Column("exclusion_reasons", pg.JSONB(), nullable=True),
        sa.Column("error_log", pg.JSONB(), nullable=True),
    )
    op.create_index("ix_analysis_jobs_municipality_id", "analysis_jobs", ["municipality_id"])

    # --- parcel_analyses ---
    op.create_table(
        "parcel_analyses",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parcel_id", pg.UUID(as_uuid=True), sa.ForeignKey("parcels.id"), nullable=False),
        sa.Column("job_id", pg.UUID(as_uuid=True), sa.ForeignKey("analysis_jobs.id"), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parcel_area", sa.Float(), nullable=True),
        sa.Column("building_footprint_area", sa.Float(), nullable=True),
        sa.Column("building_coverage_ratio", sa.Float(), nullable=True),
        sa.Column("unbuilt_area", sa.Float(), nullable=True),
        sa.Column("largest_contiguous_unbuilt_area", sa.Float(), nullable=True),
        sa.Column("width_estimated", sa.Float(), nullable=True),
        sa.Column("depth_estimated", sa.Float(), nullable=True),
        sa.Column("road_frontage_length", sa.Float(), nullable=True),
        sa.Column("geometry_quality_score", sa.Float(), nullable=True),
        sa.Column("built_category", built_category_enum, nullable=True),
        sa.Column("constructibility_status", constructibility_status_enum, nullable=False, server_default="DONNEES_INSUFFISANTES"),
        sa.Column("urbanism_confidence_score", sa.Float(), nullable=True),
        sa.Column("suggested_operations", pg.JSONB(), nullable=True),
    )
    op.create_index("ix_parcel_analyses_parcel_id", "parcel_analyses", ["parcel_id"])
    op.create_index("ix_parcel_analyses_job_id", "parcel_analyses", ["job_id"])

    # --- analysis_warnings ---
    op.create_table(
        "analysis_warnings",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", pg.UUID(as_uuid=True), sa.ForeignKey("analysis_jobs.id"), nullable=True),
        sa.Column("parcel_id", pg.UUID(as_uuid=True), sa.ForeignKey("parcels.id"), nullable=True),
        sa.Column("severity", severity_enum, nullable=False),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("source_records.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analysis_warnings_job_id", "analysis_warnings", ["job_id"])
    op.create_index("ix_analysis_warnings_parcel_id", "analysis_warnings", ["parcel_id"])

    # --- scoring_weights ---
    op.create_table(
        "scoring_weights",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("weights", pg.JSONB(), nullable=False),
        sa.Column("penalties", pg.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- parcel_scores ---
    op.create_table(
        "parcel_scores",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("analysis_id", pg.UUID(as_uuid=True), sa.ForeignKey("parcel_analyses.id"), nullable=False),
        sa.Column("score_urbanisme", sa.Float(), nullable=False),
        sa.Column("score_geometrie", sa.Float(), nullable=False),
        sa.Column("score_surface", sa.Float(), nullable=False),
        sa.Column("score_acces", sa.Float(), nullable=False),
        sa.Column("score_reseaux", sa.Float(), nullable=False),
        sa.Column("score_risques", sa.Float(), nullable=False),
        sa.Column("score_densification", sa.Float(), nullable=False),
        sa.Column("score_complexite", sa.Float(), nullable=False),
        sa.Column("score_qualite_donnees", sa.Float(), nullable=False),
        sa.Column("score_global", sa.Float(), nullable=False),
        sa.Column("explanation_text", sa.String(4000), nullable=True),
        sa.Column("weights_version_id", pg.UUID(as_uuid=True), sa.ForeignKey("scoring_weights.id"), nullable=True),
    )
    op.create_index("ix_parcel_scores_analysis_id", "parcel_scores", ["analysis_id"])


def downgrade() -> None:
    op.drop_table("parcel_scores")
    op.drop_table("scoring_weights")
    op.drop_table("analysis_warnings")
    op.drop_table("parcel_analyses")
    op.drop_table("analysis_jobs")
    op.drop_table("risks")
    op.drop_table("urbanism_zones")
    op.drop_table("parcel_buildings")
    op.drop_table("buildings")
    op.drop_table("parcels")
    op.drop_table("municipalities")
    op.drop_table("source_records")

    sa.Enum(name="risk_level_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="risk_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="analysis_job_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="constructibility_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="built_category_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="severity_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="reliability_enum").drop(op.get_bind(), checkfirst=True)
