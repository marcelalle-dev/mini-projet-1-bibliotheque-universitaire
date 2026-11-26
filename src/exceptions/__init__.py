"""Exceptions personnalisées exposées par le paquet."""

from src.exceptions.exceptions_personnalisees import (
    BibliothequeErreur,
    DonneesInvalides,
    DoublonErreur,
    EmpruntDejaCloture,
    EmpruntDejaEnCours,
    EmpruntIntrouvable,
    ErreurPersistance,
    ExemplaireIntrouvable,
    LecteurEnRetard,
    LecteurIntrouvable,
    OperationImpossible,
    OuvrageIndisponible,
    OuvrageIntrouvable,
    ProlongationRefusee,
    QuotaDepasse,
)

__all__ = [
    "BibliothequeErreur",
    "DonneesInvalides",
    "DoublonErreur",
    "EmpruntDejaCloture",
    "EmpruntDejaEnCours",
    "EmpruntIntrouvable",
    "ErreurPersistance",
    "ExemplaireIntrouvable",
    "LecteurEnRetard",
    "LecteurIntrouvable",
    "OperationImpossible",
    "OuvrageIndisponible",
    "OuvrageIntrouvable",
    "ProlongationRefusee",
    "QuotaDepasse",
]
