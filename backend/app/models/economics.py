"""CostAssumption + ParcelFeasibility -- version allegee du moteur de faisabilite,
voir docs/FEASIBILITY_ENGINE.md "Bilan promoteur" et "Garde-fous non negociables"
("Toute hypothese economique... est un parametre modifiable en base, jamais une
constante dans le code").

Ce n'est PAS le moteur de faisabilite complet documente en V2 (pas d'algorithme
d'implantation de batiment, pas de placement reel du stationnement, pas de plan de
masse) : c'est une estimation simplifiee de marge apparente, construite pour
classer les parcelles par potentiel economique reel plutot que par simple score
d'urbanisme -- voir app/services/feasibility.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base_mixins import UUIDPKMixin


class CostAssumption(UUIDPKMixin, Base):
    """Hypotheses economiques du bilan promoteur simplifie. Valeurs par defaut =
    ordres de grandeur professionnels usuels documentes en commentaire (pas des
    donnees de marche en temps reel) -- modifiables ici sans toucher au code. Une
    seule ligne is_default=True doit exister au MVP."""

    __tablename__ = "cost_assumptions"

    label: Mapped[str] = mapped_column(String(200), nullable=False, default="Hypotheses par defaut")

    # Cout de construction neuve, hors foncier, hors honoraires (gros oeuvre + second
    # oeuvre + VRD interne) -- ordre de grandeur logement collectif standard en France
    # (source : observatoires regionaux de la construction, a affiner localement).
    construction_cost_per_m2: Mapped[float] = mapped_column(Float, nullable=False, default=1900.0)

    # Cout de demolition d'un batiment existant, par m2 d'emprise au sol -- ordre de
    # grandeur demolition maison individuelle standard (hors desamiantage specifique).
    demolition_cost_per_m2_footprint: Mapped[float] = mapped_column(Float, nullable=False, default=120.0)

    # VRD externe + honoraires (maitrise d'oeuvre, bureau d'etudes) + frais financiers
    # + alea chantier + marge cible promoteur, exprimes en % des recettes -- montage
    # d'operation classique, PAS une marge nette garantie.
    overhead_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.35)

    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ParcelFeasibility(UUIDPKMixin, Base):
    """Estimation economique simplifiee par parcelle -- voir
    app/services/feasibility.py. Rappel explicite (repris dans explanation_text a
    chaque calcul) : ceci est une approximation d'ordre de grandeur, PAS un bilan
    promoteur bancable. Elle combine une hypothese generique d'emprise
    constructible (faute de reglement PLU structure disponible a l'echelle
    nationale -- voir docs/URBANISM_ENGINE.md) avec des prix DVF reels et des couts
    parametrables (CostAssumption)."""

    __tablename__ = "parcel_feasibility"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcel_analyses.id"), nullable=False, index=True, unique=True
    )
    cost_assumption_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_assumptions.id"), nullable=True
    )

    buildable_footprint_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_new_floor_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    existing_building_footprint_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    demolition_recommended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    price_per_m2_bati_dvf: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_per_m2_terrain_dvf: Mapped[float | None] = mapped_column(Float, nullable=True)
    dvf_sample_size_bati: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dvf_sample_size_terrain: Mapped[int | None] = mapped_column(Integer, nullable=True)

    estimated_land_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_demolition_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_construction_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_overhead_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    margin_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    computable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    explanation_text: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
