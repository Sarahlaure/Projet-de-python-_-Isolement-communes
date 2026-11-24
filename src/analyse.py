"""
analyse.py : revenu et tests statistiques (partie 4 du rapport).

    - lire_revenu / fusionner_revenu : revenu médian Filosofi par commune
    - correlation_spearman           : corrélation de rang entre deux variables
    - comparer_groupes               : test de Kruskal-Wallis entre groupes (+ taille d'effet)

Toutes les fonctions travaillent sur de simples tableaux pandas : elles se testent sans carte.
"""
from __future__ import annotations

import pandas as pd
from scipy import stats


# ----------------------------------------------------------------------------- revenu
def lire_revenu(chemin, objets=("COM", "ARM"), mesure: str = "MED_SL") -> pd.DataFrame:
    """Lit le fichier Filosofi « tous niveaux géographiques » (format long) et garde, pour chaque
    commune (ou arrondissement), le niveau de vie médian.

    Le fichier a une ligne par couple (territoire, indicateur). On garde seulement :
      - les territoires dont GEO_OBJECT est dans `objets` (COM = communes, ARM = arrondissements),
      - l'indicateur `mesure` (MED_SL = niveau de vie médian, en euros).
    Les valeurs absentes (secret statistique « s », donnée manquante « vm ») deviennent NaN.
    """
    colonnes = ["GEO", "GEO_OBJECT", "FILOSOFI_MEASURE", "OBS_VALUE"]
    brut = None
    # Tolérant : encodage avec ou sans BOM, séparateur « ; » ou « , » ou tabulation
    for encodage in ("utf-8-sig", "utf-16", "latin-1"):
        for sep in (";", ",", "\t"):
            try:
                essai = pd.read_csv(chemin, sep=sep, dtype=str, encoding=encodage)
            except (UnicodeError, pd.errors.ParserError):
                continue
            essai.columns = [str(c).strip().strip('"').strip("\ufeff").upper() for c in essai.columns]
            if set(colonnes) <= set(essai.columns):
                brut = essai[colonnes]
                break
        if brut is not None:
            break
    if brut is None:
        raise ValueError(f"Colonnes {colonnes} introuvables dans {chemin}. "
                         "Affichez les 300 premiers octets du fichier pour voir son format.")
    sel = brut[brut["GEO_OBJECT"].isin(objets) & (brut["FILOSOFI_MEASURE"] == mesure)].copy()
    sel["code"] = sel["GEO"].str.strip().str.zfill(5)
    sel["revenu_median"] = pd.to_numeric(sel["OBS_VALUE"].str.replace(",", ".", regex=False), errors="coerce")
    return sel[["code", "revenu_median"]].drop_duplicates(subset="code").reset_index(drop=True)


def fusionner_revenu(base: pd.DataFrame, revenu: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Ajoute le revenu médian à la base (jointure à gauche : aucune commune ne disparaît)."""
    res = base.merge(revenu, on="code", how="left")
    journal = {
        "communes_base": int(len(base)),
        "communes_sans_revenu": int(res["revenu_median"].isna().sum()),
        "codes_revenu_hors_base": int((~revenu["code"].isin(base["code"])).sum()),
    }
    return res, journal


# ----------------------------------------------------------------------------- statistiques
def correlation_spearman(x: pd.Series, y: pd.Series) -> dict:
    """Corrélation de Spearman (corrélation des RANGS) entre x et y, sur les paires complètes."""
    paires = pd.concat([x, y], axis=1, keys=["x", "y"]).dropna()
    rho, p = stats.spearmanr(paires["x"], paires["y"])
    return {"rho": float(rho), "p_value": float(p), "n": int(len(paires))}


def comparer_groupes(valeur: pd.Series, groupe: pd.Series) -> tuple[dict, pd.DataFrame]:
    """Test de Kruskal-Wallis : la valeur est-elle distribuée pareil dans tous les groupes ?

    Retourne (résultat, tableau par groupe). La taille d'effet epsilon² = H / (n - 1) va de 0 à 1 :
    elle dit si l'écart est GRAND, ce que la p-value seule ne dit pas (avec 30 000 communes,
    presque tout est « significatif »).
    """
    d = pd.concat([valeur, groupe], axis=1, keys=["v", "g"]).dropna()
    listes = [s["v"].to_numpy() for _, s in d.groupby("g", observed=True)]
    h, p = stats.kruskal(*listes)
    n = len(d)
    resultat = {"H": float(h), "p_value": float(p), "n": int(n), "epsilon2": float(h / (n - 1))}
    tableau = d.groupby("g", observed=True)["v"].agg(
        communes="size", mediane="median", q25=lambda s: s.quantile(.25), q75=lambda s: s.quantile(.75))
    return resultat, tableau.round(3)
