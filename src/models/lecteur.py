"""Classe abstraite représentant un lecteur de la bibliothèque."""

from abc import ABC, abstractmethod
from datetime import timedelta

from src.models.validation import texte_obligatoire


class Lecteur(ABC):
    """Lecteur inscrit à la bibliothèque (classe abstraite).

    Les règles de prêt (quota, durée) dépendent du type de lecteur et sont
    définies par les sous-classes via les propriétés abstraites
    :attr:`quota_max`, :attr:`duree_emprunt` et :attr:`type_lecteur`.

    Attributes:
        id_lecteur: identifiant unique (ex. ``LEC-0001``).
        nom, prenom: identité du lecteur.
        email: adresse de contact (facultative).
        emprunts_actifs: identifiants des emprunts non rendus.
    """

    #: Registre ``type_lecteur -> sous-classe`` rempli automatiquement.
    _types = {}

    def __init_subclass__(cls, **kwargs):
        """Enregistre chaque sous-classe concrète pour la désérialisation."""
        super().__init_subclass__(**kwargs)
        cle = getattr(cls, "TYPE", None)
        if cle:
            Lecteur._types[cle] = cls

    def __init__(self, id_lecteur, nom, prenom, email="",
                 emprunts_actifs=None):
        """Initialise les attributs communs à tous les lecteurs."""
        self.id_lecteur = id_lecteur
        self.nom = texte_obligatoire(nom, "nom").upper()
        self.prenom = texte_obligatoire(prenom, "prénom").title()
        self.email = (email or "").strip()
        self.emprunts_actifs = list(emprunts_actifs or [])

    # ------------------------------------------------------------------
    # Règles propres à chaque type de lecteur
    # ------------------------------------------------------------------
    @property
    @abstractmethod
    def quota_max(self):
        """Nombre maximal d'emprunts simultanés."""

    @property
    @abstractmethod
    def duree_emprunt(self):
        """Durée d'un emprunt (et d'une prolongation), en jours."""

    @property
    @abstractmethod
    def type_lecteur(self):
        """Libellé du type de lecteur (``Étudiant``, ``Enseignant``...)."""

    @abstractmethod
    def _attributs_specifiques(self):
        """Retourne les attributs propres à la sous-classe (dict)."""

    # ------------------------------------------------------------------
    # Comportement commun
    # ------------------------------------------------------------------
    @property
    def nom_complet(self):
        """Prénom et nom du lecteur."""
        return f"{self.prenom} {self.nom}"

    @property
    def nb_emprunts_actifs(self):
        """Nombre d'ouvrages actuellement détenus."""
        return len(self.emprunts_actifs)

    def peut_emprunter(self):
        """Indique si le quota autorise un nouvel emprunt."""
        return self.nb_emprunts_actifs < self.quota_max

    def calculer_date_retour(self, date_debut):
        """Retourne la date de retour prévue pour un prêt débutant le jour
        ``date_debut``, selon la durée propre au type de lecteur."""
        return date_debut + timedelta(days=self.duree_emprunt)

    def enregistrer_emprunt(self, id_emprunt):
        """Ajoute un emprunt à la liste des emprunts en cours."""
        if id_emprunt not in self.emprunts_actifs:
            self.emprunts_actifs.append(id_emprunt)

    def liberer_emprunt(self, id_emprunt):
        """Retire un emprunt rendu de la liste des emprunts en cours."""
        if id_emprunt in self.emprunts_actifs:
            self.emprunts_actifs.remove(id_emprunt)

    def modifier(self, nom=None, prenom=None, email=None):
        """Met à jour l'identité du lecteur (``None`` = inchangé)."""
        nouveau_nom = (texte_obligatoire(nom, "nom").upper()
                       if nom is not None else self.nom)
        nouveau_prenom = (texte_obligatoire(prenom, "prénom").title()
                          if prenom is not None else self.prenom)
        self.nom = nouveau_nom
        self.prenom = nouveau_prenom
        if email is not None:
            self.email = email.strip()

    # ------------------------------------------------------------------
    # Sérialisation polymorphe
    # ------------------------------------------------------------------
    def to_dict(self):
        """Retourne une représentation JSON incluant le type de lecteur."""
        donnees = {
            "type": self.TYPE,
            "id_lecteur": self.id_lecteur,
            "nom": self.nom,
            "prenom": self.prenom,
            "email": self.email,
            "emprunts_actifs": list(self.emprunts_actifs),
        }
        donnees.update(self._attributs_specifiques())
        return donnees

    @staticmethod
    def from_dict(donnees):
        """Instancie la bonne sous-classe selon le champ ``type``.

        Raises:
            KeyError: si le type de lecteur est inconnu.
        """
        type_lecteur = donnees["type"]
        if type_lecteur not in Lecteur._types:
            raise KeyError(f"Type de lecteur inconnu : {type_lecteur!r}")
        return Lecteur._types[type_lecteur]._depuis_dict(donnees)

    @classmethod
    @abstractmethod
    def _depuis_dict(cls, donnees):
        """Construit une instance de la sous-classe depuis un dict."""

    def __str__(self):
        """Résumé lisible pour l'affichage console."""
        return (f"[{self.id_lecteur}] {self.nom_complet} — "
                f"{self.type_lecteur} "
                f"({self.nb_emprunts_actifs}/{self.quota_max} emprunts)")
