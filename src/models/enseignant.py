"""Lecteur de type enseignant : 5 emprunts simultanés, 30 jours."""

from src.models.lecteur import Lecteur


class Enseignant(Lecteur):
    """Enseignant inscrit à la bibliothèque.

    Attributes:
        departement: département de rattachement (facultatif).
        grade: grade universitaire, ex. ``Maître de conférences``.
    """

    TYPE = "enseignant"
    QUOTA_MAX = 5
    DUREE_EMPRUNT = 30

    def __init__(self, id_lecteur, nom, prenom, email="", departement="",
                 grade="", emprunts_actifs=None):
        """Initialise un enseignant."""
        super().__init__(id_lecteur, nom, prenom, email, emprunts_actifs)
        self.departement = (departement or "").strip()
        self.grade = (grade or "").strip()

    @property
    def quota_max(self):
        """Un enseignant peut détenir 5 ouvrages simultanément."""
        return self.QUOTA_MAX

    @property
    def duree_emprunt(self):
        """Un enseignant dispose de 30 jours par emprunt."""
        return self.DUREE_EMPRUNT

    @property
    def type_lecteur(self):
        """Libellé affiché pour ce type de lecteur."""
        return "Enseignant"

    def _attributs_specifiques(self):
        """Attributs propres aux enseignants."""
        return {"departement": self.departement, "grade": self.grade}

    @classmethod
    def _depuis_dict(cls, donnees):
        """Construit un enseignant depuis sa représentation JSON."""
        return cls(
            donnees["id_lecteur"], donnees["nom"], donnees["prenom"],
            donnees.get("email", ""), donnees.get("departement", ""),
            donnees.get("grade", ""), donnees.get("emprunts_actifs", []),
        )
