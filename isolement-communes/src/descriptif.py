"""
descriptif.py : statistiques descriptives sur les distances et l'indice.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def resume_par_service(distances_km: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par service : part de communes équipées, médiane, quantiles et maximum (km)."""
    lignes = {}
    for service in distances_km.columns:
        d = distances_km[service].dropna()
        lignes[service] = {
            "communes_equipees_%": round(100 * float((d == 0).mean()), 1),
            "mediane_km": d.median(),
            "moyenne_km": d.mean(),
            "q90_km": d.quantile(0.90),
            "q99_km": d.quantile(0.99),
            "max_km": d.max(),
        }
    return pd.DataFrame(lignes).T.round(2).sort_values("communes_equipees_%")


def part_population_eloignee(
    distances_km: pd.DataFrame, population: pd.Series, seuils_km: list[float]
) -> pd.DataFrame:
    """Part (%) des habitants vivant dans une commune à plus de `seuil` km de chaque service.

    Chaque commune compte pour sa population : une grande commune éloignée pèse plus qu'un hameau.
    """
    pop = population.reindex(distances_km.index)
    valide = pop.notna()
    total = float(pop[valide].sum())
    resultat = {}
    for seuil in seuils_km:
        eloigne = distances_km.loc[valide].gt(seuil)
        resultat[f"> {seuil:g} km"] = (eloigne.mul(pop[valide], axis=0).sum() / total * 100).round(2)
    return pd.DataFrame(resultat)


def communes_les_plus_isolees(base: pd.DataFrame, indice: pd.Series, n: int = 20) -> pd.DataFrame:
    """Les `n` communes à l'indice le plus élevé, avec leur nom, population et surface."""
    tableau = base.set_index("code").join(indice.rename("indice"))
    colonnes = [c for c in ["nom", "population", "surface_km2", "indice"] if c in tableau.columns]
    return tableau.sort_values("indice", ascending=False)[colonnes].head(n)


def decrire_indice(indice: pd.Series) -> pd.Series:
    """Quantiles de l'indice, pour lire sa distribution."""
    return indice.describe(percentiles=[0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99]).round(3)
