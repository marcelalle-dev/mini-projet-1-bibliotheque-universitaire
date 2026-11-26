"""Dessine le diagramme de classes UML en PNG (docs/diagramme_classes.png).

Version image du fichier ``docs/diagramme_classes.mmd``, destinée au
rapport PDF. Nécessite matplotlib (outil de documentation uniquement,
l'application elle-même n'en dépend pas).

Utilisation ::

    python scripts/generer_diagramme.py
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon, Rectangle  # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, "docs", "diagramme_classes.png")

LIGNE = 1.55          # hauteur d'une ligne de texte (unités du dessin)
POLICE = 7.2
COULEURS = {
    "modele": "#E8F1FB",
    "abstrait": "#FDF2E3",
    "service": "#EAF6EC",
    "interface": "#F3EDF9",
    "exception": "#FBE9E9",
}


class Boite:
    """Rectangle UML : nom, attributs et méthodes."""

    def __init__(self, ax, nom, x, y, largeur, attributs=(), methodes=(),
                 stereotype=None, couleur="modele"):
        """Dessine la boîte dont le coin supérieur gauche est (x, y)."""
        self.x, self.y, self.largeur = x, y, largeur
        entete = 2 if stereotype else 1
        self.h = LIGNE * (entete + len(attributs) + len(methodes)) + 1.2
        ax.add_patch(Rectangle((x, y - self.h), largeur, self.h,
                               facecolor=COULEURS[couleur],
                               edgecolor="#333333", linewidth=0.9))
        curseur = y - 0.9
        if stereotype:
            ax.text(x + largeur / 2, curseur, f"«{stereotype}»",
                    ha="center", va="center", fontsize=POLICE - 0.8,
                    style="italic")
            curseur -= LIGNE
        ax.text(x + largeur / 2, curseur, nom, ha="center", va="center",
                fontsize=POLICE + 1, weight="bold",
                style="italic" if stereotype == "abstract" else "normal")
        curseur -= LIGNE * 0.6
        for bloc in (attributs, methodes):
            ax.plot([x, x + largeur], [curseur, curseur], color="#333333",
                    linewidth=0.6)
            curseur -= LIGNE * 0.55
            for ligne in bloc:
                ax.text(x + 0.6, curseur - 0.2, ligne, ha="left",
                        va="center", fontsize=POLICE, family="monospace")
                curseur -= LIGNE
            curseur += LIGNE * 0.45

    def haut(self, decalage=0.0):
        """Point au milieu du bord supérieur (décalable)."""
        return (self.x + self.largeur / 2 + decalage, self.y)

    def bas(self, decalage=0.0):
        """Point au milieu du bord inférieur (décalable)."""
        return (self.x + self.largeur / 2 + decalage, self.y - self.h)

    def gauche(self, decalage=0.0):
        """Point au milieu du bord gauche."""
        return (self.x, self.y - self.h / 2 + decalage)

    def droite(self, decalage=0.0):
        """Point au milieu du bord droit."""
        return (self.x + self.largeur, self.y - self.h / 2 + decalage)


def fleche(ax, depart, arrivee, style="assoc", texte=None, coudes=()):
    """Relie deux points ; ``style`` : heritage, assoc, dep, compo, agreg.

    ``coudes`` est une liste de points intermédiaires (lignes brisées).
    """
    points = [depart, *coudes, arrivee]
    tirets = (0, (4, 3)) if style == "dep" else "solid"
    for (x1, y1), (x2, y2) in zip(points[:-1], points[1:]):
        ax.plot([x1, x2], [y1, y2], color="#333333", linewidth=0.9,
                linestyle=tirets)
    avant, fin = points[-2], points[-1]
    if style in ("heritage", "assoc", "dep"):
        ax.annotate(
            "", xy=fin, xytext=avant,
            arrowprops={
                "arrowstyle": "-|>" if style == "heritage" else "->",
                "edgecolor": "#333333", "lw": 0.9, "shrinkA": 0,
                "shrinkB": 0,
                "mutation_scale": 14 if style == "heritage" else 10,
                "facecolor": "white" if style == "heritage" else "#333333",
                "linestyle": tirets,
            })
    else:
        # Losange côté « tout » (point de départ).
        (x0, y0), (x1, y1) = points[0], points[1]
        dx, dy = x1 - x0, y1 - y0
        norme = (dx ** 2 + dy ** 2) ** 0.5 or 1
        ux, uy = dx / norme, dy / norme
        taille = 1.4
        losange = [(x0, y0),
                   (x0 + ux * taille - uy * taille * 0.5,
                    y0 + uy * taille + ux * taille * 0.5),
                   (x0 + 2 * ux * taille, y0 + 2 * uy * taille),
                   (x0 + ux * taille + uy * taille * 0.5,
                    y0 + uy * taille - ux * taille * 0.5)]
        ax.add_patch(Polygon(losange, closed=True, edgecolor="#333333",
                             facecolor="#333333" if style == "compo"
                             else "white", linewidth=0.9, zorder=3))
    if texte:
        mx = (avant[0] + fin[0]) / 2
        my = (avant[1] + fin[1]) / 2
        ax.text(mx + (0 if avant[1] == fin[1] else 0.5), my + 0.8, texte,
                fontsize=POLICE - 0.6, color="#555555", style="italic",
                ha="center" if avant[1] == fin[1] else "left")


def dessiner():
    """Construit la figure complète et l'enregistre en PNG."""
    fig, ax = plt.subplots(figsize=(17, 12.5))
    ax.set_xlim(0, 136)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # --- Interface ---------------------------------------------------
    menu = Boite(ax, "Menu", 40, 99, 26,
                 ["- bibliotheque", "- persistance", "- horloge"],
                 ["+ executer()", "+ sauvegarder()", "+ quitter()"],
                 couleur="interface")
    console = Boite(ax, "Console", 76, 99, 30, [],
                    ["+ demander_texte(msg) : str",
                     "+ demander_entier(msg, min, max)",
                     "+ demander_date(msg) : date",
                     "+ demander_choix(options) : str",
                     "+ tableau(entetes, lignes)"],
                    couleur="interface")

    # --- Services ----------------------------------------------------
    gestion = Boite(ax, "GestionnaireEmprunts", 1, 78, 37,
                    ["- bibliotheque : Bibliotheque",
                     "- horloge : callable"],
                    ["+ emprunter(id_lect, id_ouv, date) : Emprunt",
                     "+ retourner(id_emprunt, date) : int",
                     "+ retourner_exemplaire(id_ex, date)",
                     "+ prolonger(id_emprunt) : date",
                     "+ emprunts_en_retard(date) : list",
                     "+ historique(id_lect, id_ouv) : list"],
                    couleur="service")
    tableau = Boite(ax, "TableauBord", 42, 78, 31,
                    ["- bibliotheque : Bibliotheque"],
                    ["+ taux_occupation() : float",
                     "+ ouvrages_plus_empruntes(n)",
                     "+ lecteurs_en_retard(date)",
                     "+ statistiques(date) : dict",
                     "+ generer_rapport() : str"],
                    couleur="service")
    json_ = Boite(ax, "GestionnaireJSON", 77, 78, 28,
                  ["- dossier : str", "- avertissements : list"],
                  ["+ sauvegarder(bibliotheque)",
                   "+ charger() : Bibliotheque"],
                  couleur="service")
    biblio = Boite(ax, "Bibliotheque", 44, 55, 36,
                   ["+ ouvrages : dict", "+ lecteurs : dict",
                    "+ emprunts : dict", "+ compteurs : dict"],
                   ["+ ajouter/modifier/supprimer_ouvrage()",
                    "+ rechercher(champ, terme) : list",
                    "+ inscrire_etudiant/enseignant()",
                    "+ supprimer_lecteur(id)",
                    "+ nouvel_identifiant(type) : str",
                    "+ reconstruire_index() : int"],
                   couleur="service")

    # --- Modèles -----------------------------------------------------
    lecteur = Boite(ax, "Lecteur", 1, 46, 33,
                    ["+ id_lecteur, nom, prenom, email",
                     "+ emprunts_actifs : list",
                     "+ quota_max : int {abstrait}",
                     "+ duree_emprunt : int {abstrait}",
                     "+ type_lecteur : str {abstrait}"],
                    ["+ peut_emprunter() : bool",
                     "+ calculer_date_retour(d) : date",
                     "+ to_dict() / from_dict()"],
                    stereotype="abstract", couleur="abstrait")
    etudiant = Boite(ax, "Etudiant", 0, 20, 17,
                     ["quota_max = 3", "duree = 14 j", "filiere, niveau"],
                     [])
    enseignant = Boite(ax, "Enseignant", 19, 20, 17,
                       ["quota_max = 5", "duree = 30 j",
                        "departement, grade"], [])
    emprunt = Boite(ax, "Emprunt", 44, 26, 36,
                    ["+ id_emprunt, id_lecteur, id_exemplaire",
                     "+ date_emprunt, date_retour_prevue",
                     "+ date_retour_effective, prolonge",
                     "+ PENALITE_PAR_JOUR = 100"],
                    ["+ jours_retard(date) : int",
                     "+ calculer_penalite(date) : int",
                     "+ prolonger(nb_jours, date) : date",
                     "+ cloturer(date) : int"])
    ouvrage = Boite(ax, "Ouvrage", 84, 47.7, 30,
                    ["+ id_ouvrage, titre, auteur",
                     "+ isbn, categorie",
                     "+ exemplaires : list"],
                    ["+ ajouter_exemplaires(n) : list",
                     "+ retirer_exemplaire(id)",
                     "+ exemplaires_disponibles()",
                     "+ correspond(champ, terme)"])
    exemplaire = Boite(ax, "Exemplaire", 85, 24, 28,
                       ["+ id_exemplaire, id_ouvrage",
                        "+ disponible : bool"],
                       ["+ marquer_emprunte()", "+ marquer_rendu()"])

    # --- Exceptions ---------------------------------------------------
    erreurs = Boite(ax, "BibliothequeErreur", 115, 99, 20, [], [],
                    stereotype="exception", couleur="exception")
    noms = ["OuvrageIndisponible", "QuotaDepasse", "LecteurEnRetard",
            "ProlongationRefusee", "EmpruntDejaEnCours",
            "EmpruntDejaCloture", "DonneesInvalides", "DoublonErreur",
            "OperationImpossible", "ErreurPersistance",
            "OuvrageIntrouvable", "LecteurIntrouvable",
            "ExemplaireIntrouvable", "EmpruntIntrouvable"]
    x_tronc = 116.5
    haut = 88
    for i, nom in enumerate(noms):
        y_haut = haut - 3.9 * i
        ax.add_patch(Rectangle((118, y_haut - 2.8), 17, 2.8,
                               facecolor=COULEURS["exception"],
                               edgecolor="#333333", linewidth=0.8))
        ax.text(126.5, y_haut - 1.4, nom, ha="center", va="center",
                fontsize=POLICE)
        ax.plot([x_tronc, 118], [y_haut - 1.4, y_haut - 1.4],
                color="#333333", linewidth=0.9)
    fleche(ax, (x_tronc, haut - 3.9 * (len(noms) - 1) - 1.4),
           (x_tronc, erreurs.y - erreurs.h), "heritage")

    # --- Relations ---------------------------------------------------
    fleche(ax, etudiant.haut(), lecteur.bas(-6), "heritage")
    fleche(ax, enseignant.haut(), lecteur.bas(6), "heritage")
    fleche(ax, ouvrage.bas(), exemplaire.haut(), "compo",
           "1 — 1..*")
    fleche(ax, (emprunt.x + emprunt.largeur, exemplaire.y - 4),
           (exemplaire.x, exemplaire.y - 4), "assoc", "concerne")
    fleche(ax, emprunt.gauche(4), lecteur.bas(13), "assoc", "emprunteur",
           coudes=[(lecteur.x + lecteur.largeur / 2 + 13,
                    emprunt.y - emprunt.h / 2 + 4)])
    fleche(ax, biblio.gauche(-5), (lecteur.x + lecteur.largeur,
                                   biblio.y - biblio.h / 2 - 5),
           "agreg", "0..*")
    fleche(ax, biblio.bas(), emprunt.haut(), "agreg", "0..*")
    fleche(ax, biblio.droite(-5), (ouvrage.x,
                                   biblio.y - biblio.h / 2 - 5),
           "agreg", "0..*")
    fleche(ax, gestion.bas(), biblio.gauche(5), "assoc",
           coudes=[(gestion.x + gestion.largeur / 2,
                    biblio.y - biblio.h / 2 + 5)])
    fleche(ax, tableau.bas(), biblio.haut(), "assoc")
    fleche(ax, json_.bas(), biblio.droite(5), "dep", "sérialise",
           coudes=[(json_.x + json_.largeur / 2, biblio.y - biblio.h / 2 + 5)])
    fleche(ax, menu.bas(-8), gestion.haut(), "assoc",
           coudes=[(menu.x + menu.largeur / 2 - 8, 82),
                   (gestion.x + gestion.largeur / 2, 82)])
    fleche(ax, menu.bas(), tableau.haut(), "assoc")
    fleche(ax, menu.bas(8), json_.haut(), "assoc",
           coudes=[(menu.x + menu.largeur / 2 + 8, 81),
                   (json_.x + json_.largeur / 2, 81)])
    fleche(ax, menu.droite(), console.gauche(), "assoc")

    # --- Légende -----------------------------------------------------
    legende = [("Interface", "interface"), ("Services", "service"),
               ("Modèles", "modele"), ("Classe abstraite", "abstrait"),
               ("Exceptions", "exception")]
    for i, (libelle, cle) in enumerate(legende):
        ax.add_patch(Rectangle((40 + i * 19, 2), 2.5, 2,
                               facecolor=COULEURS[cle],
                               edgecolor="#333333", linewidth=0.6))
        ax.text(43.3 + i * 19, 3, libelle, va="center", fontsize=POLICE)
    ax.text(1, 3, "Diagramme de classes — Gestion d'une bibliothèque "
            "universitaire", fontsize=POLICE + 2, weight="bold",
            va="center")

    fig.tight_layout(pad=0.3)
    fig.savefig(SORTIE, dpi=150)
    plt.close(fig)
    return SORTIE


if __name__ == "__main__":
    print("Diagramme enregistré :", dessiner())
