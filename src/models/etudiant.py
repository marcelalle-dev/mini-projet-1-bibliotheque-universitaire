"""Lecteur de type étudiant : 3 emprunts simultanés, 14 jours."""

from src.models.lecteur import Lecteur


class Etudiant(Lecteur):
    """Étudiant inscrit à la bibliothèque.

    Attributes:
        filiere: filière ou parcours suivi (facultatif).
        niveau: niveau d'études, ex. ``L2`` ou ``M1`` (facultatif).
    """

    TYPE = "etudiant"
    QUOTA_MAX = 3
    DUREE_EMPRUNT = 14

    def __init__(self, id_lecteur, nom, prenom, email="", filiere="",
                 niveau="", emprunts_actifs=None):
        """Initialise un étudiant."""
        super().__init__(id_lecteur, nom, prenom, email, emprunts_actifs)
        self.filiere = (filiere or "").strip()
        self.niveau = (niveau or "").strip().upper()

    @property
    def quota_max(self):
        """Un étudiant peut détenir 3 ouvrages simultanément."""
        return self.QUOTA_MAX

    @property
    def duree_emprunt(self):
        """Un étudiant dispose de 14 jours par emprunt."""
        return self.DUREE_EMPRUNT

    @property
    def type_lecteur(self):
        """Libellé affiché pour ce type de lecteur."""
        return "Étudiant"

    def _attributs_specifiques(self):
        """Attributs propres aux étudiants."""
        return {"filiere": self.filiere, "niveau": self.niveau}

    @classmethod
    def _depuis_dict(cls, donnees):
        """Construit un étudiant depuis sa représentation JSON."""
        return cls(
            donnees["id_lecteur"], donnees["nom"], donnees["prenom"],
            donnees.get("email", ""), donnees.get("filiere", ""),
            donnees.get("niveau", ""), donnees.get("emprunts_actifs", []),
        )
