"""Modèle d'un exemplaire physique d'un ouvrage."""


class Exemplaire:
    """Copie physique d'un ouvrage, prêtable individuellement.

    Attributes:
        id_exemplaire: identifiant unique (ex. ``OUV-0001-E02``).
        id_ouvrage: identifiant de l'ouvrage dont il est une copie.
        disponible: ``True`` s'il est en rayon, ``False`` s'il est prêté.
    """

    def __init__(self, id_exemplaire, id_ouvrage, disponible=True):
        """Initialise un exemplaire, disponible par défaut."""
        self.id_exemplaire = id_exemplaire
        self.id_ouvrage = id_ouvrage
        self.disponible = bool(disponible)

    def marquer_emprunte(self):
        """Retire l'exemplaire du rayon lors d'un emprunt."""
        self.disponible = False

    def marquer_rendu(self):
        """Remet l'exemplaire en rayon lors d'un retour."""
        self.disponible = True

    def to_dict(self):
        """Retourne une représentation sérialisable en JSON."""
        return {
            "id_exemplaire": self.id_exemplaire,
            "id_ouvrage": self.id_ouvrage,
            "disponible": self.disponible,
        }

    @classmethod
    def from_dict(cls, donnees):
        """Reconstruit un exemplaire à partir de :meth:`to_dict`."""
        return cls(
            donnees["id_exemplaire"],
            donnees["id_ouvrage"],
            donnees.get("disponible", True),
        )

    def __repr__(self):
        """Représentation de débogage."""
        etat = "disponible" if self.disponible else "emprunté"
        return f"Exemplaire({self.id_exemplaire!r}, {etat})"
