# Euromillions

Projet d'analyse data et de prédictions de tirages Euromillions.

## Technos

* JupyterLab (Anaconda)
* Python
* Pandas
* ChatGPT Codex

## ✅ Fait

* Téléchargement des fichiers CSV.
* Nettoyage, création/suppression de colonnes, uniformisation du format des dates des fichiers CSV.
* Fusion des fichiers CSV : un seul fichier de travail (_csv/global.csv_).
* Fonction de vérification des tirages déjà sortis.
* Affichage des derniers numéros et étoiles sortis (dans les 5 et 10 derniers tirages).
* Analyse des suites de numéros.
* Analyse des dizaines.

## ⌛TODO

* Statistiques et prédictions.

## Analyse de structure des tirages

Le script `analyse_structure_tirages.py` permet d'isoler une **structure type** des tirages à partir des **5 boules uniquement**. Les étoiles sont volontairement exclues pour pouvoir appliquer ensuite cette structure aux statistiques déjà dégagées sur les numéros et les dizaines.

La structure principale regroupe chaque combinaison par :

* répartition par dizaines (`1-9`, `10-19`, `20-29`, `30-39`, `40-49`, `50`) ;
* nombre de boules paires ;
* nombre de boules basses (`1-25`) ;
* présence de suites consécutives.

Une signature plus fine est aussi calculée pour qualifier une combinaison précise : tranche de somme des 5 boules et profil des écarts entre les numéros triés.

### Exemples d'utilisation

Afficher les 10 structures les plus fréquentes :

```bash
python analyse_structure_tirages.py --top 10
```

Comparer une combinaison à l'historique :

```bash
python analyse_structure_tirages.py --combo "1-13-34-36-47"
```

Pour chaque structure trouvée, le script affiche :

* le nombre d'occurrences historiques ;
* un exemple de tirage correspondant ;
* les numéros les plus sortis dans cette structure ;
* les dizaines dominantes dans cette structure.
