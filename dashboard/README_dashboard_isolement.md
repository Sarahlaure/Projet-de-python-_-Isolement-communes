# Isolement des communes de la France métropolitaine

## Présentation

Ce dashboard interactif permet d'étudier l'accès aux services du quotidien en France métropolitaine et de comparer les situations d'isolement entre communes, départements et régions.

Il répond notamment aux questions suivantes :

- Où les équipements sont-ils répartis sur le territoire ?
- Quels services sont les plus ou les moins accessibles ?
- Quelles communes sont les plus isolées ?
- Les résultats changent-ils selon la méthode de calcul ou les pondérations retenues ?
- L'isolement est-il associé à la densité de population, au revenu médian ou à la population ?

Le tableau de bord est organisé en cinq onglets : **Vue d'ensemble**, **Indicateurs**, **Comparaisons**, **Explorer un territoire** et **Données & téléchargements**.

## Démarrer et naviguer

À l'ouverture, le dashboard affiche la **Vue d'ensemble**.

- Utiliser le menu latéral pour passer d'un onglet à l'autre.
- L'onglet actif est mis en évidence dans le menu.
- Le fil d'Ariane en haut de la page indique la section ouverte.
- Sur un écran étroit, le bouton de menu permet d'ouvrir ou de fermer la navigation.
- Les cartes et graphiques interactifs peuvent être survolés pour afficher des informations complémentaires. Sur les cartes, il est également possible de zoomer, de déplacer la vue et de cliquer sur les communes.

Le choix de la méthode et de la pondération effectué dans **Indicateurs** devient la configuration active du dashboard. Il est réutilisé dans les autres vues qui affichent l'indice.

---

## 1. Vue d'ensemble

Cette page donne un panorama national de la répartition des équipements et de l'accès aux services.

### Chiffres clés

Les trois indicateurs en haut de page présentent :

- le nombre de communes étudiées ;
- le nombre total d'équipements recensés ;
- la population de référence.

### Carte de répartition

Le menu de la carte permet de choisir la variable représentée :

- **Équipements pour 1 000 habitants · communes** : compare la présence d'équipements relativement à la population communale ;
- **Nombre d'équipements · régions** : affiche les effectifs d'équipements par région ;
- **Nombre d'équipements · départements** : affiche les effectifs par département.

La légende permet de lire les classes de valeurs représentées sur la carte.

### Répartition par domaine

Le graphique en anneau présente la répartition des équipements. Le menu permet de choisir entre :

- un regroupement en **19 services** ;
- un regroupement en **6 besoins**.

La légende associée permet de consulter les catégories et leurs parts.

### Services les plus représentés

Le graphique classe les services selon le nombre d'équipements recensés. Le menu **Top 5 / Top 10 / Top 15 / Top 19** permet de modifier le nombre de services affichés.

### Distances d'accès aux services

Ce graphique compare les distances d'accès aux services. Plusieurs paramètres sont disponibles :

- **Top 5 / Top 10 / Top 15 / Top 19** : nombre de services affichés ;
- **Méthode A ou B** : méthode utilisée pour les distances ;
- **Médiane, moyenne ou 90e percentile** : statistique résumant les distances.

La médiane décrit la distance au centre de la distribution ; la moyenne tient compte de l'ensemble des valeurs ; le 90e percentile indique une distance en dessous de laquelle se situent 90 % des observations.

---

## 2. Indicateurs

Cet onglet permet de calculer et de visualiser l'indice d'isolement. Les choix effectués ici s'appliquent aux autres pages du dashboard.

### Choisir une méthode

Trois méthodes sont proposées :

| Méthode | Principe |
|---|---|
| **A** | Distance calculée depuis le centroïde de la commune ; distance nulle si le service est présent dans la commune ; 19 services. |
| **B** | Distance réelle depuis le chef-lieu de la commune jusqu'au service le plus proche ; 19 services. C'est la méthode de référence. |
| **C** | Distances de la méthode B regroupées en 6 besoins. |

