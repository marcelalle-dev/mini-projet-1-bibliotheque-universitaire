# Guide de soutenance — 15 minutes avec démonstration

## La veille

- [ ] Exporter la présentation en **PDF** ou **PowerPoint** (menu Partager › Exporter)
      pour pouvoir la projeter sans connexion.
- [ ] Vérifier que le projet tourne sur la machine de soutenance :
      `python --version` (3.10 ou plus), puis `python -m unittest discover -s tests -t .`
      (attendu : `Ran 62 tests ... OK`).
- [ ] Ouvrir `docs/rapport.pdf` une fois pour s'assurer qu'il s'affiche.

## Le jour même, juste avant de passer

1. Régénérer les données pour que les dates soient relatives au jour :

   ```
   python scripts/generer_donnees_demo.py --force
   ```

2. Ouvrir un terminal dans le dossier du projet, police agrandie (Ctrl + molette),
   fenêtre d'au moins 100 colonnes.
3. Garder la présentation ouverte sur la diapositive 1, le terminal prêt à côté.

## Déroulé minuté

| Temps | Diapositives | Contenu |
|---|---|---|
| 0:00 – 0:50 | 1 – 2 | Présentation, plan |
| 0:50 – 2:40 | 3 – 4 | Besoins, règles de gestion |
| 2:40 – 5:10 | 5 – 7 | Couches, diagramme UML, héritage |
| 5:10 – 7:20 | 8 – 10 | Contrôles d'emprunt, pénalités, persistance |
| 7:20 – 12:20 | 11 | **Démonstration** |
| 12:20 – 14:30 | 12 – 14 | Tests, difficultés, bilan |
| 14:30 – 15:00 | 15 | Questions |

## Démonstration pas à pas (vérifiée sur des données régénérées)

Lancer `python main.py`, puis :

| Étape | Saisies | Résultat attendu |
|---|---|---|
| 1. Tableau de bord | `6` | Taux d'occupation 45.45 %, top 5, 3 lecteurs en retard |
| 2. Quota atteint | `3`, `1`, `LEC-0001`, `OUV-0005`, Entrée | « a atteint son quota de 3 emprunts simultanés » |
| 3. Ouvrage indisponible | `1`, `LEC-0004`, `OUV-0004`, Entrée | « Bases de données (OUV-0004) n'a aucun exemplaire disponible » |
| 4. Lecteur en retard | `1`, `LEC-0007`, `OUV-0005`, Entrée, puis `0` | « a 1 emprunt(s) en retard : nouvel emprunt refusé » |
| 5. Retour en retard | `4`, `EMP-0013`, Entrée | « Retard de 11 jour(s) : pénalité de 1100 FCFA » |
| 6. Prolongation | `5`, `EMP-0021`, puis à nouveau `5`, `EMP-0021` | Prolongé, puis « a déjà été prolongé une fois » |
| 7. Saisie invalide | `abc` | « Choix invalide », pas de plantage |
| 8. Persistance | `9`, relancer `python main.py`, `6` | Emprunts en retard : 3 (au lieu de 4) ; pénalités facturées : 3800 FCFA (au lieu de 2700) |

Si le temps manque : sauter l'étape 3. En cas d'erreur de saisie, laisser le champ
vide pour annuler et revenir au menu.

## Questions probables

**Pourquoi une classe abstraite plutôt qu'un attribut « type » ?**
Les règles (quota, durée) sont portées par chaque sous-classe : les services
appellent `lecteur.peut_emprunter()` sans jamais tester le type. Ajouter un type de
lecteur ne demande qu'une sous-classe, sans modifier les services.

**Pourquoi distinguer ouvrage et exemplaire ?**
L'ouvrage est la notice (titre, ISBN) ; l'exemplaire est la copie physique. Un
emprunt vise un exemplaire précis : on sait quelle copie est chez quel lecteur, et
un titre peut avoir 3 copies dont 2 prêtées.

**Que se passe-t-il si un fichier JSON est corrompu ?**
Il est renommé (`.corrompu-<date>`), jamais écrasé, et la copie `.bak` est utilisée
si elle est valide ; un message l'indique au démarrage. C'est couvert par deux tests.

**Comment testez-vous des calculs qui dépendent de la date du jour ?**
Les services reçoivent une horloge injectable ; les tests utilisent une horloge
simulée qu'ils avancent jour par jour.

**Pourquoi le jour de l'échéance n'est-il pas en retard ?**
Choix d'analyse : la date de retour prévue est incluse. Le retard commence le
lendemain ; c'est testé explicitement.

**Pourquoi JSON plutôt qu'une base de données ?**
Exigé par le sujet, lisible et sans dépendance. SQLite est une piste d'évolution
pour de gros volumes.

**Avez-vous utilisé des outils d'IA ?**
Oui : Claude Code a assisté la conception, le code, les tests et la documentation.
C'est indiqué dans le rapport et dans chaque commit (`Co-Authored-By`).
