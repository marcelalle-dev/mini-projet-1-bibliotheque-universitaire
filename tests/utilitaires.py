"""Outils communs aux tests : jeu de données minimal et horloge simulée."""

from datetime import date, timedelta

from src.services import Bibliotheque, GestionnaireEmprunts, TableauBord

#: ISBN valides utilisés dans les tests.
ISBN_PYTHON = "978-2-10-000101-9"
ISBN_ALGO = "9782100001026"
ISBN_RESEAUX = "2-266-11156-6"
DEBUT = date(2026, 1, 5)


class HorlogeSimulee:
    """Horloge contrôlable : ``avancer(n)`` simule le passage du temps."""

    def __init__(self, jour=DEBUT):
        """Démarre l'horloge à la date ``jour``."""
        self.jour = jour

    def __call__(self):
        """Retourne la date courante simulée."""
        return self.jour

    def avancer(self, jours):
        """Avance l'horloge de ``jours`` jours."""
        self.jour += timedelta(days=jours)


def creer_contexte():
    """Crée une bibliothèque de test avec ses services.

    Contenu : 3 ouvrages (Python : 2 exemplaires, Algorithmique : 1,
    Réseaux : 5), un étudiant (LEC-0001) et un enseignant (LEC-0002).

    Returns:
        tuple: ``(bibliotheque, gestionnaire, tableau_bord, horloge)``.
    """
    bibliotheque = Bibliotheque()
    bibliotheque.ajouter_ouvrage("Apprendre Python", "Gérard Swinnen",
                                 ISBN_PYTHON, "Informatique", 2)
    bibliotheque.ajouter_ouvrage("Algorithmique", "Thomas Cormen",
                                 ISBN_ALGO, "Informatique", 1)
    bibliotheque.ajouter_ouvrage("Réseaux", "Andrew Tanenbaum",
                                 ISBN_RESEAUX, "Télécoms", 5)
    bibliotheque.inscrire_etudiant("Dossou", "Aïcha", filiere="Info",
                                   niveau="l2")
    bibliotheque.inscrire_enseignant("Zinsou", "Brigitte",
                                     departement="Mathématiques")
    horloge = HorlogeSimulee()
    gestionnaire = GestionnaireEmprunts(bibliotheque, horloge)
    tableau = TableauBord(bibliotheque, horloge)
    return bibliotheque, gestionnaire, tableau, horloge
