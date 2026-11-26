"""Modèle d'un emprunt : prêt d'un exemplaire à un lecteur."""

from datetime import date, timedelta

from src.exceptions import EmpruntDejaCloture, ProlongationRefusee


class Emprunt:
    """Prêt d'un exemplaire, de sa création à son retour.

    Un emprunt rendu n'est jamais supprimé : il constitue l'historique
    utilisé par le tableau de bord (ouvrages les plus empruntés).

    Attributes:
        PENALITE_PAR_JOUR: montant de la pénalité, en FCFA par jour de retard.
    """

    PENALITE_PAR_JOUR = 100
    FORMAT_DATE = "%Y-%m-%d"

    def __init__(self, id_emprunt, id_lecteur, id_ouvrage, id_exemplaire,
                 date_emprunt, date_retour_prevue, date_retour_effective=None,
                 prolonge=False, penalite_payee=0):
        """Initialise un emprunt.

        Args:
            date_emprunt: date de début du prêt.
            date_retour_prevue: date limite de retour (incluse).
            date_retour_effective: date du retour, ``None`` si non rendu.
            prolonge: ``True`` si la prolongation unique a été utilisée.
            penalite_payee: pénalité calculée au moment du retour (FCFA).
        """
        if date_retour_prevue < date_emprunt:
            raise ValueError("La date de retour précède la date d'emprunt.")
        self.id_emprunt = id_emprunt
        self.id_lecteur = id_lecteur
        self.id_ouvrage = id_ouvrage
        self.id_exemplaire = id_exemplaire
        self.date_emprunt = date_emprunt
        self.date_retour_prevue = date_retour_prevue
        self.date_retour_effective = date_retour_effective
        self.prolonge = bool(prolonge)
        self.penalite_payee = int(penalite_payee)

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------
    @property
    def est_actif(self):
        """``True`` tant que l'exemplaire n'a pas été rendu."""
        return self.date_retour_effective is None

    def jours_retard(self, date_reference=None):
        """Nombre de jours de retard à ``date_reference`` (aujourd'hui par
        défaut). Pour un emprunt rendu, le retard est figé à la date du
        retour effectif. Le jour limite lui-même n'est pas en retard."""
        if not self.est_actif:
            reference = self.date_retour_effective
        else:
            reference = date_reference or date.today()
        return max(0, (reference - self.date_retour_prevue).days)

    def est_en_retard(self, date_reference=None):
        """Indique si l'emprunt (en cours) a dépassé sa date limite."""
        return self.est_actif and self.jours_retard(date_reference) > 0

    def calculer_penalite(self, date_reference=None):
        """Pénalité en FCFA : 100 FCFA par jour de retard."""
        return self.jours_retard(date_reference) * self.PENALITE_PAR_JOUR

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------
    def prolonger(self, nb_jours, date_reference=None):
        """Repousse la date limite de ``nb_jours`` (une seule fois).

        Raises:
            EmpruntDejaCloture: si l'emprunt est déjà rendu.
            ProlongationRefusee: si l'emprunt a déjà été prolongé ou s'il
                est en retard à ``date_reference``.
        """
        if not self.est_actif:
            raise EmpruntDejaCloture(
                f"L'emprunt {self.id_emprunt} est déjà rendu."
            )
        if self.prolonge:
            raise ProlongationRefusee(
                f"L'emprunt {self.id_emprunt} a déjà été prolongé une fois."
            )
        if self.est_en_retard(date_reference):
            raise ProlongationRefusee(
                f"L'emprunt {self.id_emprunt} est en retard de "
                f"{self.jours_retard(date_reference)} jour(s) : "
                "prolongation impossible."
            )
        self.date_retour_prevue += timedelta(days=nb_jours)
        self.prolonge = True
        return self.date_retour_prevue

    def cloturer(self, date_retour=None):
        """Enregistre le retour et retourne la pénalité due (FCFA).

        Raises:
            EmpruntDejaCloture: si l'emprunt est déjà rendu.
            ValueError: si la date de retour précède la date d'emprunt.
        """
        if not self.est_actif:
            raise EmpruntDejaCloture(
                f"L'emprunt {self.id_emprunt} est déjà rendu."
            )
        date_retour = date_retour or date.today()
        if date_retour < self.date_emprunt:
            raise ValueError("La date de retour précède la date d'emprunt.")
        self.date_retour_effective = date_retour
        self.penalite_payee = self.calculer_penalite()
        return self.penalite_payee

    # ------------------------------------------------------------------
    # Sérialisation
    # ------------------------------------------------------------------
    def to_dict(self):
        """Retourne une représentation JSON (dates au format ISO 8601)."""
        return {
            "id_emprunt": self.id_emprunt,
            "id_lecteur": self.id_lecteur,
            "id_ouvrage": self.id_ouvrage,
            "id_exemplaire": self.id_exemplaire,
            "date_emprunt": self.date_emprunt.isoformat(),
            "date_retour_prevue": self.date_retour_prevue.isoformat(),
            "date_retour_effective": (
                self.date_retour_effective.isoformat()
                if self.date_retour_effective else None
            ),
            "prolonge": self.prolonge,
            "penalite_payee": self.penalite_payee,
        }

    @classmethod
    def from_dict(cls, donnees):
        """Reconstruit un emprunt depuis :meth:`to_dict`."""
        retour = donnees.get("date_retour_effective")
        return cls(
            donnees["id_emprunt"],
            donnees["id_lecteur"],
            donnees["id_ouvrage"],
            donnees["id_exemplaire"],
            date.fromisoformat(donnees["date_emprunt"]),
            date.fromisoformat(donnees["date_retour_prevue"]),
            date.fromisoformat(retour) if retour else None,
            donnees.get("prolonge", False),
            donnees.get("penalite_payee", 0),
        )

    def __str__(self):
        """Résumé lisible pour l'affichage console."""
        if self.est_actif:
            etat = f"à rendre le {self.date_retour_prevue:%d/%m/%Y}"
        else:
            etat = f"rendu le {self.date_retour_effective:%d/%m/%Y}"
        prolongation = ", prolongé" if self.prolonge else ""
        return (f"[{self.id_emprunt}] {self.id_exemplaire} → "
                f"{self.id_lecteur}, emprunté le "
                f"{self.date_emprunt:%d/%m/%Y}, {etat}{prolongation}")
