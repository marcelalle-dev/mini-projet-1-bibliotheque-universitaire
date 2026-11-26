"""Sauvegarde et chargement de la bibliothèque au format JSON.

Trois fichiers sont utilisés dans le dossier de données :

* ``ouvrages.json`` — ouvrages et exemplaires ;
* ``lecteurs.json`` — étudiants et enseignants ;
* ``emprunts.json`` — historique complet des emprunts.

Chaque fichier contient un en-tête ``{"version", "compteur", ...}`` afin de
conserver les compteurs d'identifiants entre deux exécutions.

Protection contre les pertes de données :

* écriture atomique (fichier ``.tmp`` puis :func:`os.replace`) : un arrêt
  brutal pendant l'écriture ne laisse jamais un fichier à moitié écrit ;
* copie ``.bak`` de la version précédente avant chaque écrasement ;
* un fichier corrompu est mis de côté (``.corrompu-<horodatage>``) au lieu
  d'être écrasé, et la sauvegarde ``.bak`` est utilisée si elle est valide.
"""

import json
import os
import shutil
from datetime import datetime

from src.exceptions import DonneesInvalides, ErreurPersistance
from src.models import Emprunt, Lecteur, Ouvrage
from src.services import Bibliotheque

VERSION_FORMAT = 1

#: ``type d'objet -> (fichier, clé de la liste, classe, attribut id)``
FICHIERS = {
    "ouvrage": ("ouvrages.json", "ouvrages", Ouvrage, "id_ouvrage"),
    "lecteur": ("lecteurs.json", "lecteurs", Lecteur, "id_lecteur"),
    "emprunt": ("emprunts.json", "emprunts", Emprunt, "id_emprunt"),
}


