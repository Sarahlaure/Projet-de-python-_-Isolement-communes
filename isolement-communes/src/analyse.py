"""
analyse.py : analyses de la 2e partie du projet (après l'indice et les cartes).

    - lire_revenu / fusionner_revenu : revenu médian Filosofi par commune
    - correlation_spearman           : corrélation de rang entre deux variables
    - comparer_groupes               : test de Kruskal-Wallis entre groupes (+ taille d'effet)
    - choisir_k / typologie          : profils d'isolement par ACP et k-means
    - moran_global / moran_local     : autocorrélation spatiale (bonus)

Toutes les fonctions travaillent sur de simples tableaux pandas : elles se testent sans carte.
"""
from __future__ import annotations

import numpy as np
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


# ----------------------------------------------------------------------------- typologie
def choisir_k(z: pd.DataFrame, ks=range(2, 9), echantillon: int = 5000, graine: int = 0) -> pd.DataFrame:
    """Pour chaque nombre de groupes k : inertie (cohésion) et silhouette (séparation, sur échantillon)."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    x = z.fillna(0).to_numpy()
    rng = np.random.default_rng(graine)
    idx = rng.choice(len(x), size=min(echantillon, len(x)), replace=False)
    lignes = []
    for k in ks:
        km = KMeans(n_clusters=k, n_init=10, random_state=graine).fit(x)
        lignes.append({"k": k, "inertie": km.inertia_,
                       "silhouette": silhouette_score(x[idx], km.labels_[idx])})
    return pd.DataFrame(lignes).set_index("k").round(3)


def typologie(z: pd.DataFrame, n_groupes: int = 5, graine: int = 0):
    """Regroupe les communes par profil d'éloignement (k-means sur les z), et calcule le plan de l'ACP.

    Les groupes sont numérotés du MIEUX desservi (0) au MOINS bien desservi (n-1), d'après la moyenne
    de leurs z : la numérotation brute de k-means est aléatoire et n'aurait aucun sens.
    Retourne (tableau commune -> groupe, pc1, pc2 ; profils moyens par groupe ; variance expliquée).
    """
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA

    x = z.fillna(0)
    km = KMeans(n_clusters=n_groupes, n_init=10, random_state=graine).fit(x.to_numpy())
    brut = pd.Series(km.labels_, index=z.index)
    ordre = x.groupby(brut).mean().mean(axis=1).sort_values().index
    renum = {ancien: nouveau for nouveau, ancien in enumerate(ordre)}
    groupe = brut.map(renum).rename("groupe")

    pca = PCA(n_components=2).fit(x.to_numpy())
    coord = pca.transform(x.to_numpy())
    resultat = pd.DataFrame({"groupe": groupe, "pc1": coord[:, 0], "pc2": coord[:, 1]}, index=z.index)
    profils = x.groupby(groupe).mean().round(2)
    return resultat, profils, pca.explained_variance_ratio_


# ----------------------------------------------------------------------------- spatial (bonus)
def moran_global(valeurs: pd.Series, x: pd.Series, y: pd.Series, k: int = 8, permutations: int = 199,
                 graine: int = 0) -> dict:
    """I de Moran global : les communes proches ont-elles des valeurs proches ?

    Voisins = les k communes les plus proches (centres). I vaut ~0 si la répartition est aléatoire,
    et tend vers 1 si les valeurs semblables se regroupent. La p-value vient de permutations.
    """
    import esda
    from libpysal.weights import KNN

    w = KNN.from_array(np.column_stack([x.to_numpy(), y.to_numpy()]), k=k)
    w.transform = "r"
    np.random.seed(graine)
    m = esda.Moran(valeurs.to_numpy(), w, permutations=permutations)
    return {"I": float(m.I), "esperance": float(m.EI), "p_sim": float(m.p_sim), "k": k}


def moran_local(valeurs: pd.Series, x: pd.Series, y: pd.Series, k: int = 8, permutations: int = 99,
                graine: int = 0, seuil: float = 0.05) -> pd.Series:
    """LISA : classe chaque commune en HH (isolées entourées d'isolées), LL, HL, LH ou « ns » (non significatif)."""
    import esda
    from libpysal.weights import KNN

    w = KNN.from_array(np.column_stack([x.to_numpy(), y.to_numpy()]), k=k)
    w.transform = "r"
    ml = esda.Moran_Local(valeurs.to_numpy(), w, permutations=permutations, seed=graine)
    noms = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    classes = np.where(ml.p_sim < seuil, [noms[q] for q in ml.q], "ns")
    return pd.Series(classes, index=valeurs.index, name="lisa")
