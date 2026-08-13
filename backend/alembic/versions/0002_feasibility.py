"""Ajoute cost_assumptions + parcel_feasibility (bilan promoteur simplifie), voir
docs/FEASIBILITY_ENGINE.md et app/models/economics.py. Seed une ligne
CostAssumption par defaut.

Revision ID: 0002_feasibility
Revises: 0001_initial
Create Date: 2026-08-13
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_feasibility"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_assumptions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("label", sa.String(200), nullable=False, server_default="Hypotheses par defaut"),
        sa.Column("construction_cost_per_m2", sa.Float(), nullable=False, server_default="1900.0"),
        sa.Column("demolition_cost_per_m2_footprint", sa.Float(), nullable=False, server_default="120.0"),
        sa.Column("overhead_ratio", sa.Float(), nullable=False, server_default="0.35"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "parcel_feasibility",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "analysis_id", pg.UUID(as_uuid=True), sa.ForeignKey("parcel_analyses.id"), nullable=False, unique=True
        ),
        sa.Column("cost_assumption_id", pg.UUID(as_uuid=True), sa.ForeignKey("cost_assumptions.id"), nullable=True),
        sa.Column("buildable_footprint_m2", sa.Float(), nullable=True),
        sa.Column("estimated_new_floor_area_m2", sa.Float(), nullable=True),
        sa.Column("existing_building_footprint_m2", sa.Float(), nullable=True),
        sa.Column("demolition_recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("price_per_m2_bati_dvf", sa.Float(), nullable=True),
        sa.Column("price_per_m2_terrain_dvf", sa.Float(), nullable=True),
        sa.Column("dvf_sample_size_bati", sa.Integer(), nullable=True),
        sa.Column("dvf_sample_size_terrain", sa.Integer(), nullable=True),
        sa.Column("estimated_land_cost", sa.Float(), nullable=True),
        sa.Column("estimated_demolition_cost", sa.Float(), nullable=True),
        sa.Column("estimated_construction_cost", sa.Float(), nullable=True),
        sa.Column("estimated_overhead_cost", sa.Float(), nullable=True),
        sa.Column("estimated_revenue", sa.Float(), nullable=True),
        sa.Column("estimated_margin", sa.Float(), nullable=True),
        sa.Column("margin_ratio", sa.Float(), nullable=True),
        sa.Column("computable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("explanation_text", sa.String(2000), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_parcel_feasibility_analysis_id", "parcel_feasibility", ["analysis_id"], unique=True)

    op.execute(
        """
        INSERT INTO cost_assumptions
            (id, label, construction_cost_per_m2, demolition_cost_per_m2_footprint, overhead_ratio,
             is_default, notes, created_at)
        VALUES
            (gen_random_uuid(), 'Hypotheses par defaut', 1900.0, 120.0, 0.35, true,
             'Ordres de grandeur professionnels generiques, a ajuster localement -- voir '
             'docs/FEASIBILITY_ENGINE.md.', now())
        """
    )


def downgrade() -> None:
    op.drop_table("parcel_feasibility")
    op.drop_table("cost_assumptions")
