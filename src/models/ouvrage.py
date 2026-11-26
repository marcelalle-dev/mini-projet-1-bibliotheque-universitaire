"""Modèle d'un ouvrage (notice bibliographique) et de ses exemplaires."""

from src.exceptions import ExemplaireIntrouvable, OperationImpossible
from src.models.exemplaire import Exemplaire
from src.models.validation import normaliser_isbn, texte_obligatoire


class Ouvrage:
    """Notice bibliographique regroupant un ou plusieurs exemplaires.

    Un ouvrage décrit *ce qu'est* le livre (titre, auteur, ISBN, catégorie) ;
    ses :class:`Exemplaire` sont les copies physiques effectivement prêtées.
    """

    def __init__(self, id_ouvrage, titre, auteur, isbn, categorie,
                 exemplaires=None, dernier_numero=0):
        """Initialise un ouvrage après validation des champs.

        Args:
            exemplaires: exemplaires existants (rechargement JSON).
            dernier_numero: plus grand numéro d'exemplaire déjà attribué,
                pour ne jamais réattribuer l'identifiant d'une copie retirée.

        Raises:
            DonneesInvalides: si un champ est vide ou l'ISBN incorrect.
        """
        self.id_ouvrage = id_ouvrage
        self.titre = texte_obligatoire(titre, "titre")
        self.auteur = texte_obligatoire(auteur, "auteur")
        self.isbn = normaliser_isbn(isbn)
        self.categorie = texte_obligatoire(categorie, "catégorie")
        self.exemplaires = list(exemplaires or [])
        self.dernier_numero = max(
            [dernier_numero] + [self._numero(e) for e in self.exemplaires]
        )

    # ------------------------------------------------------------------
    # Exemplaires
    # ------------------------------------------------------------------
    def ajouter_exemplaires(self, nombre=1):
        """Crée ``nombre`` nouveaux exemplaires et les retourne.

        Les identifiants sont de la forme ``<id_ouvrage>-E<numéro>`` et ne
        sont jamais réutilisés, même après suppression d'un exemplaire.
        """
        if not isinstance(nombre, int) or nombre < 1:
            raise OperationImpossible(
                "Le nombre d'exemplaires à ajouter doit être >= 1."
            )
        debut = self.dernier_numero + 1
        nouveaux = [
            Exemplaire(f"{self.id_ouvrage}-E{numero:02d}", self.id_ouvrage)
            for numero in range(debut, debut + nombre)
        ]
        self.dernier_numero += nombre
        self.exemplaires.extend(nouveaux)
        return nouveaux

    def retirer_exemplaire(self, id_exemplaire):
        """Supprime un exemplaire disponible (perte, usure...).

        Raises:
            ExemplaireIntrouvable: si l'exemplaire n'appartient pas à
                l'ouvrage.
            OperationImpossible: si l'exemplaire est actuellement prêté.
        """
        exemplaire = self.trouver_exemplaire(id_exemplaire)
        if not exemplaire.disponible:
            raise OperationImpossible(
                f"L'exemplaire {id_exemplaire} est emprunté : "
                "il doit être rendu avant d'être retiré."
            )
        self.exemplaires.remove(exemplaire)
        return exemplaire

    def trouver_exemplaire(self, id_exemplaire):
        """Retourne l'exemplaire d'identifiant donné.

        Raises:
            ExemplaireIntrouvable: si aucun exemplaire ne correspond.
        """
        for exemplaire in self.exemplaires:
            if exemplaire.id_exemplaire == id_exemplaire:
                return exemplaire
        raise ExemplaireIntrouvable(id_exemplaire)

    def exemplaires_disponibles(self):
        """Retourne la liste des exemplaires actuellement en rayon."""
        return [e for e in self.exemplaires if e.disponible]

    def premier_exemplaire_disponible(self):
        """Retourne un exemplaire disponible, ou ``None`` s'il n'y en a pas."""
        disponibles = self.exemplaires_disponibles()
        return disponibles[0] if disponibles else None

    @property
    def nb_exemplaires(self):
        """Nombre total d'exemplaires possédés."""
        return len(self.exemplaires)

    @property
    def nb_disponibles(self):
        """Nombre d'exemplaires actuellement disponibles."""
        return len(self.exemplaires_disponibles())

    @property
    def nb_empruntes(self):
        """Nombre d'exemplaires actuellement prêtés."""
        return self.nb_exemplaires - self.nb_disponibles

    def est_disponible(self):
        """Indique si au moins un exemplaire peut être emprunté."""
        return self.nb_disponibles > 0

    # ------------------------------------------------------------------
    # Modification et recherche
    # ------------------------------------------------------------------
    def modifier(self, titre=None, auteur=None, isbn=None, categorie=None):
        """Met à jour les champs fournis (``None`` = champ inchangé).

        La validation est faite avant toute affectation : en cas d'erreur
        l'ouvrage reste dans son état initial.
        """
        nouveau_titre = (texte_obligatoire(titre, "titre")
                         if titre is not None else self.titre)
        nouvel_auteur = (texte_obligatoire(auteur, "auteur")
                         if auteur is not None else self.auteur)
        nouvel_isbn = normaliser_isbn(isbn) if isbn is not None else self.isbn
        nouvelle_categorie = (texte_obligatoire(categorie, "catégorie")
                              if categorie is not None else self.categorie)
        self.titre = nouveau_titre
        self.auteur = nouvel_auteur
        self.isbn = nouvel_isbn
        self.categorie = nouvelle_categorie

    def correspond(self, champ, terme):
        """Indique si ``terme`` apparaît dans ``champ`` (sans casse).

        Pour l'ISBN la comparaison se fait sur le code normalisé exact
        (tirets et espaces ignorés).
        """
        if champ == "isbn":
            code = terme.replace("-", "").replace(" ", "").upper()
            return code == self.isbn
        valeur = getattr(self, champ)
        return terme.casefold().strip() in valeur.casefold()

    # ------------------------------------------------------------------
    # Sérialisation
    # ------------------------------------------------------------------
    def to_dict(self):
        """Retourne une représentation sérialisable en JSON."""
        return {
            "id_ouvrage": self.id_ouvrage,
            "titre": self.titre,
            "auteur": self.auteur,
            "isbn": self.isbn,
            "categorie": self.categorie,
            "exemplaires": [e.to_dict() for e in self.exemplaires],
            "dernier_numero": self.dernier_numero,
        }

    @classmethod
    def from_dict(cls, donnees):
        """Reconstruit un ouvrage (et ses exemplaires) depuis un dict."""
        return cls(
            donnees["id_ouvrage"],
            donnees["titre"],
            donnees["auteur"],
            donnees["isbn"],
            donnees["categorie"],
            [Exemplaire.from_dict(e) for e in donnees.get("exemplaires", [])],
            donnees.get("dernier_numero", 0),
        )

    @staticmethod
    def _numero(exemplaire):
        """Extrait le numéro séquentiel d'un identifiant d'exemplaire."""
        suffixe = exemplaire.id_exemplaire.rsplit("-E", 1)[-1]
        return int(suffixe) if suffixe.isdigit() else 0

    def __str__(self):
        """Résumé lisible pour l'affichage console."""
        return (f"[{self.id_ouvrage}] {self.titre} — {self.auteur} "
                f"({self.categorie}, ISBN {self.isbn}) "
                f"{self.nb_disponibles}/{self.nb_exemplaires} disponible(s)")
