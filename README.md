# Isolement des communes de la France métropolitaine

> À quelle distance de chez soi trouve-t-on les services du quotidien, quelles communes sont les plus éloignées de tout, et la réponse dépend-elle de la façon de mesurer ?

Projet du cours **Python pour la data science** (ENSAE Paris, 2ᵉ année). Chargé de TD : M. DEREPAS Alban.

[Rapport en ligne](https://sarahlaure.github.io/isolement-communes-livre/) · [Notebook](rapport.ipynb) · [Tableau de bord](dashboard/index.html) ·

Nous mesurons, pour chacune des 34 788 communes et arrondissements de France métropolitaine, la distance à 19 services de base (boulangerie, pharmacie, médecin, école, poste, gare, urgences, maternité…) à partir de la Base permanente des équipements (BPE) 2025 de l'INSEE. Nous résumons ces distances par **trois indices d'isolement** (méthodes A, B et C), que nous cartographions, comparons entre eux et mettons en relation avec la densité de population et le revenu.

**Le rapport complet est en ligne : [sarahlaure.github.io/isolement-communes-livre](https://sarahlaure.github.io/isolement-communes-livre/).** Le notebook [`rapport.ipynb`](rapport.ipynb) contient l'analyse exécutable, et le dossier [`dashboard/`](dashboard/) un tableau de bord interactif.

## Question de recherche et hypothèses

> Quelles communes sont les plus éloignées des services de base ? Cet isolement va-t-il de pair avec une faible densité et un faible revenu ? Et ces conclusions dépendent-elles de la manière de mesurer l'isolement ?

| | Hypothèse | Résultat |
|---|---|---|
| H1 | L'isolement est très inégal : la plupart des habitants sont proches des services, une minorité de communes en est très éloignée. | Partiellement confirmée : l'inégalité oppose surtout les équipements rares aux services du quotidien, et le nombre de communes au nombre d'habitants. |
| H2 | Plus une commune est peu dense, plus elle est isolée. | Confirmée avec les trois méthodes : ρ de Spearman = −0,84 (A), −0,83 (B), −0,84 (C). |
| H3 | L'isolement est lié au revenu médian. | Dépend de la méthode : faible et porté par la densité avec A et B (ρ ≈ −0,21), plus net avec C (ρ = −0,31), où il subsiste à densité comparable. |
| H4 | Le classement dépend peu de la méthode. | Confirmée pour le classement d'ensemble (Spearman de 0,98 entre A et B, 0,95 entre B et C), moins pour la liste des communes les plus isolées. |

## Les trois méthodes

| | Méthode A | Méthode B | Méthode C |
|---|---|---|---|
| Point de départ | centroïde de la commune | chef-lieu de la commune | chef-lieu de la commune |
| Service présent dans la commune | distance mise à 0 | distance réelle | distance réelle |
| Agrégation | 19 services de poids égal | 19 services pondérés par une grille (essentialité, fréquence d'usage, public concerné) | 6 grands besoins de poids égal |

Dans tous les cas, la distance est à vol d'oiseau (Lambert-93), transformée par un logarithme `ln(1 + d)` puis standardisée service par service (ou besoin par besoin) avant d'être moyennée. Nous retenons **B comme indicateur de référence** pour l'accès aux services du quotidien et **C comme éclairage complémentaire** sur l'accès aux grands équipements (gare, hôpital, lycée).

Pour tester la robustesse, nous comparons aussi 30 variantes (2 points de départ, 3 règles de distance, 5 jeux de poids). Le détail des choix est dans le rapport en ligne.

## Données

| Source | Fichier | Récupération |
|---|---|---|
| INSEE, [BPE 2025](https://www.insee.fr/fr/statistiques/8217525) | `BPE25.parquet` et 4 fichiers de documentation | automatique |
| IGN, [Admin Express](https://geoservices.ign.fr/adminexpress) | contours COG 2025 et position des chefs-lieux (archive `.7z`, ~245 Mo, GeoPackage de ~1,1 Go) | automatique |
| INSEE | populations de référence 2023 (géographie 2025), `ensemble.xlsx` | automatique |
| INSEE | Filosofi 2023, niveau de vie médian par commune (`MED_SL`), via l'API Melodi | automatique |

Toutes les données sont téléchargées par [`src/download.py`](src/download.py), que le notebook appelle. 

## Structure du dépôt

```
.
├── README.md
├── requirements.txt        bibliothèques nécessaires 
├── rapport.ipynb           le rapport : appelle src/ et deroule l'analyse
├── src/
│   ├── download.py         télécharge toutes les données dans data/raw/
│   ├── prepare_bpe.py      filtre la BPE sur le panier, écrit data/interim/
│   ├── communes.py         table des communes (centroïde, chef-lieu, surface, population)
│   ├── distances.py        présence des services et distances
│   ├── indice.py           indices, grille, besoins
│   ├── descriptif.py       statistiques descriptives
│   └── analyse.py          revenu, corrélations, tests
├── figures/                figures enregistrées par le notebook
├── dashboard/
│   └── index.html          tableau de bord interactif 
└── data/
    ├── raw/                données brutes, jamais modifiées (non versionnées)
    ├── interim/            données nettoyées (non versionnées)
    └── processed/          tableaux finaux, une ligne par commune (non versionnés)
```

## Tableau de bord interactif

Le dossier [`dashboard/`](dashboard/) contient `index.html`, un tableau de bord où les résultats et les contours des communes sont intégrés.

- **Vue d'ensemble** : répartition des équipements, services les plus représentés, distances d'accès.
- **Indicateurs** : les méthodes A, B et C, avec une pondération égale, EFT ou personnalisée (curseurs), la carte de l'indice et le classement des communes, départements et régions les plus isolés.
- **Comparaisons** : corrélations entre les méthodes, relation avec la densité, le revenu et la population.
- **Explorer un territoire** : profil et carte d'une région, d'un département ou d'une commune.
- **Données et téléchargements** : export Excel des indices par niveau géographique ou par service.

## Résultats principaux

- 10 806 communes (31 %) n'ont aucun des 33 équipements du panier.
- 56 à 59 % des communes ont un indice supérieur à la moyenne selon la méthode, mais elles ne regroupent que 9 à 10 % de la population.
- Les équipements rares sont loin de beaucoup d'habitants : 34 % de la population vit à plus de 10 km d'un hôpital et 14 % à plus de 10 km d'une gare, contre 0,5 % à plus de 5 km d'une école.
- La commune médiane est à 5,7 km en moyenne pondérée de ses 19 services (méthode B).
- Le point de départ de la distance pèse cinq fois plus sur le classement que les poids des services, et le regroupement en six besoins (C) pèse encore plus : seules 78 % des 10 % de communes les plus isolées sont communes à B et C.

## Équipe

- **Sarah-Laure FOGWOUNG DJOUFACK** ([@Sarahlaure](https://github.com/Sarahlaure))
- **Célina NGUEMFOUO NGOUMTSA** ([@nncelina](https://github.com/nncelina))
- **Eytan ZAGHROUN** ([@Eytan-ZG](https://github.com/Eytan-ZG))

## Usage d'outils d'IA

Nous avons utilisé un assistant d'IA (Claude) pour discuter de la méthode, relire le code et les textes, et mettre en forme le rapport en ligne et le tableau de bord. Les choix méthodologiques, les résultats et les textes ont été relus et validés par l'équipe.
