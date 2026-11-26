"""Indicateurs du tableau de bord de la bibliothèque."""

from collections import Counter
from datetime import date


class TableauBord:
    """Calcule les statistiques de pilotage à partir d'une bibliothèque.

    Args:
        bibliotheque: état à analyser.
        horloge: fonction retournant la date du jour (injectable).
    """

    def __init__(self, bibliotheque, horloge=date.today):
        """Associe le tableau de bord à une bibliothèque."""
        self.bibliotheque = bibliotheque
        self.horloge = horloge

    # ------------------------------------------------------------------
    # Fonds documentaire
    # ------------------------------------------------------------------
    def nb_ouvrages(self):
        """Nombre de titres distincts au catalogue."""
        return len(self.bibliotheque.ouvrages)

    def nb_exemplaires(self):
        """Nombre total d'exemplaires physiques."""
        return sum(o.nb_exemplaires
                   for o in self.bibliotheque.ouvrages.values())

    def nb_exemplaires_disponibles(self):
        """Nombre d'exemplaires actuellement en rayon."""
        return sum(o.nb_disponibles
                   for o in self.bibliotheque.ouvrages.values())

    def nb_exemplaires_empruntes(self):
        """Nombre d'exemplaires actuellement prêtés."""
        return sum(o.nb_empruntes
                   for o in self.bibliotheque.ouvrages.values())

    def taux_occupation(self):
        """Pourcentage du fonds actuellement emprunté.

        Formule : exemplaires empruntés / total des exemplaires × 100,
        arrondi à 2 décimales ; 0 si la bibliothèque est vide.
        """
        total = self.nb_exemplaires()
        if total == 0:
            return 0.0
        return round(self.nb_exemplaires_empruntes() / total * 100, 2)

    # ------------------------------------------------------------------
    # Classements
    # ------------------------------------------------------------------
    def ouvrages_plus_empruntes(self, limite=5):
        """Ouvrages classés par nombre total d'emprunts (historique).

        Returns:
            list: tuples ``(id_ouvrage, titre, nombre_emprunts)`` triés par
            nombre décroissant puis par titre ; les ouvrages jamais
            empruntés sont exclus.
        """
        compteur = Counter(e.id_ouvrage
                           for e in self.bibliotheque.emprunts.values())
        classement = [
            (id_ouvrage, self.bibliotheque.libelle_ouvrage(id_ouvrage), n)
            for id_ouvrage, n in compteur.items()
        ]
        classement.sort(key=lambda t: (-t[2], t[1].casefold()))
        return classement[:limite]

    def lecteurs_en_retard(self, date_reference=None):
        """Lecteurs ayant au moins un emprunt en cours en retard.

        Returns:
            list: dictionnaires ``{"lecteur", "emprunts", "jours_retard",
            "penalite"}`` triés par pénalité décroissante.
        """
        reference = date_reference or self.horloge()
        par_lecteur = {}
        for emprunt in self.bibliotheque.emprunts.values():
            if emprunt.est_en_retard(reference):
                par_lecteur.setdefault(emprunt.id_lecteur, []).append(emprunt)
        resultats = []
        for id_lecteur, emprunts in par_lecteur.items():
            resultats.append({
                "id_lecteur": id_lecteur,
                "lecteur": self.bibliotheque.lecteurs.get(id_lecteur),
                "nom": self.bibliotheque.libelle_lecteur(id_lecteur),
                "emprunts": emprunts,
                "jours_retard": max(e.jours_retard(reference)
                                    for e in emprunts),
                "penalite": sum(e.calculer_penalite(reference)
                                for e in emprunts),
            })
        resultats.sort(key=lambda r: (-r["penalite"], r["nom"]))
        return resultats

    # ------------------------------------------------------------------
    # Synthèse
    # ------------------------------------------------------------------
    def statistiques(self, date_reference=None):
        """Retourne l'ensemble des indicateurs sous forme de dictionnaire."""
        reference = date_reference or self.horloge()
        emprunts = list(self.bibliotheque.emprunts.values())
        actifs = [e for e in emprunts if e.est_actif]
        lecteurs = list(self.bibliotheque.lecteurs.values())
        return {
            "date": reference,
            "nb_ouvrages": self.nb_ouvrages(),
            "nb_exemplaires": self.nb_exemplaires(),
            "nb_disponibles": self.nb_exemplaires_disponibles(),
            "nb_empruntes": self.nb_exemplaires_empruntes(),
            "taux_occupation": self.taux_occupation(),
            "nb_lecteurs": len(lecteurs),
            "nb_etudiants": sum(1 for lec in lecteurs
                                if lec.TYPE == "etudiant"),
            "nb_enseignants": sum(1 for lec in lecteurs
                                  if lec.TYPE == "enseignant"),
            "nb_emprunts_total": len(emprunts),
            "nb_emprunts_actifs": len(actifs),
            "nb_emprunts_en_retard": sum(1 for e in actifs
                                         if e.est_en_retard(reference)),
            "penalites_en_cours": sum(e.calculer_penalite(reference)
                                      for e in actifs),
            "penalites_encaissees": sum(e.penalite_payee for e in emprunts
                                        if not e.est_actif),
        }

    def generer_rapport(self, date_reference=None, limite=5):
        """Retourne le tableau de bord mis en forme pour la console."""
        stats = self.statistiques(date_reference)
        lignes = [
            f"Situation au {stats['date']:%d/%m/%Y}",
            "",
            "FONDS DOCUMENTAIRE",
            f"  Ouvrages (titres distincts) : {stats['nb_ouvrages']}",
            f"  Exemplaires au total        : {stats['nb_exemplaires']}",
            f"  Exemplaires disponibles     : {stats['nb_disponibles']}",
            f"  Exemplaires empruntés       : {stats['nb_empruntes']}",
            f"  Taux d'occupation du fonds  : "
            f"{stats['taux_occupation']:.2f} %",
            "",
            "LECTEURS ET PRÊTS",
            f"  Lecteurs inscrits           : {stats['nb_lecteurs']} "
            f"({stats['nb_etudiants']} étudiants, "
            f"{stats['nb_enseignants']} enseignants)",
            f"  Emprunts enregistrés        : {stats['nb_emprunts_total']}",
            f"  Emprunts en cours           : {stats['nb_emprunts_actifs']}",
            f"  Emprunts en retard          : "
            f"{stats['nb_emprunts_en_retard']}",
            f"  Pénalités en cours          : "
            f"{stats['penalites_en_cours']} FCFA",
            f"  Pénalités facturées (rendus): "
            f"{stats['penalites_encaissees']} FCFA",
            "",
            f"TOP {limite} DES OUVRAGES LES PLUS EMPRUNTÉS",
        ]
        top = self.ouvrages_plus_empruntes(limite)
        if not top:
            lignes.append("  (aucun emprunt enregistré)")
        for rang, (id_ouvrage, titre, nombre) in enumerate(top, start=1):
            lignes.append(f"  {rang}. {titre} [{id_ouvrage}] — "
                          f"{nombre} emprunt(s)")
        lignes += ["", "LECTEURS EN RETARD"]
        retards = self.lecteurs_en_retard(stats["date"])
        if not retards:
            lignes.append("  (aucun lecteur en retard)")
        for info in retards:
            details = ", ".join(
                f"{e.id_emprunt} ({e.jours_retard(stats['date'])} j)"
                for e in info["emprunts"]
            )
            lignes.append(f"  - {info['nom']} [{info['id_lecteur']}] : "
                          f"{details} → {info['penalite']} FCFA")
        return "\n".join(lignes)
