"""Entrées/sorties console contrôlées.

La classe :class:`Console` encapsule ``input`` et ``print`` : toutes les
saisies sont validées et redemandées en cas d'erreur, et les fonctions
d'entrée/sortie sont injectables, ce qui rend le menu testable.
"""

from datetime import datetime

LARGEUR = 78
LARGEUR_TABLEAU = 100


class SaisieAnnulee(Exception):
    """L'utilisateur a laissé un champ obligatoire vide pour annuler."""


class FinDeSaisie(Exception):
    """L'entrée standard est fermée (Ctrl+Z / Ctrl+D) : il faut quitter."""


class Console:
    """Affichage et saisies contrôlées en mode texte.

    Args:
        entree: fonction de lecture d'une ligne (``input`` par défaut).
        sortie: fonction d'affichage (``print`` par défaut).
    """

    def __init__(self, entree=input, sortie=print):
        """Initialise la console avec ses fonctions d'entrée/sortie."""
        self._entree = entree
        self._sortie = sortie

    # ------------------------------------------------------------------
    # Affichage
    # ------------------------------------------------------------------
    def afficher(self, texte=""):
        """Affiche une ligne de texte."""
        self._sortie(texte)

    def titre(self, texte):
        """Affiche un titre encadré."""
        self._sortie("")
        self._sortie("=" * LARGEUR)
        self._sortie(f" {texte}")
        self._sortie("=" * LARGEUR)

    def succes(self, texte):
        """Affiche un message de réussite."""
        self._sortie(f"[OK] {texte}")

    def erreur(self, texte):
        """Affiche un message d'erreur."""
        self._sortie(f"[ERREUR] {texte}")

    def info(self, texte):
        """Affiche un message d'information."""
        self._sortie(f"[i] {texte}")

    def tableau(self, entetes, lignes, vide="(aucun élément)"):
        """Affiche des lignes sous forme de tableau aligné.

        Les cellules trop longues sont tronquées pour tenir sur la
        largeur de la console.
        """
        if not lignes:
            self._sortie(f"  {vide}")
            return
        lignes = [[str(c) for c in ligne] for ligne in lignes]
        largeurs = [
            max(len(str(entetes[i])), *(len(lg[i]) for lg in lignes))
            for i in range(len(entetes))
        ]
        # Réduit la colonne la plus large tant que le tableau déborde.
        while sum(largeurs) + 3 * (len(largeurs) - 1) > LARGEUR_TABLEAU:
            plus_large = largeurs.index(max(largeurs))
            if largeurs[plus_large] <= 8:
                break
            largeurs[plus_large] -= 1

        def formater(cellules):
            return " | ".join(
                self._tronquer(c, n).ljust(n)
                for c, n in zip(cellules, largeurs)
            ).rstrip()

        self._sortie(formater([str(e) for e in entetes]))
        self._sortie("-+-".join("-" * n for n in largeurs))
        for ligne in lignes:
            self._sortie(formater(ligne))

    @staticmethod
    def _tronquer(texte, largeur):
        """Tronque ``texte`` à ``largeur`` caractères avec « … »."""
        return texte if len(texte) <= largeur else texte[:largeur - 1] + "…"

    # ------------------------------------------------------------------
    # Saisies
    # ------------------------------------------------------------------
    def lire(self, message):
        """Lit une ligne brute (espaces de bord supprimés).

        Raises:
            FinDeSaisie: si l'entrée standard est fermée.
        """
        try:
            return self._entree(message).strip()
        except EOFError as erreur:
            raise FinDeSaisie() from erreur

    def demander_texte(self, message, obligatoire=True, defaut=None):
        """Demande un texte.

        Args:
            obligatoire: si ``True``, une réponse vide annule l'opération.
            defaut: valeur retournée si la réponse est vide (affichée
                entre crochets) ; prioritaire sur ``obligatoire``.

        Raises:
            SaisieAnnulee: champ obligatoire laissé vide.
        """
        suffixe = f" [{defaut}]" if defaut not in (None, "") else ""
        valeur = self.lire(f"{message}{suffixe} : ")
        if valeur:
            return valeur
        if defaut is not None:
            return defaut
        if obligatoire:
            raise SaisieAnnulee()
        return ""

    def demander_entier(self, message, minimum=None, maximum=None,
                        defaut=None):
        """Demande un entier compris entre ``minimum`` et ``maximum``.

        La question est reposée tant que la saisie est incorrecte ; une
        réponse vide retourne ``defaut`` ou annule l'opération.
        """
        while True:
            brut = self.demander_texte(
                message, defaut=None if defaut is None else str(defaut)
            )
            try:
                valeur = int(brut)
            except ValueError:
                self.erreur(f"« {brut} » n'est pas un nombre entier.")
                continue
            if minimum is not None and valeur < minimum:
                self.erreur(f"La valeur doit être supérieure ou égale à "
                            f"{minimum}.")
            elif maximum is not None and valeur > maximum:
                self.erreur(f"La valeur doit être inférieure ou égale à "
                            f"{maximum}.")
            else:
                return valeur

    def demander_date(self, message):
        """Demande une date ``JJ/MM/AAAA`` ; vide = ``None`` (aujourd'hui).

        La question est reposée tant que la date est invalide.
        """
        while True:
            brut = self.lire(f"{message} (JJ/MM/AAAA, vide = aujourd'hui) : ")
            if not brut:
                return None
            try:
                return datetime.strptime(brut, "%d/%m/%Y").date()
            except ValueError:
                self.erreur(f"« {brut} » n'est pas une date valide.")

    def demander_choix(self, options, message="Votre choix"):
        """Affiche un menu numéroté et retourne la clé choisie.

        Args:
            options: liste de couples ``(cle, libelle)``. Les clés sont
                des chaînes saisies telles quelles par l'utilisateur.
        """
        for cle, libelle in options:
            self._sortie(f"  {cle:>2}. {libelle}")
        cles = [cle for cle, _ in options]
        while True:
            choix = self.lire(f"{message} : ")
            if choix in cles:
                return choix
            self.erreur(f"Choix invalide. Options possibles : "
                        f"{', '.join(cles)}.")

    def confirmer(self, message):
        """Pose une question fermée ; retourne ``True`` pour oui."""
        while True:
            reponse = self.lire(f"{message} (o/n) : ").lower()
            if reponse in ("o", "oui", "y", "yes"):
                return True
            if reponse in ("n", "non", "no", ""):
                return False
            self.erreur("Répondez par « o » ou « n ».")

    def pause(self):
        """Attend que l'utilisateur appuie sur Entrée."""
        self.lire("\nAppuyez sur Entrée pour continuer...")
