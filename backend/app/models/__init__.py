"""Import de tous les modeles MVP pour que Base.metadata les connaisse (Alembic, create_all tests)."""
from app.models.analysis import AnalysisJob, AnalysisWarning, ParcelAnalysis  # noqa: F401
from app.models.building import Building, ParcelBuilding  # noqa: F401
from app.models.economics import CostAssumption, ParcelFeasibility  # noqa: F401
from app.models.municipality import Municipality  # noqa: F401
from app.models.parcel import Parcel  # noqa: F401
from app.models.risk import Risk  # noqa: F401
from app.models.scoring import ParcelScore, ScoringWeights  # noqa: F401
from app.models.source import SourceRecord  # noqa: F401
from app.models.urbanism import UrbanismZone  # noqa: F401

__all__ = [
    "AnalysisJob",
    "AnalysisWarning",
    "ParcelAnalysis",
    "Building",
    "ParcelBuilding",
    "CostAssumption",
    "ParcelFeasibility",
    "Municipality",
    "Parcel",
    "Risk",
    "ParcelScore",
    "ScoringWeights",
    "SourceRecord",
    "UrbanismZone",
]
