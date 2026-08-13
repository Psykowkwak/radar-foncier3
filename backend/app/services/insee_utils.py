"""Utilitaires partages autour du code INSEE commune."""
from __future__ import annotations


def department_from_insee(code_insee: str) -> str:
    """Deduit le code departement a partir du code INSEE commune (approximation
    documentee, suffisante pour construire les URLs de telechargement Etalab).

    - DOM (97x) : 3 premiers caracteres.
    - Corse : le code INSEE commence deja par 2A/2B.
    - Metropole : 2 premiers caracteres.
    """
    code_insee = code_insee.strip().upper()
    if code_insee.startswith("97"):
        return code_insee[:3]
    return code_insee[:2]