### Choisir la pondération

Le menu **Pondération** propose trois configurations :

- **Pondération égale** : chaque service (ou besoin pour la méthode C) reçoit le même poids.
- **Pondération EFT** : utilise les poids définis dans la configuration EFT du dashboard.
- **Ma pondération (personnalisée)** : permet de régler les poids avec les curseurs.

Avec la pondération personnalisée, déplacer un curseur modifie la part du service ou du besoin correspondant. Les parts affichées sont normalisées à partir de l'ensemble des poids : leur somme est donc ramenée à 100 %, même si la somme des valeurs brutes des curseurs n'est pas égale à 100.

Le bouton **Réinitialiser (EFT)** rétablit les poids EFT pour la méthode active.

### Comprendre l'indice

Pour chaque service, la distance est transformée par :

\[
\ln(1+d)
\]

où \(d\) est la distance à l'équipement le plus proche. Le score transformé est ensuite centré et réduit sur l'ensemble des communes :

\[
z=\frac{\ln(1+d)-\text{moyenne}}{\text{écart-type}}
\]

L'indice communal correspond à la moyenne pondérée des scores obtenus.

Interprétation :

- **Indice proche de 0** : situation proche de la moyenne nationale pour la configuration choisie ;
- **Indice positif** : commune plus éloignée des services que la moyenne ;
- **Indice négatif** : commune mieux desservie que la moyenne.

L'indice dépend de la méthode et de la pondération choisies. Il est donc préférable de comparer les classements des communes entre différentes configurations plutôt que de comparer directement leurs valeurs numériques.

### Lire les résultats

Les indicateurs synthétiques présentent notamment :

- **Indice moyen par habitant** : moyenne de l'indice pondérée par la population ;
- **Indice médian** : valeur qui partage les communes en deux groupes de taille égale ;
- **Communes très isolées** : communes appartenant au décile supérieur de l'indice ;
- **Population concernée** : population vivant dans les communes très isolées.

La carte colore les communes selon leur indice. La distribution montre comment les scores se répartissent. Les statistiques affichées comprennent le minimum, le maximum, l'écart-type et le seuil du décile supérieur.

### Classement des territoires

Le tableau des communes les plus isolées peut être configuré :

- par **communes**, **départements** ou **régions** ;
- avec un **Top 5**, **Top 10**, **Top 20** ou **Top 50**.

Le classement suit la méthode et la pondération actuellement actives.

---

## 3. Comparaisons

Cet onglet sert à examiner la robustesse de l'indice et ses relations avec certaines caractéristiques territoriales.

### Matrice de corrélation

La matrice de corrélation de Spearman compare les classements issus des méthodes A, B et C. Elle permet de voir si les méthodes ordonnent les communes de façon similaire.

Une corrélation élevée indique des classements proches ; une corrélation plus faible indique que les méthodes peuvent conduire à des ordres différents.

### Relation avec le territoire

Le menu permet de choisir la variable territoriale étudiée :

- densité de population ;
- revenu médian ;
- population.

Le graphique représente la relation entre cette variable et l'indice d'isolement actif. Les points correspondent aux médianes par vingtile, ce qui permet de résumer la relation sans afficher chaque commune individuellement.

Les statistiques associées comprennent :

- **ρ de Spearman** : mesure l'association monotone entre les variables ;
- **Kruskal-Wallis** : teste les différences entre cinq classes de la variable étudiée ;
- **Taille d'effet ε²** : donne une mesure de l'importance de ces différences.

Le graphique par quintiles présente également la distribution de l'indice selon les cinq groupes de la variable territoriale.

**Précaution :** une corrélation ne démontre pas une relation de cause à effet. Les résultats dépendent aussi de la qualité des données et de la taille des communes, notamment dans le cas des communes nouvelles ou des arrondissements.

---

## 4. Explorer un territoire

Cette page permet d'obtenir un profil à une échelle géographique précise.

### Sélectionner un territoire

