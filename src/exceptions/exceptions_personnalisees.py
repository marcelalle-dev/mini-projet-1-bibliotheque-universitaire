"""Exceptions personnalisées de l'application.

Toutes les erreurs métier héritent de :class:`BibliothequeErreur`, ce qui
permet à l'interface de les intercepter de manière uniforme tout en laissant
remonter les erreurs de programmation (``TypeError``, ``KeyError``...).
"""


class BibliothequeErreur(Exception):
    """Classe de base de toutes les erreurs métier de la bibliothèque."""


class DonneesInvalides(BibliothequeErreur):
    """Levée lorsqu'une donnée saisie ou chargée ne respecte pas les règles."""


class OuvrageIntrouvable(BibliothequeErreur):
    """Levée lorsqu'aucun ouvrage ne correspond à l'identifiant demandé."""

    def __init__(self, id_ouvrage):
        """Construit le message à partir de l'identifiant recherché."""
        super().__init__(
            f"Aucun ouvrage ne porte l'identifiant « {id_ouvrage} »."
        )
        self.id_ouvrage = id_ouvrage


class ExemplaireIntrouvable(BibliothequeErreur):
    """Levée lorsqu'aucun exemplaire ne correspond à l'identifiant demandé."""

    def __init__(self, id_exemplaire):
        """Construit le message à partir de l'identifiant recherché."""
        super().__init__(
            f"Aucun exemplaire ne porte l'identifiant « {id_exemplaire} »."
        )
        self.id_exemplaire = id_exemplaire


class LecteurIntrouvable(BibliothequeErreur):
    """Levée lorsqu'aucun lecteur ne correspond à l'identifiant demandé."""

    def __init__(self, id_lecteur):
        """Construit le message à partir de l'identifiant recherché."""
        super().__init__(
            f"Aucun lecteur ne porte l'identifiant « {id_lecteur} »."
        )
        self.id_lecteur = id_lecteur


class EmpruntIntrouvable(BibliothequeErreur):
    """Levée lorsqu'aucun emprunt ne correspond à l'identifiant demandé."""

    def __init__(self, id_emprunt):
        """Construit le message à partir de l'identifiant recherché."""
        super().__init__(
            f"Aucun emprunt ne porte l'identifiant « {id_emprunt} »."
        )
        self.id_emprunt = id_emprunt


class DoublonErreur(BibliothequeErreur):
    """Levée lorsqu'on tente de créer un élément qui existe déjà (ex. ISBN)."""


class OuvrageIndisponible(BibliothequeErreur):
    """Levée lorsqu'aucun exemplaire de l'ouvrage n'est disponible au prêt."""

    def __init__(self, ouvrage):
        """Construit le message à partir de l'ouvrage concerné."""
        super().__init__(
            f"L'ouvrage « {ouvrage.titre} » ({ouvrage.id_ouvrage}) n'a aucun "
            "exemplaire disponible."
        )
        self.ouvrage = ouvrage


class QuotaDepasse(BibliothequeErreur):
    """Levée lorsqu'un lecteur a atteint son nombre maximal d'emprunts."""

    def __init__(self, lecteur):
        """Construit le message à partir du lecteur concerné."""
        super().__init__(
            f"{lecteur.nom_complet} a atteint son quota de "
            f"{lecteur.quota_max} emprunts simultanés "
            f"({lecteur.type_lecteur})."
        )
        self.lecteur = lecteur


class LecteurEnRetard(BibliothequeErreur):
    """Levée lorsqu'un lecteur ayant un prêt en retard tente d'emprunter."""

    def __init__(self, lecteur, nb_retards):
        """Construit le message à partir du lecteur et des retards."""
        super().__init__(
            f"{lecteur.nom_complet} a {nb_retards} emprunt(s) en retard : "
            "nouvel emprunt refusé tant qu'ils ne sont pas rendus."
        )
        self.lecteur = lecteur
        self.nb_retards = nb_retards


class EmpruntDejaEnCours(BibliothequeErreur):
    """Levée lorsqu'un lecteur emprunte un ouvrage qu'il détient déjà."""


class ProlongationRefusee(BibliothequeErreur):
    """Levée lorsqu'une prolongation n'est pas autorisée."""


class EmpruntDejaCloture(BibliothequeErreur):
    """Levée lorsqu'on agit sur un emprunt déjà rendu."""


class OperationImpossible(BibliothequeErreur):
    """Levée lorsqu'une opération violerait la cohérence des données.

    Exemple : supprimer un ouvrage dont un exemplaire est encore emprunté.
    """


class ErreurPersistance(BibliothequeErreur):
    """Levée lorsqu'un fichier de données ne peut être lu ou écrit."""
