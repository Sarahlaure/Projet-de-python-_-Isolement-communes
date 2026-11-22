Projet du cours **Python pour la data science** (ENSAE Paris, 2ᵉ année). Chargé de TD : M. DEREPAS Alban.

# Isolement des communes françaises

> À quelle distance de chez soi trouve-t-on les services du quotidien, et quelles communes sont les plus éloignées de tout ?

Nous mesurons, pour chacune des 34 788 communes et arrondissements de France métropolitaine, la distance à 19 services de base (boulangerie, pharmacie, médecin, école, poste, gare, urgences, maternité…) à partir de la Base permanente des équipements (BPE) 2025 de l'INSEE. Nous résumons ces distances dans un indice d'isolement, que nous cartographions et comparons à la densité de population et au revenu.

**Le rapport complet est en ligne : [sarahlaure.github.io/isolement-communes-livre](https://sarahlaure.github.io/isolement-communes-livre/).** Le notebook [`rapport.ipynb`](rapport.ipynb) contient l'analyse exécutable.

## Question de recherche et hypothèses

> Quelles communes sont les plus éloignées des services de base, et cet isolement va-t-il de pair avec une faible densité et un faible revenu ?

| | Hypothèse | Résultat |
|---|---|---|
| H1 | Les distances sont très asymétriques : la plupart des communes sont proches, une minorité est très éloignée. | Non confirmée : médiane et moyenne sont très proches pour presque tous les services. |
| H2 | Plus une commune est peu dense, plus elle est isolée. | Confirmée : ρ de Spearman = −0,84. |
| H3 | L'isolement est lié au revenu médian. | Partiellement confirmée : lien faible (ρ = −0,22), qui vient surtout de la densité. |
| H4 | Le classement ne dépend pas des choix de méthode. | Confirmée : corrélations de Spearman supérieures à 0,9 entre les 12 indices. |

## Méthodologie

1. **Panier de services** : 33 types d'équipements de la BPE regroupés en 19 services (dictionnaire `SERVICES` dans [`src/prepare_bpe.py`](src/prepare_bpe.py)).
2. **Distance** : pour chaque commune et chaque service, 0 si la commune possède le service ; sinon, distance à vol d'oiseau (Lambert-93) entre son centre et l'équipement le plus proche.
3. **Indice** : logarithme de la distance, standardisation par service, moyenne pondérée. Quatre jeux de poids (égaux, services vitaux, équilibre par thème, première composante de l'ACP) et trois règles de distance, soit 12 indices comparés par la corrélation de Spearman.
4. **Analyses** : distributions, population éloignée d'un service, cartes, lien avec la densité et le revenu (Spearman, Kruskal-Wallis), typologie en quatre groupes (k-means).
Le détail des choix est dans le rapport en ligne et dans [`docs/DATA_GUIDE.md`](docs/DATA_GUIDE.md).

## Données

| Source | Fichier | Téléchargement |
|---|---|---|
| INSEE, [BPE 2025](https://www.insee.fr/fr/statistiques/8217525) | `BPE25.parquet` et 4 fichiers de documentation | automatique (`src/download.py`) |
| INSEE / data.gouv | Population municipale 2023, géographie 2025 | à la main |
| IGN, [Admin Express](https://geoservices.ign.fr/adminexpress) | Contours COG 2025 (couches `COMMUNE` et `ARRONDISSEMENT_MUNICIPAL`) | à la main |
| INSEE | Filosofi, niveau de vie médian par commune (`MED_SL`) | à la main |

Les trois fichiers à récupérer à la main se placent dans `data/raw/`. La commande `python src/download.py` rappelle où les trouver et quoi choisir. Les données brutes ne sont pas versionnées (fichiers lourds). Les sources sont publiées sous licence ouverte.

## Structure du dépôt

```
.
├── README.md
├── requirements.txt        bibliothèques nécessaires
├── rapport.ipynb           le rapport : appelle src/ et raconte l'analyse
├── src/
│   ├── download.py         télécharge les fichiers INSEE dans data/raw/
│   ├── inspect_bpe.py      inspecte la BPE (colonnes, codes du panier)
│   ├── prepare_bpe.py      filtre la BPE sur le panier, écrit data/interim/
│   ├── communes.py         table des communes (centre, surface, population)
│   ├── distances.py        présence des services et distances
│   ├── indice.py           indice d'isolement
│   ├── descriptif.py       statistiques descriptives
│   └── analyse.py          revenu, corrélations, tests, typologie
├── tests/                  tests automatiques (pytest)
├── docs/
│   ├── DATA_GUIDE.md       sources, fusions, pièges
│   └── WORKFLOW_GIT.md     organisation du travail à trois
└── data/
    ├── raw/                données brutes, jamais modifiées (non versionnées)
    ├── interim/            données nettoyées (non versionnées)
    └── processed/          tableaux finaux, une ligne par commune (non versionnés)
```

## Reproduire les résultats

```bash
# 1. Récupérer le code
git clone https://github.com/Sarahlaure/Projet-de-python-_-Isolement-communes.git
cd Projet-de-python-_-Isolement-communes

# 2. Créer un environnement et installer les dépendances
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt

# 3. Télécharger les données INSEE (data/raw/)
python src/download.py
#    puis placer à la main dans data/raw/ : population, contours IGN, Filosofi

# 4. Nettoyer la BPE (data/interim/equipements.parquet)
python src/prepare_bpe.py

# 5. Ouvrir le rapport et tout exécuter (Run All)
jupyter lab
```

Lancer les tests : `pytest`.

## Résultats principaux

- 10 806 communes (31 %) n'ont aucun équipement du panier ; 59 % des communes ont un indice supérieur à la moyenne, mais elles ne regroupent que 9,9 % de la population.
- Les services rares sont loin de beaucoup d'habitants : 53,1 % de la population vit à plus de 5 km d'une maternité, contre 0,46 % pour une école.
- L'isolement est très fortement lié à la faible densité (ρ = −0,84) et beaucoup plus faiblement au niveau de vie (ρ = −0,22).
- Une typologie en quatre groupes décrit un gradient, des pôles très bien desservis (64 % de la population dans 9 % des communes) au rural isolé (37 % des communes pour 4,3 % de la population).

## Limites et quelques choix assumés

- Distance **à vol d'oiseau**, pas par la route ni en temps de trajet.
- La BPE mesure la **présence** d'un équipement, pas sa capacité ni ses horaires.
- **France métropolitaine seulement** : les DROM utilisent d'autres systèmes de coordonnées.
- Paris, Lyon et Marseille sont traitées **par arrondissement**, comme dans la BPE.
- Instantané 2025 : l'INSEE déconseille de comparer les millésimes de la BPE.
- Le niveau de vie n'est pas publié pour 11,4 % des communes, les plus isolées : l'analyse du revenu ne leur est pas applicable.

## Équipe

| Prénom NOM | GitHub |
|---|---|
| Sarah-Laure FOGWOUNG DJOUFACK | [Sarahlaure](https://github.com/Sarahlaure) |
| Célina NGUEMFOUO NGOUMTSA | [nncelina](https://github.com/nncelina) |
| Eytan ZAGHROUN | [Eytan-ZG](https://github.com/Eytan-ZG) |

## Usage d'outils d'IA

Nous avons utilisé un assistant d'IA (Claude) pour discuter de la méthode, relire le code et les textes, et mettre en forme le rapport en ligne. Les choix méthodologiques, les résultats et les textes ont été relus et validés par l'équipe, et le code est couvert par des tests automatiques.
