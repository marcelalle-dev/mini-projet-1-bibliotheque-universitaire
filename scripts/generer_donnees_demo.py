"""Génère le jeu de données de démonstration dans ``data/``.

Les emprunts sont rejoués chronologiquement à travers les vrais services
(:class:`GestionnaireEmprunts`) avec une horloge simulée : toutes les règles
métier (quota, retards, disponibilité, prolongation unique) sont donc
respectées. Les dates sont calculées par rapport au jour de génération,
afin que la démonstration comporte toujours des emprunts en cours, des
emprunts en retard et un historique.

Utilisation ::

    python scripts/generer_donnees_demo.py            # refuse d'écraser
    python scripts/generer_donnees_demo.py --force    # régénère

Les ISBN sont fictifs mais possèdent une clé de contrôle valide.
"""

import argparse
import os
import sys
from datetime import date, timedelta

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from src.persistence import GestionnaireJSON  # noqa: E402
from src.services import Bibliotheque, GestionnaireEmprunts  # noqa: E402


def isbn13(corps):
    """Complète les 12 premiers chiffres d'un ISBN-13 par sa clé."""
    total = sum(int(c) * (1 if i % 2 == 0 else 3)
                for i, c in enumerate(corps))
    return corps + str((10 - total % 10) % 10)


# clé : (titre, auteur, corps ISBN, catégorie, nombre d'exemplaires)
OUVRAGES = {
    "python": ("Apprendre à programmer avec Python 3", "Gérard Swinnen",
               "978210000101", "Informatique", 4),
    "algo": ("Introduction à l'algorithmique", "Thomas H. Cormen",
             "978210000102", "Informatique", 3),
    "clean": ("Coder proprement", "Robert C. Martin", "978210000103",
              "Informatique", 2),
    "bdd": ("Bases de données", "Georges Gardarin", "978210000104",
            "Informatique", 2),
    "analyse": ("Analyse : cours et exercices", "Jean-Marie Monier",
                "978210000105", "Mathématiques", 3),
    "algebre": ("Algèbre linéaire", "Joseph Grifone", "978210000106",
                "Mathématiques", 2),
    "stat": ("Statistique et probabilités", "Jean-Pierre Lecoutre",
             "978210000107", "Mathématiques", 3),
    "physique": ("Physique", "Eugene Hecht", "978210000108", "Physique",
                 2),
    "eco": ("Principes de l'économie", "N. Gregory Mankiw",
            "978210000109", "Économie", 3),
    "droit": ("Introduction générale au droit", "François Terré",
              "978210000110", "Droit", 2),
    "aventure": ("L'Aventure ambiguë", "Cheikh Hamidou Kane",
                 "978210000111", "Littérature", 2),
    "lettre": ("Une si longue lettre", "Mariama Bâ", "978210000112",
               "Littérature", 3),
    "management": ("Management", "Stephen P. Robbins", "978210000113",
                   "Gestion", 2),
}

# Personnes fictives.
ETUDIANTS = {
    "s1": ("Hounkpatin", "Arnaud", "Informatique", "L2"),
    "s2": ("Dossou", "Aïcha", "Mathématiques", "L3"),
    "s3": ("Koffi", "Yao", "Informatique", "M1"),
    "s4": ("Agbo", "Fréjus", "Économie", "L1"),
    "s5": ("Soglo", "Mireille", "Lettres modernes", "L2"),
    "s6": ("Traoré", "Mariam", "Informatique", "L3"),
}
ENSEIGNANTS = {
    "p1": ("Ahouandjinou", "Codjo", "Informatique", "Professeur titulaire"),
    "p2": ("Zinsou", "Brigitte", "Mathématiques", "Maître de conférences"),
    "p3": ("Gbaguidi", "Rodrigue", "Économie", "Maître-assistant"),
}

