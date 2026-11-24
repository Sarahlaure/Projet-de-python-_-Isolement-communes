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


# Grille « experte » (méthode B) : chaque service est noté sur trois critères.
#   E (essentialité) : 2 = vital ou obligatoire, 1 = important, 0 = confort
#   F (fréquence)    : 2 = quotidien/hebdomadaire, 1 = mensuel à quelques fois par an, 0 = rare
#   P (public)       : 1 = presque toute la population, 0 = un public particulier
# Score = 1 + E + F + P (de 1 à 6) ; le poids d'un service est proportionnel à son score.

###### GRILLE FAITE à LA MAIN !!!
GRILLE_EXPERTE: dict[str, tuple[int, int, int, str]] = {
    "alimentation":      (2, 2, 1, "se nourrir, plusieurs fois par semaine, pour tous"),
    "boulangerie":       (1, 2, 1, "commerce le plus fréquenté, en partie substituable"),
    "medecin":           (2, 1, 1, "porte d'entrée du soin (médecin traitant), pour tous"),
    "pharmacie":         (2, 1, 1, "seul accès aux médicaments, recours régulier"),
    "ecole":             (2, 2, 0, "obligatoire dès 3 ans, trajet quotidien, familles"),
    "college":           (2, 2, 0, "obligatoire, trajet quotidien, 11-15 ans"),
    "lycee":             (1, 2, 0, "formation jusqu'à 18 ans, trajet quotidien, 15-18 ans"),
    "urgences":          (2, 0, 1, "vital (AVC, infarctus) mais recours rare"),
    "maternite":         (2, 0, 0, "vital à l'accouchement, rare, public particulier"),
    "infirmier":         (1, 1, 0, "soins réguliers des malades chroniques et des âgés"),
    "kine":              (1, 1, 0, "rééducation, recours régulier mais ciblé"),
    "dentiste":          (1, 0, 1, "soins courants, une à deux fois par an"),
    "sante_proximite":   (1, 1, 1, "centre ou maison de santé : soins de premier recours"),
    "poste":             (1, 1, 1, "courrier, colis, services bancaires de base"),
    "france_services":   (1, 0, 1, "démarches administratives, occasionnelles"),
    "petite_enfance":    (1, 2, 0, "garde d'enfant, condition de l'emploi des parents"),
    "personnes_agees":   (1, 1, 0, "prise en charge des personnes âgées dépendantes"),
    "proximite_sociale": (0, 1, 0, "lien social, accompagnement ; public ciblé"),
    "gare":              (0, 1, 1, "alternative à la voiture, non vitale"),
}


def table_grille_experte(services) -> pd.DataFrame:
    """Tableau de la grille experte : E, F, P, score, poids (somme = 1) et justification."""
    t = pd.DataFrame(
        {s: dict(zip(["E", "F", "P", "justification"], GRILLE_EXPERTE[s])) for s in services}
    ).T
    t[["E", "F", "P"]] = t[["E", "F", "P"]].astype(int)
    t["score"] = 1 + t["E"] + t["F"] + t["P"]
    t["poids"] = (t["score"] / t["score"].sum()).round(4)
    return t[["E", "F", "P", "score", "poids", "justification"]]


def poids_experts(services) -> dict[str, float]:
    """Poids de la méthode B : score 1 + E + F + P de la grille experte."""
    return {s: float(1 + sum(GRILLE_EXPERTE[s][:3])) for s in services}


# Méthode C : les 19 services regroupés en 6 besoins (d'après les domaines et sous-domaines de la BPE).
#   règle "min"     : services substituables, on va au plus proche des deux (pain en supérette ou en boulangerie)
#   règle "moyenne" : services complémentaires, il faut pouvoir accéder à chacun
BESOINS: dict[str, dict] = {
    "courses": {"libelle": "Faire ses courses", "regle": "min",
                "services": ["boulangerie", "alimentation"]},
    "soins_courants": {"libelle": "Se soigner au quotidien", "regle": "moyenne",
                       "services": ["medecin", "pharmacie", "infirmier", "kine", "dentiste", "sante_proximite"]},
    "hopital": {"libelle": "Soins hospitaliers", "regle": "moyenne",
                "services": ["urgences", "maternite"]},
    "scolarite": {"libelle": "Scolariser ses enfants", "regle": "moyenne",
                  "services": ["ecole", "college", "lycee"]},
    "social": {"libelle": "Démarches et accompagnement social", "regle": "moyenne",
               "services": ["poste", "france_services", "petite_enfance", "personnes_agees", "proximite_sociale"]},
    "transport": {"libelle": "Se déplacer", "regle": "moyenne",
                  "services": ["gare"]},
}


def distances_par_besoin(distances_km: pd.DataFrame, besoins: dict[str, dict] = BESOINS) -> pd.DataFrame:
    """Distance (km) de chaque commune à chaque besoin : minimum ou moyenne des distances de ses services."""
    colonnes = {}
    for nom, b in besoins.items():
        d = distances_km[b["services"]]
        colonnes[nom] = d.min(axis=1) if b["regle"] == "min" else d.mean(axis=1)
    return pd.DataFrame(colonnes, index=distances_km.index)


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
