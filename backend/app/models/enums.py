"""Enums partages entre modeles -- voir docs/DATA_MODEL.md (note d'implementation :
"Les scores et statuts de constructibilite utilisent des Enum Python + CHECK constraint
PostgreSQL, jamais des chaines libres, pour eviter la derive de valeurs.")
"""
import enum


class ReliabilityEnum(str, enum.Enum):
    OFFICIAL = "OFFICIAL"
    DERIVED = "DERIVED"
    USER_IMPORTED = "USER_IMPORTED"


class SeverityEnum(str, enum.Enum):
    BLOQUANT = "BLOQUANT"
    IMPORTANT = "IMPORTANT"
    INFORMATION = "INFORMATION"


class BuiltCategoryEnum(str, enum.Enum):
    VACANT_LAND = "VACANT_LAND"
    LIGHTLY_BUILT = "LIGHTLY_BUILT"
    PARTIALLY_BUILT = "PARTIALLY_BUILT"
    HEAVILY_BUILT = "HEAVILY_BUILT"
    FULLY_DEVELOPED = "FULLY_DEVELOPED"
    REDEVELOPMENT_POTENTIAL = "REDEVELOPMENT_POTENTIAL"


class ConstructibilityStatusEnum(str, enum.Enum):
    FAVORABLE = "FAVORABLE"
    FAVORABLE_SOUS_CONDITIONS = "FAVORABLE_SOUS_CONDITIONS"
    COMPLEXE = "COMPLEXE"
    DEFAVORABLE = "DEFAVORABLE"
    A_PRIORI_NON_CONSTRUCTIBLE = "A_PRIORI_NON_CONSTRUCTIBLE"
    DONNEES_INSUFFISANTES = "DONNEES_INSUFFISANTES"


class AnalysisJobStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RiskTypeEnum(str, enum.Enum):
    RGA = "RGA"
    CAVITE = "CAVITE"
    PPR = "PPR"
    AUTRE = "AUTRE"


class RiskLevelEnum(str, enum.Enum):
    FAIBLE = "FAIBLE"
    MOYEN = "MOYEN"
    FORT = "FORT"
    UNKNOWN = "UNKNOWN"
