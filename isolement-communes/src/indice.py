"""
indice.py : de 19 distances (km) à un indice d'isolement par commune.

ÉTAPES
    1. Logarithme      d' = ln(1 + d)      : une distance de 100 km ne compte pas 100 fois celle de 1 km.
    2. Standardisation z = (d' - moyenne) / écart-type, service par service : tous les services
                        sont ramenés à la même échelle (moyenne 0, écart-type 1).
    3. Somme pondérée  I = somme(w * z) / somme(w) : plus l'indice est élevé, plus la commune est isolée.
    Plusieurs jeux de poids sont comparés pour montrer que le classement ne dépend pas de ce choix.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

# Thème de chaque service (sert au jeu de poids « thèmes équilibrés »).
THEMES: dict[str, str] = {
    "boulangerie": "commerces", "alimentation": "commerces",
    "pharmacie": "sante", "medecin": "sante", "dentiste": "sante", "kine": "sante",
    "infirmier": "sante", "sante_proximite": "sante", "urgences": "sante", "maternite": "sante",
    "ecole": "enseignement", "college": "enseignement", "lycee": "enseignement",
    "poste": "services_publics", "france_services": "services_publics",
    "petite_enfance": "services_publics", "personnes_agees": "services_publics",
    "proximite_sociale": "services_publics",
    "gare": "transport",
}

# Services « vitaux » : soins urgents ou de premier recours, comptés double dans un des jeux de poids.
SERVICES_VITAUX = ["urgences", "maternite", "medecin", "pharmacie", "sante_proximite"]


def log_distance(distances_km: pd.DataFrame) -> pd.DataFrame:
    """ln(1 + d) : le « +1 » permet de traiter les distances nulles (service présent)."""
    return np.log1p(distances_km)


def standardiser(tableau: pd.DataFrame) -> pd.DataFrame:
    """z-score par colonne. Une colonne constante (écart-type nul) devient une colonne de zéros."""
    moyenne = tableau.mean()
    ecart = tableau.std(ddof=0).replace(0, np.nan)
    return ((tableau - moyenne) / ecart).fillna(0.0)


def poids_egaux(services) -> dict[str, float]:
    return {s: 1.0 for s in services}


def poids_vitaux(services) -> dict[str, float]:
    return {s: (2.0 if s in SERVICES_VITAUX else 1.0) for s in services}


def poids_themes_equilibres(services) -> dict[str, float]:
    """Chaque thème pèse autant : le poids d'un service est 1 / (nombre de services de son thème)."""
    effectifs = pd.Series({s: THEMES[s] for s in services}).value_counts()
    return {s: 1.0 / effectifs[THEMES[s]] for s in services}


def indice_pondere(z: pd.DataFrame, poids: dict[str, float]) -> pd.Series:
    """Moyenne pondérée des z-scores. Divisé par la somme des poids : l'échelle reste comparable."""
    w = pd.Series(poids).reindex(z.columns)
    if w.isna().any():
        raise ValueError(f"Poids manquants pour : {list(w[w.isna()].index)}")
    numerateur = (z * w).sum(axis=1)
    denominateur = float(w.sum())
    return (numerateur / denominateur).rename("indice")


def indice_acp(z: pd.DataFrame, reference: pd.Series) -> tuple[pd.Series, float]:
    """Première composante principale des z-scores, orientée comme `reference`.

    Renvoie (scores, part de variance expliquée). Le signe d'une composante est arbitraire :
    on l'oriente pour qu'un score élevé veuille dire « plus isolé » comme dans l'indice de référence.
    """
    acp = PCA(n_components=1, random_state=0)
    scores = pd.Series(acp.fit_transform(z.to_numpy())[:, 0], index=z.index, name="indice_acp")
    if np.corrcoef(scores.to_numpy(), reference.to_numpy())[0, 1] < 0:
        scores = -scores
    return scores, float(acp.explained_variance_ratio_[0])


def calculer_indice(distances_km: pd.DataFrame, poids: dict[str, float]) -> pd.Series:
    """Chaîne complète : logarithme, standardisation, somme pondérée."""
    z = standardiser(log_distance(distances_km))
    return indice_pondere(z, poids)


def comparer_classements(indices: pd.DataFrame) -> pd.DataFrame:
    """Matrice de corrélation de Spearman (comparaison de classements) entre plusieurs indices."""
    return indices.corr(method="spearman")