Les filtres sont liés dans l'ordre suivant :

**Région → Département → Commune**

1. Choisir une région pour afficher son profil.
2. Choisir un département pour affiner la sélection.
3. Choisir une commune pour consulter son profil communal.

Le champ de recherche permet de rechercher directement une commune par son **nom** ou son **code INSEE**.

Le bouton **Toute la France** réinitialise la sélection et revient au profil national.

Les liens du fil de localisation du profil permettent également de remonter à la région, au département ou à la France métropolitaine.

### Utiliser la carte

La carte affiche les communes selon l'indice d'isolement actif.

- Survoler une commune pour consulter son nom, son département, son indice, son centile et sa population.
- Cliquer sur une commune pour la sélectionner et descendre dans l'échelle géographique : depuis la France vers la région, depuis la région vers le département, puis vers la commune.
- Utiliser les contrôles de la carte pour zoomer ou déplacer la vue.

Le profil présente notamment l'indice, la population, la densité, le nombre d'équipements, les équipements pour 1 000 habitants et le revenu médian lorsqu'il est disponible. Il permet aussi de consulter les distances aux services et la localisation du territoire dans son voisinage.

---

## 5. Données & téléchargements

Cet onglet permet de préparer et de télécharger un fichier **Excel (.xlsx)** à partir des données et indices calculés.

### Choisir le type de données

Deux types d'extraction sont disponibles :

- **Indices par niveau géographique** ;
- **Indices par équipement / service / regroupement**.

### Extraction des indices par niveau géographique

Pour ce type d'extraction, choisir :

- le niveau géographique : pays, régions, départements ou communes ;
- éventuellement une région et/ou un département pour limiter le périmètre ;
- la méthode A, B ou C ;
- la pondération égale, EFT ou personnalisée.

L'indicateur est préréglé sur la configuration active de l'onglet **Indicateurs**, mais il peut être modifié indépendamment dans la page d'export.

### Extraction par équipement, service ou regroupement

Pour ce type d'extraction, choisir le niveau de détail :

- **Regroupements de services (6)** ;
- **Services (19)** ;
- **Équipements (types BPE)**.

Les contrôles complémentaires permettent de préciser le regroupement et le périmètre de l'extraction.

Les distances de cette extraction reposent sur la méthode B (chef-lieu et distance réelle au service le plus proche). Les regroupements en 6 besoins suivent la méthode C : minimum pour les courses et moyenne pour les autres besoins.

### Aperçu et téléchargement

L'aperçu se met à jour lorsque les paramètres changent. Il affiche le nombre de lignes et les premières lignes du fichier (jusqu'à 10).

- Vérifier le périmètre, les paramètres et l'aperçu.
- Cliquer sur **Télécharger le fichier Excel**.
- Le fichier contient les données correspondant à toute la sélection, pas uniquement aux lignes visibles dans l'aperçu.
- Un second onglet **Paramètres** documente la méthode, la pondération, la définition de l'indice et les sources.

---

## Conseils de navigation

Pour une première exploration, suivre cet ordre :

1. **Vue d'ensemble** : comprendre la répartition nationale des équipements et les distances.
2. **Indicateurs** : choisir une méthode et une pondération, puis repérer les communes les plus isolées.
3. **Comparaisons** : vérifier si les méthodes donnent des classements proches et étudier les relations territoriales.
4. **Explorer un territoire** : examiner une région, un département ou une commune.
5. **Données & téléchargements** : exporter les résultats utiles pour une analyse complémentaire.

## À garder en tête

- L'indice est relatif à l'ensemble des communes et à la méthode choisie.
- Une valeur positive indique un isolement supérieur à la moyenne nationale ; une valeur négative indique une meilleure desserte relative.
- Les résultats peuvent changer lorsque la méthode ou les poids changent.
- Une association statistique ne suffit pas à établir une causalité.
- Les données exportées et les résultats doivent être interprétés en tenant compte du périmètre et des paramètres sélectionnés.
