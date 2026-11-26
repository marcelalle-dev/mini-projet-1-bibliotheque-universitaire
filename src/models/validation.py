"""Fonctions de validation partagées par les modèles."""

import re

from src.exceptions import DonneesInvalides

_ISBN_CARACTERES = re.compile(r"[\s-]")


def texte_obligatoire(valeur, nom_champ):
    """Retourne ``valeur`` nettoyée ou lève :class:`DonneesInvalides`.

    Args:
        valeur: valeur à contrôler (doit être une chaîne non vide).
        nom_champ: nom du champ, utilisé dans le message d'erreur.
    """
    if not isinstance(valeur, str) or not valeur.strip():
        raise DonneesInvalides(f"Le champ « {nom_champ} » est obligatoire.")
    return " ".join(valeur.split())


def normaliser_isbn(isbn):
    """Normalise un ISBN-10 ou ISBN-13 et vérifie sa clé de contrôle.

    Les tirets et espaces sont supprimés ; un ``x`` final d'ISBN-10 est
    converti en majuscule.

    Raises:
        DonneesInvalides: si le format ou la clé de contrôle est incorrect.
    """
    brut = texte_obligatoire(isbn, "ISBN")
    code = _ISBN_CARACTERES.sub("", brut).upper()
    if len(code) == 13 and code.isdigit():
        total = sum(
            int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(code[:12])
        )
        if (10 - total % 10) % 10 == int(code[12]):
            return code
    elif len(code) == 10 and code[:9].isdigit() and (
            code[9].isdigit() or code[9] == "X"):
        total = sum(int(c) * (10 - i) for i, c in enumerate(code[:9]))
        cle = 10 if code[9] == "X" else int(code[9])
        if (total + cle) % 11 == 0:
            return code
    raise DonneesInvalides(
        f"ISBN « {brut} » invalide (10 ou 13 chiffres avec clé correcte)."
    )
