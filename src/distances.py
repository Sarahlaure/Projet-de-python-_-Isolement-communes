"""
distances.py : présence d'un service dans une commune, et distance au service le plus proche.

LA RÈGLE (pour chaque commune et chaque service) :
    1. PRÉSENCE : si la commune possède au moins un équipement du service, la distance vaut 0.
       On utilise le code commune de la BPE, donc même les équipements SANS coordonnées comptent.
    2. SINON : distance à vol d'oiseau entre le CENTRE de la commune et l'équipement le plus proche
       qui a des coordonnées. On ne garde que la plus petite des distances.

Toutes les distances sont rendues en KILOMÈTRES (coordonnées Lambert-93 en mètres, divisées par 1000).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


def distance_to_nearest(origins_xy: np.ndarray, targets_xy: np.ndarray) -> np.ndarray:
    """Distance (mètres) de chaque origine à la cible la plus proche.

    origins_xy : tableau (n, 2) de coordonnées projetées en mètres (EPSG:2154).
    targets_xy : tableau (m, 2), m >= 1. Les points à NaN sont ignorés.
    """
    targets = np.asarray(targets_xy, dtype=float)
    targets = targets[~np.isnan(targets).any(axis=1)]
    if len(targets) == 0:
        return np.full(len(origins_xy), np.nan)
    dist, _ = cKDTree(targets).query(np.asarray(origins_xy, dtype=float), k=1)
    return dist


def presence_par_service(codes_communes, equipements: pd.DataFrame, services: list[str]) -> pd.DataFrame:
    """Tableau booléen : une ligne par commune, une colonne par service, True si le service est présent.

    `equipements` doit avoir les colonnes `depcom` (code commune) et `service`.
    Un équipement dont le code commune n'est pas dans `codes_communes` est ignoré ici
    (le contrôle `controle_codes` permet de les compter).
    """
    codes = pd.Index(codes_communes, name="code")
    paires = equipements[["depcom", "service"]].drop_duplicates()
    lignes = codes.get_indexer(paires["depcom"])
    colonnes = pd.Index(services).get_indexer(paires["service"])
    valides = (lignes >= 0) & (colonnes >= 0)  # get_indexer renvoie -1 si absent
    tableau = np.zeros((len(codes), len(services)), dtype=bool)
    tableau[lignes[valides], colonnes[valides]] = True
    return pd.DataFrame(tableau, index=codes, columns=list(services))


def controle_codes(equipements: pd.DataFrame, codes_communes) -> dict:
    """Compte les équipements dont le code commune est inconnu de la table des communes."""
    connus = set(codes_communes)
    inconnus = equipements.loc[~equipements["depcom"].isin(connus), "depcom"]
    return {
        "equipements_sans_commune": int(len(inconnus)),
        "codes_inconnus": sorted(inconnus.unique().tolist())[:20],
    }


def distances_par_service(
    communes: pd.DataFrame,
    equipements: pd.DataFrame,
    services: list[str],
    qualites: list[str] | None = None,
    regle_presence: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Distances (km) de chaque commune à chaque service, et tableau de présence.

    communes     : colonnes `code`, `x`, `y` (centre de la commune, Lambert-93, mètres).
    equipements  : colonnes `depcom`, `service`, `x`, `y`, `qualite_xy`.
    services     : liste des noms de services à calculer.
    qualites     : si fourni (ex. ["A", "B"]), seuls les équipements dont la position a cette
                   qualité servent au calcul de distance. La PRÉSENCE n'est pas filtrée.
    regle_presence : True (règle principale) -> distance 0 si la commune a le service.
                     False (variante) -> toujours la distance du centre de la commune au plus
                     proche équipement localisé.
    """
    origines = communes[["x", "y"]].to_numpy(dtype=float)
    presence = presence_par_service(communes["code"].to_numpy(), equipements, services)
    colonnes = {}
    for service in services:
        localises = equipements[equipements["service"] == service].dropna(subset=["x", "y"])
        if qualites is not None:
            localises = localises[localises["qualite_xy"].isin(qualites)]
        d_km = distance_to_nearest(origines, localises[["x", "y"]].to_numpy(dtype=float)) / 1000.0
        if regle_presence:
            d_km = np.where(presence[service].to_numpy(), 0.0, d_km)
        colonnes[service] = d_km
    distances = pd.DataFrame(colonnes, index=pd.Index(communes["code"].to_numpy(), name="code"))
    return distances, presence