# (jour relatif à aujourd'hui, action, paramètres)
#   emprunt  : (étiquette, lecteur, ouvrage)
#   retour   : (étiquette,)
#   prolonger: (étiquette,)
SCENARIO = [
    # --- Historique : emprunts rendus (dont certains en retard) ---
    (-120, "emprunt", ("h1", "s1", "python")),
    (-110, "retour", ("h1",)),
    (-100, "emprunt", ("h2", "s2", "algo")),
    (-90, "emprunt", ("h3", "p1", "clean")),
    (-85, "emprunt", ("h4", "s3", "python")),
    (-80, "retour", ("h2",)),             # 6 jours de retard
    (-75, "emprunt", ("h5", "s4", "eco")),
    (-70, "retour", ("h3",)),
    (-70, "emprunt", ("h6", "p2", "algebre")),
    (-65, "retour", ("h5",)),
    (-60, "retour", ("h4",)),             # 11 jours de retard
    (-60, "emprunt", ("h7", "s1", "algo")),
    (-55, "emprunt", ("h8", "s5", "lettre")),
    (-50, "retour", ("h7",)),
    (-50, "emprunt", ("h9", "s6", "python")),
    (-45, "retour", ("h8",)),
    (-45, "emprunt", ("h10", "p3", "eco")),
    (-40, "prolonger", ("h9",)),          # prolongation dans les délais
    (-40, "emprunt", ("a1", "p1", "physique")),
    (-30, "retour", ("h6",)),             # 10 jours de retard
    (-30, "emprunt", ("a2", "s2", "python")),
    (-25, "retour", ("h9",)),
    (-25, "emprunt", ("a3", "s3", "stat")),
    (-20, "retour", ("h10",)),
    (-20, "emprunt", ("a4", "s3", "algo")),
    # --- Emprunts en cours dans les délais ---
    (-12, "emprunt", ("a5", "s1", "python")),
    (-12, "emprunt", ("a6", "s1", "clean")),
    (-8, "emprunt", ("a7", "s4", "lettre")),
    (-6, "emprunt", ("a8", "s5", "bdd")),
    (-6, "emprunt", ("a9", "p3", "bdd")),     # plus d'exemplaire dispo
    (-5, "prolonger", ("a6",)),
    (-5, "emprunt", ("a10", "p2", "algo")),
    (-5, "emprunt", ("a11", "p2", "analyse")),
    (-4, "emprunt", ("a12", "s1", "algebre")),  # s1 atteint son quota
    (-3, "emprunt", ("a13", "p3", "droit")),
    (-2, "emprunt", ("a14", "s6", "python")),
    (-1, "emprunt", ("a15", "s5", "aventure")),
]


def construire(aujourd_hui):
    """Construit et retourne la bibliothèque de démonstration."""
    bibliotheque = Bibliotheque()
    ouvrages = {
        cle: bibliotheque.ajouter_ouvrage(titre, auteur, isbn13(corps),
                                          categorie, nombre)
        for cle, (titre, auteur, corps, categorie, nombre) in OUVRAGES.items()
    }
    lecteurs = {}
    for cle, (nom, prenom, filiere, niveau) in ETUDIANTS.items():
        email = f"{prenom[0]}.{nom}@etudiant.example.org".lower()
        lecteurs[cle] = bibliotheque.inscrire_etudiant(
            nom, prenom, email, filiere, niveau)
    for cle, (nom, prenom, departement, grade) in ENSEIGNANTS.items():
        email = f"{prenom[0]}.{nom}@enseignant.example.org".lower()
        lecteurs[cle] = bibliotheque.inscrire_enseignant(
            nom, prenom, email, departement, grade)

    horloge = [aujourd_hui]
    gestionnaire = GestionnaireEmprunts(bibliotheque, lambda: horloge[0])
    emprunts = {}
    for decalage, action, parametres in SCENARIO:
        horloge[0] = aujourd_hui + timedelta(days=decalage)
        if action == "emprunt":
            etiquette, lecteur, ouvrage = parametres
            emprunts[etiquette] = gestionnaire.emprunter(
                lecteurs[lecteur].id_lecteur, ouvrages[ouvrage].id_ouvrage)
        elif action == "retour":
            gestionnaire.retourner(emprunts[parametres[0]].id_emprunt)
        else:
            gestionnaire.prolonger(emprunts[parametres[0]].id_emprunt)
    return bibliotheque


def main(arguments=None):
    """Génère les fichiers JSON de démonstration."""
    analyseur = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analyseur.add_argument("--data", default=os.path.join(RACINE, "data"),
                           help="dossier de destination (défaut : ./data)")
    analyseur.add_argument("--force", action="store_true",
                           help="écraser les données existantes")
    options = analyseur.parse_args(arguments)

    persistance = GestionnaireJSON(options.data)
    existants = [t for t in ("ouvrage", "lecteur", "emprunt")
                 if os.path.exists(persistance.chemin(t))]
    if existants and not options.force:
        print("Des données existent déjà dans", options.data)
        print("Relancez avec --force pour les remplacer (une copie .bak "
              "de chaque fichier sera conservée).")
        return 1

    bibliotheque = construire(date.today())
    persistance.sauvegarder(bibliotheque)
    actifs = sum(1 for e in bibliotheque.emprunts.values() if e.est_actif)
    print(f"Données de démonstration générées dans {options.data} :")
    print(f"  {len(bibliotheque.ouvrages)} ouvrages, "
          f"{sum(o.nb_exemplaires for o in bibliotheque.ouvrages.values())}"
          f" exemplaires, {len(bibliotheque.lecteurs)} lecteurs, "
          f"{len(bibliotheque.emprunts)} emprunts dont {actifs} en cours.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
