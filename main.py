"""Point d'entrée de l'application de gestion de bibliothèque universitaire.

Utilisation ::

    python main.py                  # données dans ./data
    python main.py --data mon_dossier
"""

import argparse
import os
import sys

from src.interface import Menu
from src.persistence import GestionnaireJSON

DOSSIER_DONNEES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "data")


def configurer_sortie():
    """Évite un plantage si la console ne sait pas afficher un caractère."""
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(errors="replace")


def analyser_arguments(arguments=None):
    """Analyse les arguments de la ligne de commande."""
    analyseur = argparse.ArgumentParser(
        description="Gestion des prêts d'une bibliothèque universitaire."
    )
    analyseur.add_argument(
        "--data", default=DOSSIER_DONNEES,
        help="dossier des fichiers JSON (défaut : ./data)",
    )
    return analyseur.parse_args(arguments)


def main(arguments=None):
    """Charge les données, lance le menu et retourne le code de sortie."""
    configurer_sortie()
    options = analyser_arguments(arguments)
    persistance = GestionnaireJSON(options.data)
    bibliotheque = persistance.charger()
    menu = Menu(bibliotheque, persistance)
    try:
        menu.executer()
    except KeyboardInterrupt:
        print("\nInterruption : sauvegarde des données...")
        menu.quitter()
    return 0


if __name__ == "__main__":
    sys.exit(main())