class GestionnaireJSON:
    """Lit et écrit l'état d'une :class:`Bibliotheque` dans un dossier.

    Attributes:
        dossier: chemin du dossier contenant les fichiers JSON.
        avertissements: messages produits lors du dernier chargement
            (fichier absent, corrompu, restauré...).
    """

    def __init__(self, dossier):
        """Associe le gestionnaire à un dossier de données."""
        self.dossier = dossier
        self.avertissements = []

    def chemin(self, type_objet):
        """Chemin complet du fichier JSON d'un type d'objet."""
        return os.path.join(self.dossier, FICHIERS[type_objet][0])

    # ------------------------------------------------------------------
    # Sauvegarde
    # ------------------------------------------------------------------
    def sauvegarder(self, bibliotheque):
        """Écrit l'état complet de la bibliothèque dans les trois fichiers.

        Raises:
            ErreurPersistance: si l'écriture échoue (droits, disque...).
        """
        collections = {
            "ouvrage": bibliotheque.ouvrages,
            "lecteur": bibliotheque.lecteurs,
            "emprunt": bibliotheque.emprunts,
        }
        try:
            os.makedirs(self.dossier, exist_ok=True)
            for type_objet, collection in collections.items():
                cle = FICHIERS[type_objet][1]
                contenu = {
                    "version": VERSION_FORMAT,
                    "compteur": bibliotheque.compteurs[type_objet],
                    cle: [collection[i].to_dict() for i in sorted(collection)],
                }
                self._ecrire_atomique(self.chemin(type_objet), contenu)
        except OSError as erreur:
            raise ErreurPersistance(
                f"Échec de la sauvegarde dans {self.dossier} : {erreur}"
            ) from erreur

    @staticmethod
    def _ecrire_atomique(chemin, contenu):
        """Écrit ``contenu`` en JSON sans jamais corrompre ``chemin``."""
        temporaire = chemin + ".tmp"
        with open(temporaire, "w", encoding="utf-8") as fichier:
            json.dump(contenu, fichier, ensure_ascii=False, indent=2)
            fichier.write("\n")
            fichier.flush()
            os.fsync(fichier.fileno())
        if os.path.exists(chemin):
            shutil.copy2(chemin, chemin + ".bak")
        os.replace(temporaire, chemin)

    # ------------------------------------------------------------------
    # Chargement
    # ------------------------------------------------------------------
    def charger(self):
        """Reconstruit une bibliothèque à partir des fichiers JSON.

        Un fichier absent donne une collection vide. Un fichier corrompu
        est mis de côté et remplacé par sa sauvegarde ``.bak`` si elle est
        lisible, sinon par une collection vide. Les messages
        correspondants sont disponibles dans :attr:`avertissements`.

        Returns:
            Bibliotheque: l'état restauré (cohérence des index vérifiée).
        """
        self.avertissements = []
        bibliotheque = Bibliotheque()
        cibles = {
            "ouvrage": bibliotheque.ouvrages,
            "lecteur": bibliotheque.lecteurs,
            "emprunt": bibliotheque.emprunts,
        }
        for type_objet, cible in cibles.items():
            attribut_id = FICHIERS[type_objet][3]
            compteur, objets = self._charger_fichier(type_objet)
            for objet in objets:
                cible[getattr(objet, attribut_id)] = objet
            plus_grand = max(
                (self._numero(i) for i in cible), default=0
            )
            bibliotheque.compteurs[type_objet] = max(compteur, plus_grand)
        corrections = bibliotheque.reconstruire_index()
        if corrections:
            self.avertissements.append(
                f"{corrections} incohérence(s) corrigée(s) entre emprunts, "
                "exemplaires et lecteurs."
            )
        return bibliotheque

    def _charger_fichier(self, type_objet):
        """Retourne ``(compteur, objets)`` pour un type d'objet."""
        chemin = self.chemin(type_objet)
        nom = os.path.basename(chemin)
        if not os.path.exists(chemin):
            if os.path.exists(chemin + ".bak"):
                self.avertissements.append(
                    f"{nom} absent : restauration depuis {nom}.bak."
                )
                return self._lire(type_objet, chemin + ".bak")
            self.avertissements.append(
                f"{nom} absent : démarrage avec une liste vide."
            )
            return 0, []
        try:
            return self._lire(type_objet, chemin)
        except ErreurPersistance as erreur:
            mis_de_cote = self._mettre_de_cote(chemin)
            self.avertissements.append(
                f"{nom} corrompu ({erreur}). Copie conservée sous "
                f"{os.path.basename(mis_de_cote)}."
            )
        try:
            resultat = self._lire(type_objet, chemin + ".bak")
        except (ErreurPersistance, FileNotFoundError):
            self.avertissements.append(
                f"Aucune sauvegarde valide de {nom} : liste vide."
            )
            return 0, []
        self.avertissements.append(f"{nom} restauré depuis {nom}.bak.")
        return resultat

    @staticmethod
    def _lire(type_objet, chemin):
        """Lit et valide un fichier ; lève :class:`ErreurPersistance`."""
        _, cle, classe, _ = FICHIERS[type_objet]
        try:
            with open(chemin, encoding="utf-8") as fichier:
                contenu = json.load(fichier)
            if not isinstance(contenu, dict) or not isinstance(
                    contenu.get(cle), list):
                raise ValueError(f"clé « {cle} » absente ou invalide")
            objets = [classe.from_dict(d) for d in contenu[cle]]
            compteur = int(contenu.get("compteur", 0))
        except FileNotFoundError:
            raise
        except (OSError, ValueError, KeyError, TypeError, AttributeError,
                DonneesInvalides) as erreur:
            raise ErreurPersistance(
                f"{type(erreur).__name__}: {erreur}"
            ) from erreur
        return compteur, objets

    @staticmethod
    def _mettre_de_cote(chemin):
        """Renomme un fichier corrompu pour ne jamais l'écraser."""
        horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
        destination = f"{chemin}.corrompu-{horodatage}"
        os.replace(chemin, destination)
        return destination

    @staticmethod
    def _numero(identifiant):
        """Partie numérique d'un identifiant ``XXX-0042`` (0 sinon)."""
        suffixe = identifiant.rsplit("-", 1)[-1]
        return int(suffixe) if suffixe.isdigit() else 0
