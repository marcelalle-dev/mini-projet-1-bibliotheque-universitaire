"""Service central : catalogue des ouvrages, lecteurs et registre des prêts.

La classe :class:`Bibliotheque` détient l'état de l'application (ouvrages,
lecteurs, emprunts et compteurs d'identifiants). Les autres services
(:mod:`gestionnaire_emprunts`, :mod:`tableau_bord`) et la persistance
travaillent sur une instance de cette classe.
"""

from src.exceptions import (
    DoublonErreur,
    DonneesInvalides,
    EmpruntIntrouvable,
    LecteurIntrouvable,
    OperationImpossible,
    OuvrageIntrouvable,
)
from src.models import Enseignant, Etudiant, Ouvrage
from src.models.validation import normaliser_isbn

#: Champs autorisés pour la recherche d'ouvrages.
CHAMPS_RECHERCHE = ("titre", "auteur", "categorie", "isbn")


class Bibliotheque:
    """Catalogue d'ouvrages, fichier des lecteurs et registre des emprunts.

    Attributes:
        ouvrages: dictionnaire ``id_ouvrage -> Ouvrage``.
        lecteurs: dictionnaire ``id_lecteur -> Lecteur``.
        emprunts: dictionnaire ``id_emprunt -> Emprunt`` (historique
            complet, emprunts rendus compris).
        compteurs: dernier numéro attribué pour chaque type d'identifiant.
    """

    PREFIXES = {"ouvrage": "OUV", "lecteur": "LEC", "emprunt": "EMP"}

    def __init__(self):
        """Crée une bibliothèque vide."""
        self.ouvrages = {}
        self.lecteurs = {}
        self.emprunts = {}
        self.compteurs = {cle: 0 for cle in self.PREFIXES}

    # ------------------------------------------------------------------
    # Identifiants
    # ------------------------------------------------------------------
    def nouvel_identifiant(self, type_objet):
        """Génère un identifiant unique et croissant (ex. ``OUV-0007``).

        Les compteurs sont sauvegardés : un identifiant supprimé n'est
        jamais réattribué, même après redémarrage.
        """
        self.compteurs[type_objet] += 1
        return f"{self.PREFIXES[type_objet]}-{self.compteurs[type_objet]:04d}"

    @staticmethod
    def normaliser_identifiant(identifiant):
        """Met un identifiant saisi au format canonique (majuscules)."""
        return (identifiant or "").strip().upper()

    # ------------------------------------------------------------------
    # Ouvrages
    # ------------------------------------------------------------------
    def ajouter_ouvrage(self, titre, auteur, isbn, categorie,
                        nb_exemplaires=1):
        """Ajoute un ouvrage avec ``nb_exemplaires`` copies et le retourne.

        Raises:
            DonneesInvalides: champ vide, ISBN invalide ou nombre
                d'exemplaires < 1.
            DoublonErreur: si un ouvrage possède déjà cet ISBN.
        """
        if not isinstance(nb_exemplaires, int) or nb_exemplaires < 1:
            raise DonneesInvalides("Il faut au moins un exemplaire.")
        self._verifier_isbn_unique(normaliser_isbn(isbn))
        # L'ouvrage est validé avant de consommer un identifiant.
        ouvrage = Ouvrage("OUV-TEMP", titre, auteur, isbn, categorie)
        ouvrage.id_ouvrage = self.nouvel_identifiant("ouvrage")
        ouvrage.ajouter_exemplaires(nb_exemplaires)
        self.ouvrages[ouvrage.id_ouvrage] = ouvrage
        return ouvrage

    def obtenir_ouvrage(self, id_ouvrage):
        """Retourne l'ouvrage demandé.

        Raises:
            OuvrageIntrouvable: si l'identifiant est inconnu.
        """
        cle = self.normaliser_identifiant(id_ouvrage)
        if cle not in self.ouvrages:
            raise OuvrageIntrouvable(id_ouvrage)
        return self.ouvrages[cle]

    def modifier_ouvrage(self, id_ouvrage, titre=None, auteur=None,
                         isbn=None, categorie=None):
        """Modifie les champs fournis d'un ouvrage et le retourne.

        Raises:
            OuvrageIntrouvable: identifiant inconnu.
            DonneesInvalides: nouvelle valeur incorrecte.
            DoublonErreur: nouvel ISBN déjà utilisé par un autre ouvrage.
        """
        ouvrage = self.obtenir_ouvrage(id_ouvrage)
        if isbn is not None:
            self._verifier_isbn_unique(normaliser_isbn(isbn),
                                       sauf=ouvrage.id_ouvrage)
        ouvrage.modifier(titre, auteur, isbn, categorie)
        return ouvrage

    def supprimer_ouvrage(self, id_ouvrage):
        """Supprime un ouvrage et tous ses exemplaires.

        L'historique des emprunts passés est conservé.

        Raises:
            OuvrageIntrouvable: identifiant inconnu.
            OperationImpossible: si un exemplaire est encore emprunté.
        """
        ouvrage = self.obtenir_ouvrage(id_ouvrage)
        if ouvrage.nb_empruntes:
            raise OperationImpossible(
                f"{ouvrage.nb_empruntes} exemplaire(s) de « {ouvrage.titre} »"
                " sont encore empruntés : suppression impossible."
            )
        return self.ouvrages.pop(ouvrage.id_ouvrage)

    def ajouter_exemplaires(self, id_ouvrage, nombre):
        """Ajoute ``nombre`` exemplaires à un ouvrage et les retourne."""
        return self.obtenir_ouvrage(id_ouvrage).ajouter_exemplaires(nombre)

    def retirer_exemplaire(self, id_ouvrage, id_exemplaire):
        """Retire un exemplaire disponible d'un ouvrage."""
        ouvrage = self.obtenir_ouvrage(id_ouvrage)
        if ouvrage.nb_exemplaires == 1:
            raise OperationImpossible(
                "C'est le dernier exemplaire : supprimez plutôt l'ouvrage."
            )
        return ouvrage.retirer_exemplaire(
            self.normaliser_identifiant(id_exemplaire)
        )

    def rechercher(self, champ, terme):
        """Recherche des ouvrages par ``titre``, ``auteur``, ``categorie``
        ou ``isbn``.

        La recherche textuelle est partielle et insensible à la casse ;
        la recherche par ISBN est exacte. Résultats triés par titre.

        Raises:
            DonneesInvalides: champ inconnu ou terme vide.
        """
        if champ not in CHAMPS_RECHERCHE:
            raise DonneesInvalides(f"Critère de recherche inconnu : {champ}")
        if not terme or not terme.strip():
            raise DonneesInvalides("Le terme recherché est vide.")
        resultats = [o for o in self.ouvrages.values()
                     if o.correspond(champ, terme)]
        return sorted(resultats, key=lambda o: o.titre.casefold())

    def rechercher_par_titre(self, terme):
        """Ouvrages dont le titre contient ``terme``."""
        return self.rechercher("titre", terme)

    def rechercher_par_auteur(self, terme):
        """Ouvrages dont l'auteur contient ``terme``."""
        return self.rechercher("auteur", terme)

    def rechercher_par_categorie(self, terme):
        """Ouvrages dont la catégorie contient ``terme``."""
        return self.rechercher("categorie", terme)

    def rechercher_par_isbn(self, isbn):
        """Ouvrages dont l'ISBN est exactement ``isbn``."""
        return self.rechercher("isbn", isbn)

    def lister_ouvrages(self):
        """Retourne tous les ouvrages, triés par identifiant."""
        return [self.ouvrages[cle] for cle in sorted(self.ouvrages)]

    def categories(self):
        """Retourne la liste triée des catégories existantes."""
        return sorted({o.categorie for o in self.ouvrages.values()},
                      key=str.casefold)

    def _verifier_isbn_unique(self, isbn, sauf=None):
        """Lève :class:`DoublonErreur` si l'ISBN est déjà utilisé."""
        for ouvrage in self.ouvrages.values():
            if ouvrage.isbn == isbn and ouvrage.id_ouvrage != sauf:
                raise DoublonErreur(
                    f"L'ISBN {isbn} est déjà attribué à "
                    f"{ouvrage.id_ouvrage} (« {ouvrage.titre} »). "
                    "Ajoutez plutôt des exemplaires à cet ouvrage."
                )

    # ------------------------------------------------------------------
    # Lecteurs
    # ------------------------------------------------------------------
    def inscrire_etudiant(self, nom, prenom, email="", filiere="",
                          niveau=""):
        """Inscrit un nouvel étudiant et le retourne."""
        etudiant = Etudiant("LEC-TEMP", nom, prenom, email, filiere, niveau)
        return self._enregistrer_lecteur(etudiant)

    def inscrire_enseignant(self, nom, prenom, email="", departement="",
                            grade=""):
        """Inscrit un nouvel enseignant et le retourne."""
        enseignant = Enseignant("LEC-TEMP", nom, prenom, email,
                                departement, grade)
        return self._enregistrer_lecteur(enseignant)

    def _enregistrer_lecteur(self, lecteur):
        """Attribue un identifiant au lecteur validé et l'enregistre."""
        lecteur.id_lecteur = self.nouvel_identifiant("lecteur")
        self.lecteurs[lecteur.id_lecteur] = lecteur
        return lecteur

    def obtenir_lecteur(self, id_lecteur):
        """Retourne le lecteur demandé.

        Raises:
            LecteurIntrouvable: si l'identifiant est inconnu.
        """
        cle = self.normaliser_identifiant(id_lecteur)
        if cle not in self.lecteurs:
            raise LecteurIntrouvable(id_lecteur)
        return self.lecteurs[cle]

    def modifier_lecteur(self, id_lecteur, nom=None, prenom=None,
                         email=None):
        """Modifie l'identité d'un lecteur et le retourne."""
        lecteur = self.obtenir_lecteur(id_lecteur)
        lecteur.modifier(nom, prenom, email)
        return lecteur

    def supprimer_lecteur(self, id_lecteur):
        """Supprime un lecteur n'ayant aucun emprunt en cours.

        Raises:
            LecteurIntrouvable: identifiant inconnu.
            OperationImpossible: le lecteur détient encore des ouvrages.
        """
        lecteur = self.obtenir_lecteur(id_lecteur)
        if lecteur.nb_emprunts_actifs:
            raise OperationImpossible(
                f"{lecteur.nom_complet} a encore "
                f"{lecteur.nb_emprunts_actifs} emprunt(s) en cours."
            )
        return self.lecteurs.pop(lecteur.id_lecteur)

    def lister_lecteurs(self, type_lecteur=None):
        """Retourne les lecteurs triés par identifiant.

        Args:
            type_lecteur: ``"etudiant"``, ``"enseignant"`` ou ``None``
                pour tous les lecteurs.
        """
        return [self.lecteurs[cle] for cle in sorted(self.lecteurs)
                if type_lecteur is None
                or self.lecteurs[cle].TYPE == type_lecteur]

    def rechercher_lecteurs(self, terme):
        """Lecteurs dont le nom ou le prénom contient ``terme``."""
        terme = (terme or "").casefold().strip()
        return [lecteur for lecteur in self.lister_lecteurs()
                if terme in lecteur.nom_complet.casefold()]

    # ------------------------------------------------------------------
    # Emprunts (registre)
    # ------------------------------------------------------------------
    def obtenir_emprunt(self, id_emprunt):
        """Retourne l'emprunt demandé.

        Raises:
            EmpruntIntrouvable: si l'identifiant est inconnu.
        """
        cle = self.normaliser_identifiant(id_emprunt)
        if cle not in self.emprunts:
            raise EmpruntIntrouvable(id_emprunt)
        return self.emprunts[cle]

    def libelle_ouvrage(self, id_ouvrage):
        """Titre d'un ouvrage, même s'il a été supprimé du catalogue."""
        ouvrage = self.ouvrages.get(id_ouvrage)
        return ouvrage.titre if ouvrage else f"{id_ouvrage} (supprimé)"

    def libelle_lecteur(self, id_lecteur):
        """Nom d'un lecteur, même s'il a été supprimé."""
        lecteur = self.lecteurs.get(id_lecteur)
        return lecteur.nom_complet if lecteur else f"{id_lecteur} (supprimé)"

    # ------------------------------------------------------------------
    # Cohérence
    # ------------------------------------------------------------------
    def reconstruire_index(self):
        """Recalcule les états dérivés à partir des emprunts actifs.

        La disponibilité des exemplaires et la liste des emprunts en cours
        de chaque lecteur sont déduites des emprunts non rendus, qui font
        foi. Retourne le nombre de corrections effectuées.
        """
        corrections = 0
        actifs = [e for e in self.emprunts.values() if e.est_actif]
        empruntes = {e.id_exemplaire for e in actifs}
        for ouvrage in self.ouvrages.values():
            for exemplaire in ouvrage.exemplaires:
                attendu = exemplaire.id_exemplaire not in empruntes
                if exemplaire.disponible != attendu:
                    exemplaire.disponible = attendu
                    corrections += 1
        for lecteur in self.lecteurs.values():
            attendus = sorted(e.id_emprunt for e in actifs
                              if e.id_lecteur == lecteur.id_lecteur)
            if sorted(lecteur.emprunts_actifs) != attendus:
                lecteur.emprunts_actifs = attendus
                corrections += 1
        return corrections
