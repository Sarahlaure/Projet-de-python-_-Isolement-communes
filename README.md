# Isolement des communes françaises

> À quelle distance de chez soi trouve-t-on les services du quotidien, et quelles communes sont les plus éloignées de tout ?

Projet du cours **Python pour la data science** (ENSAE). Nous mesurons, pour chaque commune de France métropolitaine, la distance à 19 services de base (boulangerie, pharmacie, médecin, école, poste, gare…) à partir de la Base permanente des équipements (BPE) de l'INSEE, puis nous les résumons dans un indice d'isolement, cartographié et mis en relation avec la densité et le revenu.


## Question de recherche et hypothèses

> Quelles communes sont les plus éloignées des services de base, et cet isolement va-t-il de pair avec une faible densité et un faible revenu ?

| | Hypothèse | Outil |
|---|---|---|
| H1 | L'isolement est très inégal : la plupart des communes sont proches des services, une minorité est très éloignée. | quantiles, histogrammes |
| H2 | Plus une commune est peu dense, plus elle est isolée. | corrélation de Spearman |
| H3 | Les communes isolées forment des zones continues. | cartes, I de Moran (bonus) |
| H4 | Le lien avec le revenu médian est à tester (positif, négatif ou nul). | comparaison par groupes, Kruskal-Wallis |


## Méthodologie

## Données

| Source | Fichier | Récupération |
|---|---|---|
| INSEE, [BPE 2025](https://www.insee.fr/fr/statistiques/8217525) | `BPE25.parquet` et 4 fichiers de documentation | automatique (`src/download.py`) |
| INSEE / data.gouv | Population municipale 2023, géographie 2025 | à la main |
| IGN, [Admin Express](https://geoservices.ign.fr/adminexpress) | Contours COG 2025 (communes et arrondissements municipaux) | à la main |
| INSEE | Filosofi, revenu médian par commune | à la main |


## Structure du dépôt

```
isolement-communes/
├── README.md
├── requirements.txt        bibliothèques nécessaires
├── rapport.ipynb           le rapport : appelle src/ 
├── src/
│   ├── download.py         télécharge les fichiers INSEE dans data/raw/
│   ├── inspect_bpe.py      inspecte la BPE 
│   ├── prepare_bpe.py      filtre la BPE sur le panier
│   └── distances.py        distance au plus proche équipement 
├── tests/                  tests automatiques (pytest)
└── data/
    ├── raw/                données brutes, jamais modifiées (non versionnées)
    ├── interim/            données nettoyées (non versionnées)
    └── processed/          tableaux finaux, une ligne par commune (non versionnés)
```

## Choix assumés et limites


## Équipe

Projet réalisé dans le cadre du cours de Python de 2ᵉ année à l'ENSAE Paris.

- [FOGWOUNG DJOUFACK Sarah-Laure](https://github.com/Sarahlaure)
- [NGUEMFOUO NGOUMTSA Célina](https://github.com/nncelina)
- [ZAGHROUN Eytan](https://github.com/Eytan-ZG)

## Usage d'outils d'IA
