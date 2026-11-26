"""Tests de la hiérarchie Lecteur / Etudiant / Enseignant."""

import unittest
from datetime import date

from src.exceptions import (
    DonneesInvalides,
    LecteurIntrouvable,
    OperationImpossible,
)
from src.models import Enseignant, Etudiant, Lecteur
from tests.utilitaires import creer_contexte


class TestHierarchieLecteurs(unittest.TestCase):
    """Classe abstraite, héritage et polymorphisme."""

    def test_lecteur_est_abstrait(self):
        """La classe abstraite Lecteur ne peut pas être instanciée."""
        with self.assertRaises(TypeError):
            Lecteur("LEC-0001", "Nom", "Prénom")  # pylint: disable=E0110

    def test_creation_etudiant(self):
        """Un étudiant : 3 emprunts maximum, 14 jours."""
        etudiant = Etudiant("LEC-0001", "dossou", "aïcha", niveau="l2")
        self.assertIsInstance(etudiant, Lecteur)
        self.assertEqual((etudiant.quota_max, etudiant.duree_emprunt),
                         (3, 14))
        self.assertEqual(etudiant.type_lecteur, "Étudiant")
        self.assertEqual(etudiant.nom_complet, "Aïcha DOSSOU")
        self.assertEqual(etudiant.niveau, "L2")

    def test_creation_enseignant(self):
        """Un enseignant : 5 emprunts maximum, 30 jours."""
        enseignant = Enseignant("LEC-0002", "Zinsou", "Brigitte",
                                departement="Maths")
        self.assertIsInstance(enseignant, Lecteur)
        self.assertEqual((enseignant.quota_max, enseignant.duree_emprunt),
                         (5, 30))
        self.assertEqual(enseignant.type_lecteur, "Enseignant")

    def test_polymorphisme_date_retour(self):
        """La même méthode donne une échéance différente selon le type."""
        debut = date(2026, 3, 1)
        lecteurs = [Etudiant("L1", "A", "B"), Enseignant("L2", "C", "D")]
        echeances = [lec.calculer_date_retour(debut) for lec in lecteurs]
        self.assertEqual(echeances, [date(2026, 3, 15), date(2026, 3, 31)])

    def test_quota_peut_emprunter(self):
        """peut_emprunter() dépend du quota propre au type de lecteur."""
        etudiant = Etudiant("L1", "A", "B",
                            emprunts_actifs=["E1", "E2", "E3"])
        enseignant = Enseignant("L2", "C", "D",
                                emprunts_actifs=["E1", "E2", "E3"])
        self.assertFalse(etudiant.peut_emprunter())
        self.assertTrue(enseignant.peut_emprunter())

    def test_serialisation_polymorphe(self):
        """from_dict reconstruit la bonne sous-classe et ses attributs."""
        enseignant = Enseignant("LEC-0009", "Gbaguidi", "Rodrigue",
                                "r@example.org", "Économie", "MA", ["E7"])
        copie = Lecteur.from_dict(enseignant.to_dict())
        self.assertIsInstance(copie, Enseignant)
        self.assertEqual(copie.to_dict(), enseignant.to_dict())
        with self.assertRaises(KeyError):
            Lecteur.from_dict({"type": "visiteur", "id_lecteur": "X"})

    def test_nom_obligatoire(self):
        """Un lecteur sans nom est refusé."""
        with self.assertRaises(DonneesInvalides):
            Etudiant("L1", "", "Prénom")


class TestGestionLecteurs(unittest.TestCase):
    """Inscription, modification et suppression via la bibliothèque."""

    def setUp(self):
        """Prépare une bibliothèque de test."""
        self.biblio, self.gestion, _, _ = creer_contexte()

    def test_inscription_identifiants_uniques(self):
        """Chaque inscription reçoit un nouvel identifiant."""
        lecteur = self.biblio.inscrire_etudiant("Koffi", "Yao")
        self.assertEqual(lecteur.id_lecteur, "LEC-0003")
        self.assertEqual(len(self.biblio.lister_lecteurs("etudiant")), 2)
        self.assertEqual(len(self.biblio.lister_lecteurs("enseignant")), 1)

    def test_modification_et_recherche(self):
        """Un lecteur modifié est retrouvé par son nouveau nom."""
        self.biblio.modifier_lecteur("lec-0001", nom="Houessou")
        self.assertEqual(
            [lec.id_lecteur
             for lec in self.biblio.rechercher_lecteurs("houes")],
            ["LEC-0001"])

    def test_suppression_lecteur(self):
        """Un lecteur sans emprunt peut être supprimé, sinon refus."""
        self.gestion.emprunter("LEC-0001", "OUV-0001")
        with self.assertRaises(OperationImpossible):
            self.biblio.supprimer_lecteur("LEC-0001")
        self.biblio.supprimer_lecteur("LEC-0002")
        with self.assertRaises(LecteurIntrouvable):
            self.biblio.obtenir_lecteur("LEC-0002")


if __name__ == "__main__":
    unittest.main()
