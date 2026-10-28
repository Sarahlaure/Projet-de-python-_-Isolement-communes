"""
communes.py : construit la TABLE DE BASE des communes (une ligne par commune ou arrondissement).

POURQUOI ?
    Chaque commune a besoin d'un point de départ (son centre) pour mesurer les distances, d'une surface
    et d'une population pour calculer la densité. Ces informations viennent des contours IGN
    (Admin Express). La BPE code Paris, Lyon et Marseille par ARRONDISSEMENT : la base doit donc
    contenir les arrondissements, et PAS les trois villes entières (sinon on compterait deux fois).

DEUX NIVEAUX :
    - les fonctions qui lisent les contours (geopandas) : lire_couche, geometrie_vers_table, geometries_base
    - les fonctions qui travaillent sur de simples tableaux pandas : assembler_base, fusionner_population
      (faciles à tester sans carte).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CRS_METROPOLE = 2154  # Lambert-93
PREFIXES_HORS_METROPOLE = ("97", "98")  # DROM et collectivités d'outre-mer


def trouver_fichiers(dossier: Path, motifs=("*.gpkg", "*.shp")) -> list[Path]:
    """Cherche (dans tous les sous-dossiers) les fichiers cartographiques d'un dossier."""
    dossier = Path(dossier)
    return sorted(p for motif in motifs for p in dossier.rglob(motif))


def choisir_colonne(colonnes, candidats: list[str], obligatoire: bool = True) -> str | None:
    """Première colonne dont le nom (en minuscules) figure parmi `candidats`.

    Si aucune ne correspond : erreur explicite (obligatoire=True) ou None (obligatoire=False).
    """
    minuscules = {c.lower(): c for c in colonnes}
    for candidat in candidats:
        if candidat.lower() in minuscules:
            return minuscules[candidat.lower()]
    if obligatoire:
        raise KeyError(f"Aucune colonne parmi {candidats} dans {list(colonnes)}")
    return None


def lister_couches(chemin: Path) -> list[str]:
    """Noms des couches d'un fichier GeoPackage (.gpkg)."""
    import pyogrio

    return [nom for nom, _ in pyogrio.list_layers(chemin)]


def lire_couche(chemin: Path, nom_couche: str | None = None):
    """Lit une couche cartographique et la met en Lambert-93, noms de colonnes en minuscules."""
    import geopandas as gpd

    if nom_couche is not None and Path(chemin).suffix.lower() == ".gpkg":
        gdf = gpd.read_file(chemin, layer=nom_couche)
    else:
        gdf = gpd.read_file(chemin)
    gdf = gdf.rename(columns=str.lower)
    return gdf.to_crs(CRS_METROPOLE)


def geometrie_vers_table(gdf, col_code: str, col_nom: str | None = None,
                         col_population: str | None = None, col_parent: str | None = None) -> pd.DataFrame:
    """Transforme une couche cartographique en simple tableau :
    code, nom, population, x, y (centre), surface_km2, et parent (ville mère, pour les arrondissements).
    """
    centre = gdf.geometry.centroid
    table = pd.DataFrame({
        "code": gdf[col_code].astype(str).str.strip().to_numpy(),
        "nom": gdf[col_nom].to_numpy() if col_nom else None,
        "population": pd.to_numeric(gdf[col_population], errors="coerce").to_numpy()
        if col_population else float("nan"),
        "x": centre.x.to_numpy(),
        "y": centre.y.to_numpy(),
        "surface_km2": (gdf.geometry.area / 1e6).to_numpy(),
    })
    if col_parent:
        table["parent"] = gdf[col_parent].astype(str).str.strip().to_numpy()
    return table


def assembler_base(communes: pd.DataFrame, arrondissements: pd.DataFrame) -> pd.DataFrame:
    """Table de base : communes (sans les villes découpées en arrondissements) + arrondissements.

    - Les villes « mères » (Paris 75056, Lyon 69123, Marseille 13055) sont retirées : ce sont les
      valeurs de la colonne `parent` des arrondissements.
    - Seule la métropole est conservée (codes qui ne commencent pas par 97 ou 98).
    - Contrôles : codes de 5 caractères, aucun doublon.
    """
    villes_meres = set(arrondissements["parent"])
    sans_villes = communes[~communes["code"].isin(villes_meres)]
    base = pd.concat(
        [sans_villes.drop(columns=["parent"], errors="ignore"),
         arrondissements.drop(columns=["parent"], errors="ignore")],
        ignore_index=True,
    )
    base = base[~base["code"].str.startswith(PREFIXES_HORS_METROPOLE)].copy()
    if (base["code"].str.len() != 5).any():
        raise ValueError("Des codes commune ne font pas 5 caractères.")
    doublons = base["code"].duplicated(keep=False)
    if doublons.any():
        raise ValueError(f"Codes en double : {sorted(base.loc[doublons, 'code'].unique())[:10]}")
    base["densite"] = base["population"] / base["surface_km2"]
    return base.sort_values("code").reset_index(drop=True)


def fusionner_population(base: pd.DataFrame, population: pd.DataFrame,
                         col_code: str, col_population: str) -> tuple[pd.DataFrame, dict]:
    """Remplace la population de la base par celle d'un fichier externe, et journalise les écarts.

    Jointure à gauche : aucune commune de la base ne disparaît. Les codes du fichier sont remis
    sur 5 caractères en texte (un code lu comme un nombre aurait perdu son zéro initial).
    """
    externe = population[[col_code, col_population]].copy()
    externe[col_code] = externe[col_code].astype(str).str.strip().str.zfill(5)
    externe[col_population] = pd.to_numeric(externe[col_population], errors="coerce")
    externe = externe.drop_duplicates(subset=col_code).rename(
        columns={col_code: "code", col_population: "population_ext"}
    )
    resultat = base.merge(externe, on="code", how="left")
    journal = {
        "communes_base": int(len(base)),
        "communes_sans_population_ext": int(resultat["population_ext"].isna().sum()),
        "codes_ext_hors_base": int((~externe["code"].isin(base["code"])).sum()),
    }
    resultat["population"] = resultat["population_ext"].fillna(resultat["population"])
    resultat = resultat.drop(columns="population_ext")
    resultat["densite"] = resultat["population"] / resultat["surface_km2"]
    return resultat, journal


def geometries_base(gdf_communes, gdf_arrondissements, col_code_commune: str,
                    col_code_arrondissement: str, villes_meres: set[str]):
    """Polygones de la base (pour les cartes) : communes sans villes mères + arrondissements."""
    import geopandas as gpd

    com = gdf_communes[[col_code_commune, "geometry"]].rename(columns={col_code_commune: "code"})
    com["code"] = com["code"].astype(str).str.strip()
    com = com[~com["code"].isin(villes_meres)]
    arm = gdf_arrondissements[[col_code_arrondissement, "geometry"]].rename(
        columns={col_code_arrondissement: "code"})
    arm["code"] = arm["code"].astype(str).str.strip()
    geo = pd.concat([com, arm], ignore_index=True)
    geo = geo[~geo["code"].str.startswith(PREFIXES_HORS_METROPOLE)]
    return gpd.GeoDataFrame(geo, geometry="geometry", crs=CRS_METROPOLE)
