"""Tests du tableau de bord et de l'interface console."""

import tempfile
import unittest

from src.interface import Console, Menu
from src.persistence import GestionnaireJSON
from src.services import Bibliotheque, TableauBord
from tests.utilitaires import creer_contexte


class TestTableauBord(unittest.TestCase):
    """Indicateurs : fonds, top des ouvrages, retards, taux."""

    def setUp(self):
        """Prépare une bibliothèque (8 exemplaires) et quelques prêts."""
        self.biblio, self.gestion, self.tableau, self.horloge = (
            creer_contexte())
        self.gestion.emprunter("LEC-0001", "OUV-0001")   # étudiant, 14 j
        self.gestion.emprunter("LEC-0002", "OUV-0001")   # enseignant, 30 j
        self.gestion.emprunter("LEC-0001", "OUV-0003")
        self.gestion.retourner("EMP-0003")
        self.gestion.emprunter("LEC-0001", "OUV-0002")

    def test_bibliotheque_vide(self):
        """Une bibliothèque vide a un taux d'occupation nul."""
        tableau = TableauBord(Bibliotheque())
        self.assertEqual(tableau.taux_occupation(), 0.0)
        self.assertEqual(tableau.ouvrages_plus_empruntes(), [])

    def test_compteurs_et_taux_occupation(self):
        """Taux = exemplaires empruntés / total × 100."""
        self.assertEqual(self.tableau.nb_ouvrages(), 3)
        self.assertEqual(self.tableau.nb_exemplaires(), 8)
        self.assertEqual(self.tableau.nb_exemplaires_empruntes(), 3)
        self.assertEqual(self.tableau.nb_exemplaires_disponibles(), 5)
        self.assertEqual(self.tableau.taux_occupation(), 37.5)

    def test_ouvrages_plus_empruntes(self):
        """Classement par nombre d'emprunts (historique compris)."""
        top = self.tableau.ouvrages_plus_empruntes(2)
        self.assertEqual(top[0], ("OUV-0001", "Apprendre Python", 2))
        self.assertEqual(len(top), 2)
        self.assertEqual(top[1][2], 1)

    def test_lecteurs_en_retard(self):
        """Seuls les lecteurs dépassant leur échéance apparaissent."""
        self.assertEqual(self.tableau.lecteurs_en_retard(), [])
        self.horloge.avancer(20)   # étudiant en retard de 6 j, pas le prof
        retards = self.tableau.lecteurs_en_retard()
        self.assertEqual([r["id_lecteur"] for r in retards], ["LEC-0001"])
        self.assertEqual(retards[0]["jours_retard"], 6)
        self.assertEqual(retards[0]["penalite"], 1200)   # 2 prêts × 6 j

    def test_statistiques_et_rapport(self):
        """La synthèse agrège correctement les indicateurs."""
        self.horloge.avancer(20)
        stats = self.tableau.statistiques()
        self.assertEqual(stats["nb_emprunts_total"], 4)
        self.assertEqual(stats["nb_emprunts_actifs"], 3)
        self.assertEqual(stats["nb_emprunts_en_retard"], 2)
        self.assertEqual(stats["penalites_en_cours"], 1200)
        rapport = self.tableau.generer_rapport()
        self.assertIn("37.50 %", rapport)
        self.assertIn("Aïcha DOSSOU", rapport)


class TestInterfaceConsole(unittest.TestCase):
    """Le menu ne plante pas sur des saisies incorrectes."""

    def executer_menu(self, saisies):
        """Lance le menu avec des saisies simulées ; retourne la sortie."""
        biblio, _, _, horloge = creer_contexte()
        reponses = iter(saisies)
        sortie = []

        def entree(message):
            sortie.append(message)
            try:
                return next(reponses)
            except StopIteration:
                raise EOFError() from None

        with tempfile.TemporaryDirectory() as dossier:
            persistance = GestionnaireJSON(dossier)
            menu = Menu(biblio, persistance, Console(entree, sortie.append),
                        horloge)
            menu.executer()
            recharge = persistance.charger()
        return "\n".join(sortie), recharge

    def test_saisies_invalides_et_erreur_metier(self):
        """Choix invalide, quota dépassé et retour au menu sans plantage."""
        saisies = ["abc", "3",
                   "1", "LEC-0001", "OUV-0001", "",
                   "1", "LEC-0001", "OUV-0002", "",
                   "1", "LEC-0001", "OUV-0003", "",
                   "1", "LEC-0001", "OUV-0003", "",   # 4e : quota
                   "0", "9"]
        texte, recharge = self.executer_menu(saisies)
        self.assertIn("Choix invalide", texte)
        self.assertIn("quota de 3", texte)
        self.assertEqual(len(recharge.emprunts), 3,
                         "les emprunts sont sauvegardés automatiquement")

    def test_fin_de_saisie_sauvegarde(self):
        """Une fermeture de l'entrée standard sauvegarde et quitte."""
        texte, recharge = self.executer_menu(["2", "4", "Koffi", "Yao", "",
                                              "", ""])
        self.assertIn("Au revoir", texte)
        self.assertIn("LEC-0003", recharge.lecteurs)


if __name__ == "__main__":
    unittest.main()
