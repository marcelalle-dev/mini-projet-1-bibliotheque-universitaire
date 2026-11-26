"""Tests des règles de prêt : emprunt, retour, prolongation, pénalités."""

import unittest
from datetime import date, timedelta

from src.exceptions import (
    DonneesInvalides,
    EmpruntDejaCloture,
    EmpruntDejaEnCours,
    EmpruntIntrouvable,
    LecteurEnRetard,
    OuvrageIndisponible,
    ProlongationRefusee,
    QuotaDepasse,
)
from src.models import Emprunt
from tests.utilitaires import DEBUT, creer_contexte


class TestEmprunt(unittest.TestCase):
    """Création d'un emprunt et vérifications préalables."""

    def setUp(self):
        """Prépare une bibliothèque de test."""
        self.biblio, self.gestion, _, self.horloge = creer_contexte()

    def _ajouter_ouvrages(self, nombre):
        """Ajoute ``nombre`` ouvrages d'un exemplaire, retourne leurs id."""
        ids = []
        for i in range(nombre):
            corps = f"97821000{20 + i:03d}0"
            total = sum(int(c) * (1 if k % 2 == 0 else 3)
                        for k, c in enumerate(corps[:12]))
            isbn = corps[:12] + str((10 - total % 10) % 10)
            ids.append(self.biblio.ajouter_ouvrage(
                f"Livre {i}", "Auteur", isbn, "Divers").id_ouvrage)
        return ids

    def test_emprunt_ouvrage_disponible(self):
        """Un emprunt valide réserve un exemplaire pour 14 jours."""
        emprunt = self.gestion.emprunter("LEC-0001", "OUV-0001")
        self.assertEqual(emprunt.id_emprunt, "EMP-0001")
        self.assertEqual(emprunt.id_exemplaire, "OUV-0001-E01")
        self.assertEqual(emprunt.date_emprunt, DEBUT)
        self.assertEqual(emprunt.date_retour_prevue,
                         DEBUT + timedelta(days=14))
        exemplaire = self.biblio.ouvrages["OUV-0001"].exemplaires[0]
        self.assertFalse(exemplaire.disponible)
        self.assertEqual(self.biblio.lecteurs["LEC-0001"].emprunts_actifs,
                         ["EMP-0001"])

    def test_emprunt_enseignant_trente_jours(self):
        """Un enseignant dispose de 30 jours."""
        emprunt = self.gestion.emprunter("LEC-0002", "OUV-0001")
        self.assertEqual(emprunt.date_retour_prevue,
                         DEBUT + timedelta(days=30))

    def test_ouvrage_indisponible(self):
        """Emprunter un ouvrage sans exemplaire en rayon est refusé."""
        self.gestion.emprunter("LEC-0001", "OUV-0002")   # 1 seul exemplaire
        with self.assertRaises(OuvrageIndisponible):
            self.gestion.emprunter("LEC-0002", "OUV-0002")

    def test_quota_etudiant_depasse(self):
        """Un étudiant ne peut pas dépasser 3 emprunts simultanés."""
        for id_ouvrage in ("OUV-0001", "OUV-0002", "OUV-0003"):
            self.gestion.emprunter("LEC-0001", id_ouvrage)
        autre = self._ajouter_ouvrages(1)[0]
        with self.assertRaises(QuotaDepasse) as contexte:
            self.gestion.emprunter("LEC-0001", autre)
        self.assertEqual(contexte.exception.lecteur.quota_max, 3)

    def test_quota_enseignant_cinq(self):
        """Un enseignant peut emprunter 5 ouvrages, pas 6."""
        ids = self._ajouter_ouvrages(6)
        for id_ouvrage in ids[:5]:
            self.gestion.emprunter("LEC-0002", id_ouvrage)
        with self.assertRaises(QuotaDepasse):
            self.gestion.emprunter("LEC-0002", ids[5])

    def test_lecteur_en_retard_ne_peut_plus_emprunter(self):
        """Un lecteur ayant un prêt en retard ne peut pas emprunter."""
        self.gestion.emprunter("LEC-0001", "OUV-0001")
        self.horloge.avancer(15)
        with self.assertRaises(LecteurEnRetard):
            self.gestion.emprunter("LEC-0001", "OUV-0003")

    def test_meme_ouvrage_deux_fois_refuse(self):
        """Un lecteur ne détient pas deux exemplaires du même ouvrage."""
        self.gestion.emprunter("LEC-0001", "OUV-0003")
        with self.assertRaises(EmpruntDejaEnCours):
            self.gestion.emprunter("LEC-0001", "OUV-0003")

    def test_date_emprunt_future_refusee(self):
        """Une date d'emprunt dans le futur est refusée."""
        with self.assertRaises(DonneesInvalides):
            self.gestion.emprunter("LEC-0001", "OUV-0001",
                                   DEBUT + timedelta(days=1))


