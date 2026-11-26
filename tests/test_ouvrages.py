"""Tests des ouvrages, exemplaires et de la recherche dans le catalogue."""

import unittest

from src.exceptions import (
    DonneesInvalides,
    DoublonErreur,
    ExemplaireIntrouvable,
    OperationImpossible,
    OuvrageIntrouvable,
)
from src.models import Ouvrage
from tests.utilitaires import ISBN_PYTHON, creer_contexte


class TestCreationOuvrage(unittest.TestCase):
    """Création et validation des ouvrages."""

    def setUp(self):
        """Prépare une bibliothèque de test."""
        self.biblio, *_ = creer_contexte()

    def test_creation_ouvrage_avec_exemplaires(self):
        """Un ouvrage reçoit un identifiant unique et ses exemplaires."""
        ouvrage = self.biblio.ajouter_ouvrage(
            "Bases de données", "Georges Gardarin", "9782100001040",
            "Informatique", 3)
        self.assertEqual(ouvrage.id_ouvrage, "OUV-0004")
        self.assertEqual(ouvrage.nb_exemplaires, 3)
        self.assertEqual(
            [e.id_exemplaire for e in ouvrage.exemplaires],
            ["OUV-0004-E01", "OUV-0004-E02", "OUV-0004-E03"])
        self.assertTrue(all(e.disponible for e in ouvrage.exemplaires))

    def test_isbn_normalise_et_isbn10_avec_x(self):
        """Les tirets sont supprimés ; un ISBN-10 finissant par X est
        accepté."""
        ouvrage = self.biblio.obtenir_ouvrage("OUV-0001")
        self.assertEqual(ouvrage.isbn, "9782100001019")
        livre = Ouvrage("OUV-9999", "T", "A", "0-8044-2957-x", "C")
        self.assertEqual(livre.isbn, "080442957X")

    def test_isbn_invalide_refuse(self):
        """Un ISBN dont la clé de contrôle est fausse est refusé."""
        with self.assertRaises(DonneesInvalides):
            self.biblio.ajouter_ouvrage("Titre", "Auteur", "9782100001012",
                                        "Cat")
        with self.assertRaises(DonneesInvalides):
            self.biblio.ajouter_ouvrage("Titre", "Auteur", "12345", "Cat")

    def test_champ_obligatoire_vide_refuse(self):
        """Titre, auteur et catégorie sont obligatoires."""
        with self.assertRaises(DonneesInvalides):
            self.biblio.ajouter_ouvrage("   ", "Auteur", "9782100001040",
                                        "Cat")
        self.assertEqual(self.biblio.compteurs["ouvrage"], 3,
                         "un échec ne doit pas consommer d'identifiant")

    def test_isbn_en_double_refuse(self):
        """Deux ouvrages ne peuvent pas partager le même ISBN."""
        with self.assertRaises(DoublonErreur):
            self.biblio.ajouter_ouvrage("Autre", "X", ISBN_PYTHON, "Cat")


class TestModificationSuppression(unittest.TestCase):
    """Modification et suppression d'ouvrages."""

    def setUp(self):
        """Prépare une bibliothèque de test."""
        self.biblio, self.gestion, _, _ = creer_contexte()

    def test_modification_ouvrage(self):
        """Seuls les champs fournis sont modifiés."""
        self.biblio.modifier_ouvrage("ouv-0001", titre="Python 3",
                                     categorie="Programmation")
        ouvrage = self.biblio.obtenir_ouvrage("OUV-0001")
        self.assertEqual(ouvrage.titre, "Python 3")
        self.assertEqual(ouvrage.categorie, "Programmation")
        self.assertEqual(ouvrage.auteur, "Gérard Swinnen")

    def test_modification_invalide_laisse_ouvrage_intact(self):
        """Une modification invalide n'altère aucun champ."""
        with self.assertRaises(DonneesInvalides):
            self.biblio.modifier_ouvrage("OUV-0001", titre="Nouveau",
                                         isbn="123")
        self.assertEqual(self.biblio.obtenir_ouvrage("OUV-0001").titre,
                         "Apprendre Python")

    def test_suppression_ouvrage(self):
        """Un ouvrage sans prêt en cours peut être supprimé."""
        self.biblio.supprimer_ouvrage("OUV-0002")
        with self.assertRaises(OuvrageIntrouvable):
            self.biblio.obtenir_ouvrage("OUV-0002")

    def test_suppression_ouvrage_emprunte_refusee(self):
        """On ne peut pas supprimer un ouvrage dont un exemplaire est
        prêté."""
        self.gestion.emprunter("LEC-0001", "OUV-0002")
        with self.assertRaises(OperationImpossible):
            self.biblio.supprimer_ouvrage("OUV-0002")
        self.assertIn("OUV-0002", self.biblio.ouvrages)


