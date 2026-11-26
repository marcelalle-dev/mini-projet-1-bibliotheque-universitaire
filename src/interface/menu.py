"""Menu interactif en console de l'application."""

from datetime import date

from src.exceptions import (
    BibliothequeErreur,
    DonneesInvalides,
    ErreurPersistance,
)
from src.interface.console import Console, FinDeSaisie, SaisieAnnulee
from src.models.validation import normaliser_isbn
from src.services import GestionnaireEmprunts, TableauBord

ANNULER = "(laisser vide pour annuler)"
FORMAT_DATE_COURT = "%d/%m/%y"


class Menu:
    """Interface console reliant l'utilisateur aux services métier.

    Chaque opération qui modifie les données déclenche une sauvegarde
    automatique. Les erreurs métier sont affichées sans interrompre
    l'application.

    Args:
        bibliotheque: état chargé au démarrage.
        persistance: gestionnaire JSON utilisé pour les sauvegardes.
        console: entrées/sorties (une :class:`Console` standard par
            défaut).
        horloge: fonction retournant la date du jour.
    """

    def __init__(self, bibliotheque, persistance, console=None,
                 horloge=date.today):
        """Construit le menu et les services associés."""
        self.bibliotheque = bibliotheque
        self.persistance = persistance
        self.console = console or Console()
        self.horloge = horloge
        self.emprunts = GestionnaireEmprunts(bibliotheque, horloge)
        self.tableau_bord = TableauBord(bibliotheque, horloge)
        self._actif = True

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------
    def executer(self):
        """Affiche le menu principal jusqu'à ce que l'utilisateur quitte."""
        actions = {
            "1": self.menu_ouvrages,
            "2": self.menu_lecteurs,
            "3": self.menu_emprunts,
            "4": self.retourner_ouvrage,
            "5": self.prolonger_emprunt,
            "6": self.afficher_tableau_bord,
            "7": self.menu_historique,
            "8": self.sauvegarder,
            "9": self.quitter,
        }
        options = [
            ("1", "Gestion des ouvrages"),
            ("2", "Gestion des lecteurs"),
            ("3", "Gestion des emprunts"),
            ("4", "Retour d'un ouvrage"),
            ("5", "Prolongation d'un emprunt"),
            ("6", "Tableau de bord"),
            ("7", "Historique des emprunts"),
            ("8", "Sauvegarder les données"),
            ("9", "Quitter"),
        ]
        self._afficher_avertissements_chargement()
        while self._actif:
            try:
                self.console.titre(
                    "BIBLIOTHÈQUE UNIVERSITAIRE — MENU PRINCIPAL "
                    f"({self.horloge():%d/%m/%Y})"
                )
                choix = self.console.demander_choix(options)
                self._lancer(actions[choix])
            except FinDeSaisie:
                self.console.afficher()
                self.quitter()

    def _lancer(self, action):
        """Exécute une action en interceptant les erreurs prévisibles."""
        try:
            action()
        except SaisieAnnulee:
            self.console.info("Opération annulée.")
        except BibliothequeErreur as erreur:
            self.console.erreur(str(erreur))

    def _sauvegarde_auto(self):
        """Sauvegarde après une modification ; signale un éventuel échec."""
        try:
            self.persistance.sauvegarder(self.bibliotheque)
        except ErreurPersistance as erreur:
            self.console.erreur(f"{erreur} — vos modifications restent en "
                                "mémoire, réessayez via le menu 8.")

    def _afficher_avertissements_chargement(self):
        """Affiche les messages produits lors du chargement des données."""
        for message in getattr(self.persistance, "avertissements", []):
            self.console.info(message)

    def sauvegarder(self):
        """Menu 8 : sauvegarde manuelle de toutes les données."""
        self.persistance.sauvegarder(self.bibliotheque)
        self.console.succes(
            f"Données sauvegardées dans {self.persistance.dossier}."
        )

    def quitter(self):
        """Menu 9 : sauvegarde puis arrêt de l'application."""
        try:
            self.persistance.sauvegarder(self.bibliotheque)
            self.console.succes("Données sauvegardées. Au revoir !")
        except ErreurPersistance as erreur:
            self.console.erreur(str(erreur))
        self._actif = False

    # ------------------------------------------------------------------
    # 1. Ouvrages
    # ------------------------------------------------------------------
    def menu_ouvrages(self):
        """Sous-menu de gestion du catalogue."""
        actions = {
            "1": self.lister_ouvrages,
            "2": self.rechercher_ouvrages,
            "3": self.details_ouvrage,
            "4": self.ajouter_ouvrage,
            "5": self.modifier_ouvrage,
            "6": self.ajouter_exemplaires,
            "7": self.retirer_exemplaire,
            "8": self.supprimer_ouvrage,
        }
        self._sous_menu("GESTION DES OUVRAGES", [
            ("1", "Lister les ouvrages"),
            ("2", "Rechercher (titre, auteur, catégorie, ISBN)"),
            ("3", "Détails et disponibilité d'un ouvrage"),
            ("4", "Ajouter un ouvrage"),
            ("5", "Modifier un ouvrage"),
            ("6", "Ajouter des exemplaires"),
            ("7", "Retirer un exemplaire"),
            ("8", "Supprimer un ouvrage"),
        ], actions)

    def _sous_menu(self, titre, options, actions):
        """Boucle générique d'un sous-menu (``0`` = retour)."""
        while True:
            self.console.titre(titre)
            choix = self.console.demander_choix(
                options + [("0", "Retour au menu principal")]
            )
            if choix == "0":
                return
            self._lancer(actions[choix])

    def _afficher_ouvrages(self, ouvrages):
        """Affiche une liste d'ouvrages sous forme de tableau."""
        self.console.tableau(
            ["ID", "Titre", "Auteur", "Catégorie", "Dispo"],
            [[o.id_ouvrage, o.titre, o.auteur, o.categorie,
              f"{o.nb_disponibles}/{o.nb_exemplaires}"] for o in ouvrages],
            vide="(aucun ouvrage)",
        )

    def lister_ouvrages(self):
        """Affiche tout le catalogue."""
        ouvrages = self.bibliotheque.lister_ouvrages()
        self._afficher_ouvrages(ouvrages)
        self.console.info(f"{len(ouvrages)} ouvrage(s).")

    def rechercher_ouvrages(self):
        """Recherche par titre, auteur, catégorie ou ISBN."""
        champ = self.console.demander_choix([
            ("1", "Titre"), ("2", "Auteur"), ("3", "Catégorie"),
            ("4", "ISBN"),
        ], "Critère")
        champ = {"1": "titre", "2": "auteur", "3": "categorie",
                 "4": "isbn"}[champ]
        if champ == "categorie":
            self.console.info("Catégories : "
                              + ", ".join(self.bibliotheque.categories()))
        terme = self.console.demander_texte(f"Texte recherché {ANNULER}")
        resultats = self.bibliotheque.rechercher(champ, terme)
        self._afficher_ouvrages(resultats)
        self.console.info(f"{len(resultats)} résultat(s).")

    def _demander_ouvrage(self):
        """Demande un identifiant et retourne l'ouvrage correspondant."""
        return self.bibliotheque.obtenir_ouvrage(
            self.console.demander_texte(f"Identifiant de l'ouvrage, ex. "
                                        f"OUV-0001 {ANNULER}")
        )

    def _demander_isbn(self, defaut=None):
        """Demande un ISBN jusqu'à obtenir une clé de contrôle valide."""
        while True:
            saisie = self.console.demander_texte("ISBN (10 ou 13 chiffres)",
                                                 defaut=defaut)
            try:
                return normaliser_isbn(saisie)
            except DonneesInvalides as erreur:
                self.console.erreur(str(erreur))

    def details_ouvrage(self):
        """Affiche un ouvrage, ses exemplaires et leur disponibilité."""
        ouvrage = self._demander_ouvrage()
        self.console.afficher(str(ouvrage))
        emprunteurs = {e.id_exemplaire: e
                       for e in self.emprunts.emprunts_actifs()}
        lignes = []
        for exemplaire in ouvrage.exemplaires:
            emprunt = emprunteurs.get(exemplaire.id_exemplaire)
            if emprunt is None:
                lignes.append([exemplaire.id_exemplaire, "Disponible", "",
                               ""])
            else:
                lignes.append([
                    exemplaire.id_exemplaire, "Emprunté",
                    self.bibliotheque.libelle_lecteur(emprunt.id_lecteur),
                    f"{emprunt.date_retour_prevue:%d/%m/%Y}",
                ])
        self.console.tableau(["Exemplaire", "État", "Emprunteur",
                              "Retour prévu"], lignes)

    def ajouter_ouvrage(self):
        """Saisit et ajoute un nouvel ouvrage."""
        titre = self.console.demander_texte(f"Titre {ANNULER}")
        auteur = self.console.demander_texte("Auteur")
        isbn = self._demander_isbn()
        categorie = self.console.demander_texte("Catégorie")
        nombre = self.console.demander_entier("Nombre d'exemplaires", 1, 100,
                                              defaut=1)
        ouvrage = self.bibliotheque.ajouter_ouvrage(titre, auteur, isbn,
                                                    categorie, nombre)
        self._sauvegarde_auto()
        self.console.succes(f"Ouvrage ajouté : {ouvrage}")

    def modifier_ouvrage(self):
        """Modifie un ouvrage (Entrée = conserver la valeur actuelle)."""
        ouvrage = self._demander_ouvrage()
        self.console.info("Appuyez sur Entrée pour conserver une valeur.")
        titre = self.console.demander_texte("Titre", defaut=ouvrage.titre)
        auteur = self.console.demander_texte("Auteur", defaut=ouvrage.auteur)
        isbn = self._demander_isbn(defaut=ouvrage.isbn)
        categorie = self.console.demander_texte("Catégorie",
                                                defaut=ouvrage.categorie)
        self.bibliotheque.modifier_ouvrage(ouvrage.id_ouvrage, titre, auteur,
                                           isbn, categorie)
        self._sauvegarde_auto()
        self.console.succes(f"Ouvrage modifié : {ouvrage}")

    def ajouter_exemplaires(self):
        """Ajoute des exemplaires à un ouvrage existant."""
        ouvrage = self._demander_ouvrage()
        nombre = self.console.demander_entier("Nombre d'exemplaires à "
                                              "ajouter", 1, 100)
        nouveaux = self.bibliotheque.ajouter_exemplaires(ouvrage.id_ouvrage,
                                                         nombre)
        self._sauvegarde_auto()
        self.console.succes("Exemplaires créés : " + ", ".join(
            e.id_exemplaire for e in nouveaux))

    def retirer_exemplaire(self):
        """Retire un exemplaire disponible (perte, usure)."""
        ouvrage = self._demander_ouvrage()
        self.console.info("Exemplaires : " + ", ".join(
            e.id_exemplaire for e in ouvrage.exemplaires))
        id_exemplaire = self.console.demander_texte("Exemplaire à retirer")
        retire = self.bibliotheque.retirer_exemplaire(ouvrage.id_ouvrage,
                                                      id_exemplaire)
        self._sauvegarde_auto()
        self.console.succes(f"Exemplaire {retire.id_exemplaire} retiré.")

    def supprimer_ouvrage(self):
        """Supprime un ouvrage après confirmation."""
        ouvrage = self._demander_ouvrage()
        if not self.console.confirmer(f"Supprimer « {ouvrage.titre} » et "
                                      f"ses {ouvrage.nb_exemplaires} "
                                      "exemplaire(s) ?"):
            raise SaisieAnnulee()
        self.bibliotheque.supprimer_ouvrage(ouvrage.id_ouvrage)
        self._sauvegarde_auto()
        self.console.succes(f"Ouvrage {ouvrage.id_ouvrage} supprimé "
                            "(l'historique de ses emprunts est conservé).")

    # ------------------------------------------------------------------
    # 2. Lecteurs
    # ------------------------------------------------------------------
    def menu_lecteurs(self):
        """Sous-menu de gestion des lecteurs."""
        self._sous_menu("GESTION DES LECTEURS", [
            ("1", "Lister les lecteurs"),
            ("2", "Rechercher un lecteur par nom"),
            ("3", "Fiche d'un lecteur (emprunts, pénalités)"),
            ("4", "Inscrire un étudiant"),
            ("5", "Inscrire un enseignant"),
            ("6", "Modifier un lecteur"),
            ("7", "Supprimer un lecteur"),
        ], {
            "1": self.lister_lecteurs,
            "2": self.rechercher_lecteurs,
            "3": self.fiche_lecteur,
            "4": self.inscrire_etudiant,
            "5": self.inscrire_enseignant,
            "6": self.modifier_lecteur,
            "7": self.supprimer_lecteur,
        })

    def _afficher_lecteurs(self, lecteurs):
        """Affiche une liste de lecteurs sous forme de tableau."""
        self.console.tableau(
            ["ID", "Nom", "Type", "Emprunts", "Durée"],
            [[lec.id_lecteur, lec.nom_complet, lec.type_lecteur,
              f"{lec.nb_emprunts_actifs}/{lec.quota_max}",
              f"{lec.duree_emprunt} j"] for lec in lecteurs],
            vide="(aucun lecteur)",
        )

    def lister_lecteurs(self):
        """Affiche tous les lecteurs."""
        lecteurs = self.bibliotheque.lister_lecteurs()
        self._afficher_lecteurs(lecteurs)
        self.console.info(f"{len(lecteurs)} lecteur(s).")

    def rechercher_lecteurs(self):
        """Recherche des lecteurs par nom ou prénom."""
        terme = self.console.demander_texte(f"Nom ou prénom {ANNULER}")
        self._afficher_lecteurs(self.bibliotheque.rechercher_lecteurs(terme))

    def _demander_lecteur(self):
        """Demande un identifiant et retourne le lecteur correspondant."""
        return self.bibliotheque.obtenir_lecteur(
            self.console.demander_texte(f"Identifiant du lecteur, ex. "
                                        f"LEC-0001 {ANNULER}")
        )

    def fiche_lecteur(self):
        """Affiche un lecteur, ses emprunts en cours et ses pénalités."""
        lecteur = self._demander_lecteur()
        self.console.afficher(str(lecteur))
        if lecteur.email:
            self.console.afficher(f"Email : {lecteur.email}")
        self.console.afficher(f"Règles : {lecteur.quota_max} emprunts "
                              f"simultanés, {lecteur.duree_emprunt} jours.")
        en_cours = self.emprunts.emprunts_du_lecteur(lecteur.id_lecteur)
        self._afficher_emprunts(en_cours)
        total = sum(e.calculer_penalite(self.horloge()) for e in en_cours)
        if total:
            self.console.info(f"Pénalité due à ce jour : {total} FCFA.")

    def _demander_identite(self):
        """Saisit nom, prénom et email d'un nouveau lecteur."""
        nom = self.console.demander_texte(f"Nom {ANNULER}")
        prenom = self.console.demander_texte("Prénom")
        email = self.console.demander_texte("Email (facultatif)",
                                            obligatoire=False)
        return nom, prenom, email

    def inscrire_etudiant(self):
        """Inscrit un nouvel étudiant."""
        nom, prenom, email = self._demander_identite()
        filiere = self.console.demander_texte("Filière (facultatif)",
                                              obligatoire=False)
        niveau = self.console.demander_texte("Niveau, ex. L2 (facultatif)",
                                             obligatoire=False)
        lecteur = self.bibliotheque.inscrire_etudiant(nom, prenom, email,
                                                      filiere, niveau)
        self._sauvegarde_auto()
        self.console.succes(f"Étudiant inscrit : {lecteur}")

    def inscrire_enseignant(self):
        """Inscrit un nouvel enseignant."""
        nom, prenom, email = self._demander_identite()
        departement = self.console.demander_texte("Département (facultatif)",
                                                  obligatoire=False)
        grade = self.console.demander_texte("Grade (facultatif)",
                                            obligatoire=False)
        lecteur = self.bibliotheque.inscrire_enseignant(
            nom, prenom, email, departement, grade)
        self._sauvegarde_auto()
        self.console.succes(f"Enseignant inscrit : {lecteur}")

    def modifier_lecteur(self):
        """Modifie l'identité d'un lecteur."""
        lecteur = self._demander_lecteur()
        self.console.info("Appuyez sur Entrée pour conserver une valeur.")
        nom = self.console.demander_texte("Nom", defaut=lecteur.nom)
        prenom = self.console.demander_texte("Prénom", defaut=lecteur.prenom)
        email = self.console.demander_texte("Email", defaut=lecteur.email)
        self.bibliotheque.modifier_lecteur(lecteur.id_lecteur, nom, prenom,
                                           email)
        self._sauvegarde_auto()
        self.console.succes(f"Lecteur modifié : {lecteur}")

    def supprimer_lecteur(self):
        """Supprime un lecteur sans emprunt en cours, après confirmation."""
        lecteur = self._demander_lecteur()
        if not self.console.confirmer(f"Supprimer {lecteur.nom_complet} ?"):
            raise SaisieAnnulee()
        self.bibliotheque.supprimer_lecteur(lecteur.id_lecteur)
        self._sauvegarde_auto()
        self.console.succes(f"Lecteur {lecteur.id_lecteur} supprimé.")

    # ------------------------------------------------------------------
    # 3. Emprunts, 4. Retours, 5. Prolongations
    # ------------------------------------------------------------------
    def menu_emprunts(self):
        """Sous-menu de gestion des emprunts."""
        self._sous_menu("GESTION DES EMPRUNTS", [
            ("1", "Enregistrer un emprunt"),
            ("2", "Lister les emprunts en cours"),
            ("3", "Lister les emprunts en retard"),
        ], {
            "1": self.enregistrer_emprunt,
            "2": self.lister_emprunts_en_cours,
            "3": self.lister_emprunts_en_retard,
        })

    def _afficher_emprunts(self, emprunts):
        """Affiche des emprunts avec leur état et leur retard éventuel."""
        aujourd_hui = self.horloge()
        lignes = []
        for e in emprunts:
            if e.est_actif:
                retard = e.jours_retard(aujourd_hui)
                etat = f"RETARD {retard} j" if retard else "En cours"
            else:
                etat = (f"Rendu "
                        f"{e.date_retour_effective:{FORMAT_DATE_COURT}}")
            lignes.append([
                e.id_emprunt,
                self.bibliotheque.libelle_ouvrage(e.id_ouvrage),
                self.bibliotheque.libelle_lecteur(e.id_lecteur),
                f"{e.date_emprunt:{FORMAT_DATE_COURT}}",
                f"{e.date_retour_prevue:{FORMAT_DATE_COURT}}"
                + ("*" if e.prolonge else ""),
                etat,
                e.calculer_penalite(aujourd_hui),
            ])
        self.console.tableau(
            ["ID", "Ouvrage", "Lecteur", "Emprunté", "Échéance", "État",
             "FCFA"], lignes, vide="(aucun emprunt)")
        if any(e.prolonge for e in emprunts):
            self.console.afficher("  * emprunt prolongé")

    def enregistrer_emprunt(self):
        """Enregistre un emprunt après toutes les vérifications."""
        lecteur = self._demander_lecteur()
        self.console.info(f"{lecteur.nom_complet} : "
                          f"{lecteur.nb_emprunts_actifs}/{lecteur.quota_max}"
                          " emprunts en cours.")
        ouvrage = self._demander_ouvrage()
        date_emprunt = self.console.demander_date("Date d'emprunt")
        emprunt = self.emprunts.emprunter(lecteur.id_lecteur,
                                          ouvrage.id_ouvrage, date_emprunt)
        self._sauvegarde_auto()
        self.console.succes(
            f"Emprunt {emprunt.id_emprunt} : exemplaire "
            f"{emprunt.id_exemplaire} prêté à {lecteur.nom_complet}, "
            f"à rendre au plus tard le "
            f"{emprunt.date_retour_prevue:%d/%m/%Y}."
        )

    def lister_emprunts_en_cours(self):
        """Affiche les emprunts non rendus."""
        self._afficher_emprunts(self.emprunts.emprunts_actifs())

    def lister_emprunts_en_retard(self):
        """Affiche les emprunts en retard et la pénalité courante."""
        retards = self.emprunts.emprunts_en_retard()
        self._afficher_emprunts(retards)
        total = sum(e.calculer_penalite(self.horloge()) for e in retards)
        self.console.info(f"{len(retards)} emprunt(s) en retard, "
                          f"{total} FCFA de pénalités en cours.")

    def retourner_ouvrage(self):
        """Menu 4 : retour par identifiant d'emprunt ou d'exemplaire."""
        self.console.titre("RETOUR D'UN OUVRAGE")
        identifiant = self.console.demander_texte(
            f"Identifiant de l'emprunt (EMP-...) ou de l'exemplaire "
            f"(OUV-...-E..) {ANNULER}"
        ).upper()
        date_retour = self.console.demander_date("Date de retour")
        if identifiant.startswith("OUV-"):
            emprunt, penalite = self.emprunts.retourner_exemplaire(
                identifiant, date_retour)
        else:
            emprunt = self.bibliotheque.obtenir_emprunt(identifiant)
            penalite = self.emprunts.retourner(emprunt.id_emprunt,
                                               date_retour)
        self._sauvegarde_auto()
        self.console.succes(
            f"Retour enregistré : {emprunt.id_exemplaire} "
            f"(« {self.bibliotheque.libelle_ouvrage(emprunt.id_ouvrage)} »)."
        )
        if penalite:
            self.console.info(
                f"Retard de {emprunt.jours_retard()} jour(s) : pénalité de "
                f"{penalite} FCFA à régler."
            )
        else:
            self.console.info("Rendu dans les délais : aucune pénalité.")

    def prolonger_emprunt(self):
        """Menu 5 : prolongation unique d'un emprunt."""
        self.console.titre("PROLONGATION D'UN EMPRUNT")
        identifiant = self.console.demander_texte(
            f"Identifiant de l'emprunt (EMP-...) {ANNULER}")
        nouvelle_date = self.emprunts.prolonger(identifiant)
        self._sauvegarde_auto()
        self.console.succes(f"Emprunt prolongé jusqu'au "
                            f"{nouvelle_date:%d/%m/%Y} (prolongation unique "
                            "utilisée).")

    # ------------------------------------------------------------------
    # 6. Tableau de bord, 7. Historique
    # ------------------------------------------------------------------
    def afficher_tableau_bord(self):
        """Menu 6 : indicateurs de la bibliothèque."""
        self.console.titre("TABLEAU DE BORD")
        self.console.afficher(self.tableau_bord.generer_rapport())

    def menu_historique(self):
        """Menu 7 : historique des emprunts, filtrable."""
        self.console.titre("HISTORIQUE DES EMPRUNTS")
        choix = self.console.demander_choix([
            ("1", "Tout l'historique"),
            ("2", "Historique d'un lecteur"),
            ("3", "Historique d'un ouvrage"),
        ])
        if choix == "1":
            emprunts = self.emprunts.historique()
        elif choix == "2":
            lecteur = self._demander_lecteur()
            emprunts = self.emprunts.historique(id_lecteur=lecteur.id_lecteur)
        else:
            identifiant = self.console.demander_texte(
                f"Identifiant de l'ouvrage {ANNULER}")
            emprunts = self.emprunts.historique(id_ouvrage=identifiant)
        self._afficher_emprunts(emprunts)
        self.console.info(f"{len(emprunts)} emprunt(s).")
