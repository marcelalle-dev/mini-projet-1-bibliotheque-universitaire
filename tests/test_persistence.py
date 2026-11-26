"""Tests de la sauvegarde et du chargement JSON."""

import json
import os
import tempfile
import unittest

from src.models import Enseignant
from src.persistence import GestionnaireJSON
from src.services import GestionnaireEmprunts
from tests.utilitaires import creer_contexte


class TestPersistanceJSON(unittest.TestCase):
    """Sauvegarde, restauration et robustesse face aux fichiers abîmés."""

    def setUp(self):
        """Crée un dossier temporaire et une bibliothèque avec 3 prêts."""
        self._dossier = tempfile.TemporaryDirectory()
        self.dossier = self._dossier.name
        self.persistance = GestionnaireJSON(self.dossier)
        self.biblio, self.gestion, _, self.horloge = creer_contexte()
        # Plusieurs emprunts du même ouvrage : vérifie que chaque emprunt
        # est bien indexé par son propre identifiant au rechargement.
        self.gestion.emprunter("LEC-0001", "OUV-0003")
        self.gestion.emprunter("LEC-0002", "OUV-0003")
        self.gestion.prolonger("EMP-0002")
        self.horloge.avancer(3)
        self.gestion.retourner("EMP-0001")
        self.gestion.emprunter("LEC-0001", "OUV-0003")

    def tearDown(self):
        """Supprime le dossier temporaire."""
        self._dossier.cleanup()

    def _ecrire(self, nom, texte):
        """Écrit un contenu brut dans un fichier du dossier de test."""
        with open(os.path.join(self.dossier, nom), "w",
                  encoding="utf-8") as fichier:
            fichier.write(texte)

    def test_sauvegarde_et_restauration(self):
        """L'état rechargé est identique à l'état sauvegardé."""
        self.persistance.sauvegarder(self.biblio)
        copie = self.persistance.charger()
        self.assertEqual(self.persistance.avertissements, [])
        for attribut in ("ouvrages", "lecteurs", "emprunts"):
            original = getattr(self.biblio, attribut)
            restaure = getattr(copie, attribut)
            self.assertEqual(sorted(restaure), sorted(original))
            for cle, objet in original.items():
                self.assertEqual(restaure[cle].to_dict(), objet.to_dict())
        self.assertIsInstance(copie.lecteurs["LEC-0002"], Enseignant)
        self.assertTrue(copie.emprunts["EMP-0002"].prolonge)
        self.assertFalse(copie.emprunts["EMP-0001"].est_actif)
        self.assertEqual(copie.compteurs, self.biblio.compteurs)

    def test_identifiants_conserves_apres_redemarrage(self):
        """Les nouveaux identifiants continuent la séquence existante."""
        self.persistance.sauvegarder(self.biblio)
        copie = self.persistance.charger()
        gestion = GestionnaireEmprunts(copie, self.horloge)
        self.assertEqual(gestion.emprunter("LEC-0002", "OUV-0001")
                         .id_emprunt, "EMP-0004")
        self.assertEqual(copie.inscrire_etudiant("Koffi", "Yao")
                         .id_lecteur, "LEC-0003")

    def test_fichiers_inexistants(self):
        """Sans fichier, l'application démarre avec des données vides."""
        biblio = GestionnaireJSON(os.path.join(self.dossier, "vide")).charger()
        self.assertEqual((biblio.ouvrages, biblio.lecteurs, biblio.emprunts),
                         ({}, {}, {}))

    def test_json_corrompu_restaure_depuis_sauvegarde(self):
        """Un fichier corrompu est mis de côté et le .bak est utilisé."""
        self.persistance.sauvegarder(self.biblio)
        self.persistance.sauvegarder(self.biblio)     # crée les .bak
        self._ecrire("lecteurs.json", "{ ceci n'est pas du JSON")
        copie = self.persistance.charger()
        self.assertEqual(sorted(copie.lecteurs), ["LEC-0001", "LEC-0002"])
        fichiers = os.listdir(self.dossier)
        self.assertTrue(any(f.startswith("lecteurs.json.corrompu-")
                            for f in fichiers))
        self.assertTrue(any("restauré" in m
                            for m in self.persistance.avertissements))

    def test_json_corrompu_sans_sauvegarde(self):
        """Sans .bak, la collection est vide mais le fichier est gardé."""
        self._ecrire("ouvrages.json", json.dumps({"ouvrages": "pas liste"}))
        copie = self.persistance.charger()
        self.assertEqual(copie.ouvrages, {})
        self.assertTrue(any(f.startswith("ouvrages.json.corrompu-")
                            for f in os.listdir(self.dossier)))

    def test_ecriture_atomique_avec_copie_de_securite(self):
        """La sauvegarde ne laisse aucun .tmp et conserve un .bak."""
        self.persistance.sauvegarder(self.biblio)
        self.persistance.sauvegarder(self.biblio)
        fichiers = sorted(os.listdir(self.dossier))
        self.assertIn("emprunts.json.bak", fichiers)
        self.assertFalse(any(f.endswith(".tmp") for f in fichiers))
        with open(os.path.join(self.dossier, "emprunts.json"),
                  encoding="utf-8") as fichier:
            contenu = json.load(fichier)
        self.assertEqual(contenu["compteur"], 3)
        self.assertEqual(len(contenu["emprunts"]), 3)

    def test_incoherences_corrigees_au_chargement(self):
        """Les états dérivés sont recalculés à partir des emprunts."""
        self.biblio.ouvrages["OUV-0001"].exemplaires[0].disponible = False
        self.biblio.lecteurs["LEC-0001"].emprunts_actifs = []
        self.persistance.sauvegarder(self.biblio)
        copie = self.persistance.charger()
        self.assertTrue(copie.ouvrages["OUV-0001"].exemplaires[0].disponible)
        self.assertEqual(copie.lecteurs["LEC-0001"].emprunts_actifs,
                         ["EMP-0003"])
        self.assertTrue(self.persistance.avertissements)


if __name__ == "__main__":
    unittest.main()