class TestRecherche(unittest.TestCase):
    """Recherche par titre, auteur, catégorie et ISBN."""

    def setUp(self):
        """Prépare une bibliothèque de test."""
        self.biblio, *_ = creer_contexte()

    def test_recherche_par_titre_partielle_sans_casse(self):
        """La recherche par titre est partielle et ignore la casse."""
        resultats = self.biblio.rechercher_par_titre("pYtHoN")
        self.assertEqual([o.id_ouvrage for o in resultats], ["OUV-0001"])

    def test_recherche_par_auteur(self):
        """La recherche par auteur trouve un nom partiel."""
        resultats = self.biblio.rechercher_par_auteur("tanenbaum")
        self.assertEqual([o.titre for o in resultats], ["Réseaux"])

    def test_recherche_par_categorie(self):
        """La recherche par catégorie retourne tous les ouvrages
        concernés, triés par titre."""
        resultats = self.biblio.rechercher_par_categorie("informatique")
        self.assertEqual([o.titre for o in resultats],
                         ["Algorithmique", "Apprendre Python"])

    def test_recherche_par_isbn_exacte(self):
        """La recherche par ISBN est exacte et ignore les tirets."""
        self.assertEqual(
            len(self.biblio.rechercher_par_isbn("978-2-10-000101-9")), 1)
        self.assertEqual(len(self.biblio.rechercher_par_isbn("978210")), 0)

    def test_recherche_critere_invalide(self):
        """Un critère inconnu ou un terme vide est refusé."""
        with self.assertRaises(DonneesInvalides):
            self.biblio.rechercher("editeur", "x")
        with self.assertRaises(DonneesInvalides):
            self.biblio.rechercher("titre", "  ")


class TestExemplaires(unittest.TestCase):
    """Gestion des exemplaires multiples d'un ouvrage."""

    def setUp(self):
        """Prépare une bibliothèque de test."""
        self.biblio, self.gestion, _, _ = creer_contexte()

    def test_disponibilite_suivie_par_exemplaire(self):
        """Emprunter un exemplaire réduit la disponibilité de l'ouvrage."""
        ouvrage = self.biblio.obtenir_ouvrage("OUV-0001")
        self.gestion.emprunter("LEC-0001", "OUV-0001")
        self.assertEqual((ouvrage.nb_disponibles, ouvrage.nb_empruntes),
                         (1, 1))
        self.assertTrue(ouvrage.est_disponible())

    def test_ajout_exemplaires(self):
        """Les nouveaux exemplaires suivent la numérotation existante."""
        nouveaux = self.biblio.ajouter_exemplaires("OUV-0002", 2)
        self.assertEqual([e.id_exemplaire for e in nouveaux],
                         ["OUV-0002-E02", "OUV-0002-E03"])

    def test_identifiant_exemplaire_jamais_reattribue(self):
        """Un identifiant d'exemplaire retiré n'est pas réutilisé."""
        self.biblio.retirer_exemplaire("OUV-0001", "OUV-0001-E02")
        nouveau = self.biblio.ajouter_exemplaires("OUV-0001", 1)[0]
        self.assertEqual(nouveau.id_exemplaire, "OUV-0001-E03")

    def test_retrait_exemplaire_emprunte_ou_inconnu_refuse(self):
        """On ne retire ni un exemplaire prêté ni un exemplaire inconnu."""
        emprunt = self.gestion.emprunter("LEC-0001", "OUV-0003")
        with self.assertRaises(OperationImpossible):
            self.biblio.retirer_exemplaire("OUV-0003",
                                           emprunt.id_exemplaire)
        with self.assertRaises(ExemplaireIntrouvable):
            self.biblio.retirer_exemplaire("OUV-0003", "OUV-0003-E99")


if __name__ == "__main__":
    unittest.main()