class TestRetour(unittest.TestCase):
    """Retour d'un ouvrage."""

    def setUp(self):
        """Prépare une bibliothèque avec un emprunt en cours."""
        self.biblio, self.gestion, _, self.horloge = creer_contexte()
        self.emprunt = self.gestion.emprunter("LEC-0001", "OUV-0002")

    def test_retour_libere_exemplaire_et_quota(self):
        """Le retour remet l'exemplaire en rayon et libère le quota."""
        self.horloge.avancer(5)
        penalite = self.gestion.retourner("EMP-0001")
        self.assertEqual(penalite, 0)
        self.assertFalse(self.emprunt.est_actif)
        self.assertEqual(self.emprunt.date_retour_effective,
                         DEBUT + timedelta(days=5))
        self.assertTrue(self.biblio.ouvrages["OUV-0002"].est_disponible())
        self.assertEqual(self.biblio.lecteurs["LEC-0001"].emprunts_actifs,
                         [])

    def test_double_retour_refuse(self):
        """Un emprunt déjà rendu ne peut pas l'être une seconde fois."""
        self.gestion.retourner("EMP-0001")
        with self.assertRaises(EmpruntDejaCloture):
            self.gestion.retourner("EMP-0001")

    def test_retour_par_identifiant_exemplaire(self):
        """Le retour peut se faire en scannant l'exemplaire."""
        emprunt, _ = self.gestion.retourner_exemplaire("ouv-0002-e01")
        self.assertIs(emprunt, self.emprunt)
        with self.assertRaises(EmpruntIntrouvable):
            self.gestion.retourner_exemplaire("OUV-0002-E01")

    def test_historique_conserve_apres_retour(self):
        """Un emprunt rendu reste dans l'historique."""
        self.gestion.retourner("EMP-0001")
        self.assertEqual(self.gestion.historique(id_lecteur="LEC-0001"),
                         [self.emprunt])
        self.assertEqual(self.gestion.emprunts_actifs(), [])


class TestProlongation(unittest.TestCase):
    """Prolongation unique d'un emprunt."""

    def setUp(self):
        """Prépare une bibliothèque avec un emprunt étudiant."""
        self.biblio, self.gestion, _, self.horloge = creer_contexte()
        self.emprunt = self.gestion.emprunter("LEC-0001", "OUV-0001")

    def test_prolongation_autorisee(self):
        """La prolongation repousse l'échéance de la durée du lecteur."""
        self.horloge.avancer(10)
        nouvelle = self.gestion.prolonger("EMP-0001")
        self.assertEqual(nouvelle, DEBUT + timedelta(days=28))
        self.assertTrue(self.emprunt.prolonge)

    def test_deuxieme_prolongation_refusee(self):
        """Une seule prolongation est autorisée."""
        self.gestion.prolonger("EMP-0001")
        with self.assertRaises(ProlongationRefusee):
            self.gestion.prolonger("EMP-0001")
        self.assertEqual(self.emprunt.date_retour_prevue,
                         DEBUT + timedelta(days=28))

    def test_prolongation_refusee_si_retard_ou_rendu(self):
        """Pas de prolongation d'un prêt en retard ou déjà rendu."""
        self.horloge.avancer(20)
        with self.assertRaises(ProlongationRefusee):
            self.gestion.prolonger("EMP-0001")
        self.gestion.retourner("EMP-0001")
        with self.assertRaises(EmpruntDejaCloture):
            self.gestion.prolonger("EMP-0001")


class TestRetardsEtPenalites(unittest.TestCase):
    """Calcul des retards et des pénalités (100 FCFA par jour)."""

    def setUp(self):
        """Crée un emprunt du 1er au 15 mars 2026."""
        self.emprunt = Emprunt("EMP-0001", "LEC-0001", "OUV-0001",
                               "OUV-0001-E01", date(2026, 3, 1),
                               date(2026, 3, 15))

    def test_calcul_des_retards(self):
        """Le jour limite n'est pas en retard, le lendemain l'est."""
        self.assertEqual(self.emprunt.jours_retard(date(2026, 3, 10)), 0)
        self.assertEqual(self.emprunt.jours_retard(date(2026, 3, 15)), 0)
        self.assertEqual(self.emprunt.jours_retard(date(2026, 3, 16)), 1)
        self.assertEqual(self.emprunt.jours_retard(date(2026, 4, 4)), 20)
        self.assertTrue(self.emprunt.est_en_retard(date(2026, 3, 16)))

    def test_calcul_des_penalites(self):
        """La pénalité vaut 100 FCFA par jour de retard."""
        self.assertEqual(self.emprunt.calculer_penalite(date(2026, 3, 15)),
                         0)
        self.assertEqual(self.emprunt.calculer_penalite(date(2026, 3, 22)),
                         700)

    def test_penalite_figee_au_retour(self):
        """Après le retour, la pénalité n'augmente plus."""
        penalite = self.emprunt.cloturer(date(2026, 3, 18))
        self.assertEqual(penalite, 300)
        self.assertEqual(self.emprunt.penalite_payee, 300)
        self.assertEqual(self.emprunt.calculer_penalite(date(2026, 12, 31)),
                         300)
        self.assertFalse(self.emprunt.est_en_retard(date(2026, 12, 31)))

    def test_retour_en_retard_via_gestionnaire(self):
        """Le gestionnaire retourne la pénalité calculée au retour."""
        _, gestion, _, horloge = creer_contexte()
        gestion.emprunter("LEC-0002", "OUV-0003")   # enseignant : 30 jours
        horloge.avancer(34)
        self.assertEqual(gestion.penalite_en_cours("EMP-0001"), 400)
        self.assertEqual(gestion.retourner("EMP-0001"), 400)

    def test_date_retour_anterieure_refusee(self):
        """Une date de retour avant la date d'emprunt est refusée."""
        _, gestion, _, _ = creer_contexte()
        gestion.emprunter("LEC-0001", "OUV-0001")
        with self.assertRaises(DonneesInvalides):
            gestion.retourner("EMP-0001", DEBUT - timedelta(days=1))


if __name__ == "__main__":
    unittest.main()
