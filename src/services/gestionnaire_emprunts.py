"""Service de gestion des prêts : emprunt, retour, prolongation, retards."""

from datetime import date

from src.exceptions import (
    DonneesInvalides,
    EmpruntDejaCloture,
    EmpruntDejaEnCours,
    EmpruntIntrouvable,
    LecteurEnRetard,
    OuvrageIndisponible,
    QuotaDepasse,
)
from src.models import Emprunt


class GestionnaireEmprunts:
    """Applique les règles de prêt sur une :class:`Bibliotheque`.

    Args:
        bibliotheque: état sur lequel opérer.
        horloge: fonction sans argument retournant la date du jour ;
            remplaçable dans les tests pour simuler le passage du temps.
    """

    def __init__(self, bibliotheque, horloge=date.today):
        """Associe le gestionnaire à une bibliothèque et à une horloge."""
        self.bibliotheque = bibliotheque
        self.horloge = horloge

    # ------------------------------------------------------------------
    # Opérations
    # ------------------------------------------------------------------
    def emprunter(self, id_lecteur, id_ouvrage, date_emprunt=None):
        """Prête un exemplaire disponible de l'ouvrage au lecteur.

        Vérifications, dans l'ordre : existence du lecteur et de
        l'ouvrage, absence de retard, quota, ouvrage non déjà détenu par
        le lecteur, disponibilité d'un exemplaire.

        Args:
            date_emprunt: date du prêt (aujourd'hui par défaut, jamais
                dans le futur).

        Returns:
            Emprunt: l'emprunt créé.

        Raises:
            LecteurIntrouvable, OuvrageIntrouvable: identifiant inconnu.
            DonneesInvalides: date d'emprunt dans le futur.
            LecteurEnRetard: le lecteur a un prêt en retard.
            QuotaDepasse: le lecteur a atteint son quota.
            EmpruntDejaEnCours: le lecteur détient déjà cet ouvrage.
            OuvrageIndisponible: aucun exemplaire en rayon.
        """
        biblio = self.bibliotheque
        lecteur = biblio.obtenir_lecteur(id_lecteur)
        ouvrage = biblio.obtenir_ouvrage(id_ouvrage)
        date_emprunt = self._date_valide(date_emprunt)

        retards = [e for e in self.emprunts_du_lecteur(lecteur.id_lecteur)
                   if e.est_en_retard(date_emprunt)]
        if retards:
            raise LecteurEnRetard(lecteur, len(retards))
        if not lecteur.peut_emprunter():
            raise QuotaDepasse(lecteur)
        if any(e.id_ouvrage == ouvrage.id_ouvrage
               for e in self.emprunts_du_lecteur(lecteur.id_lecteur)):
            raise EmpruntDejaEnCours(
                f"{lecteur.nom_complet} détient déjà un exemplaire de "
                f"« {ouvrage.titre} »."
            )
        exemplaire = ouvrage.premier_exemplaire_disponible()
        if exemplaire is None:
            raise OuvrageIndisponible(ouvrage)

        emprunt = Emprunt(
            biblio.nouvel_identifiant("emprunt"),
            lecteur.id_lecteur,
            ouvrage.id_ouvrage,
            exemplaire.id_exemplaire,
            date_emprunt,
            lecteur.calculer_date_retour(date_emprunt),
        )
        exemplaire.marquer_emprunte()
        lecteur.enregistrer_emprunt(emprunt.id_emprunt)
        biblio.emprunts[emprunt.id_emprunt] = emprunt
        return emprunt

    def retourner(self, id_emprunt, date_retour=None):
        """Enregistre le retour d'un emprunt et retourne la pénalité due.

        Raises:
            EmpruntIntrouvable: identifiant inconnu.
            EmpruntDejaCloture: emprunt déjà rendu.
            DonneesInvalides: date dans le futur ou avant l'emprunt.
        """
        emprunt = self.bibliotheque.obtenir_emprunt(id_emprunt)
        if not emprunt.est_actif:
            raise EmpruntDejaCloture(
                f"L'emprunt {emprunt.id_emprunt} a déjà été rendu le "
                f"{emprunt.date_retour_effective:%d/%m/%Y}."
            )
        date_retour = self._date_valide(date_retour)
        if date_retour < emprunt.date_emprunt:
            raise DonneesInvalides(
                "La date de retour ne peut pas précéder la date d'emprunt "
                f"({emprunt.date_emprunt:%d/%m/%Y})."
            )
        penalite = emprunt.cloturer(date_retour)
        ouvrage = self.bibliotheque.ouvrages.get(emprunt.id_ouvrage)
        if ouvrage is not None:
            ouvrage.trouver_exemplaire(emprunt.id_exemplaire).marquer_rendu()
        lecteur = self.bibliotheque.lecteurs.get(emprunt.id_lecteur)
        if lecteur is not None:
            lecteur.liberer_emprunt(emprunt.id_emprunt)
        return penalite

    def retourner_exemplaire(self, id_exemplaire, date_retour=None):
        """Retour à partir de l'identifiant de l'exemplaire rapporté.

        Returns:
            tuple: ``(emprunt, penalite)``.

        Raises:
            EmpruntIntrouvable: aucun prêt en cours pour cet exemplaire.
        """
        cle = self.bibliotheque.normaliser_identifiant(id_exemplaire)
        for emprunt in self.emprunts_actifs():
            if emprunt.id_exemplaire == cle:
                return emprunt, self.retourner(emprunt.id_emprunt,
                                               date_retour)
        raise EmpruntIntrouvable(f"en cours pour l'exemplaire {cle}")

    def prolonger(self, id_emprunt):
        """Prolonge un emprunt d'une durée égale à celle du lecteur.

        Une seule prolongation est permise, et seulement si l'emprunt
        n'est pas déjà en retard.

        Returns:
            date: la nouvelle date de retour prévue.

        Raises:
            EmpruntIntrouvable, EmpruntDejaCloture, ProlongationRefusee.
        """
        emprunt = self.bibliotheque.obtenir_emprunt(id_emprunt)
        lecteur = self.bibliotheque.lecteurs.get(emprunt.id_lecteur)
        duree = lecteur.duree_emprunt if lecteur is not None else 14
        return emprunt.prolonger(duree, self.horloge())

    # ------------------------------------------------------------------
    # Consultations
    # ------------------------------------------------------------------
    def emprunts_actifs(self):
        """Emprunts non rendus, du plus ancien au plus récent."""
        return sorted(
            (e for e in self.bibliotheque.emprunts.values() if e.est_actif),
            key=lambda e: (e.date_emprunt, e.id_emprunt),
        )

    def emprunts_du_lecteur(self, id_lecteur, actifs_seulement=True):
        """Emprunts d'un lecteur (en cours uniquement par défaut)."""
        cle = self.bibliotheque.normaliser_identifiant(id_lecteur)
        return [e for e in self.historique()
                if e.id_lecteur == cle
                and (e.est_actif or not actifs_seulement)]

    def emprunts_en_retard(self, date_reference=None):
        """Emprunts en cours dont la date limite est dépassée."""
        reference = date_reference or self.horloge()
        return [e for e in self.emprunts_actifs()
                if e.est_en_retard(reference)]

    def historique(self, id_lecteur=None, id_ouvrage=None):
        """Historique complet des emprunts, du plus ancien au plus récent,
        éventuellement filtré par lecteur et/ou par ouvrage."""
        normaliser = self.bibliotheque.normaliser_identifiant
        emprunts = sorted(self.bibliotheque.emprunts.values(),
                          key=lambda e: (e.date_emprunt, e.id_emprunt))
        if id_lecteur:
            emprunts = [e for e in emprunts
                        if e.id_lecteur == normaliser(id_lecteur)]
        if id_ouvrage:
            emprunts = [e for e in emprunts
                        if e.id_ouvrage == normaliser(id_ouvrage)]
        return emprunts

    def penalite_en_cours(self, id_emprunt, date_reference=None):
        """Pénalité qui serait due si l'emprunt était rendu ce jour."""
        emprunt = self.bibliotheque.obtenir_emprunt(id_emprunt)
        return emprunt.calculer_penalite(date_reference or self.horloge())

    # ------------------------------------------------------------------
    # Outils internes
    # ------------------------------------------------------------------
    def _date_valide(self, valeur):
        """Retourne ``valeur`` ou la date du jour ; refuse le futur."""
        aujourd_hui = self.horloge()
        valeur = valeur or aujourd_hui
        if valeur > aujourd_hui:
            raise DonneesInvalides(
                f"La date {valeur:%d/%m/%Y} est dans le futur."
            )
        return valeur
