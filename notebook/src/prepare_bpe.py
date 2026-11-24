"""
prepare_bpe.py : extrait de la BPE 2025 uniquement ce dont le projet a besoin.

POURQUOI ?
    La BPE brute fait 2,9 millions de lignes et 95 colonnes. Pour l'indice d'isolement, on a
    besoin de 33 types d'équipements (le « panier ») et de 5 informations par équipement.
    Ce script fait ce tri UNE fois et écrit un petit fichier propre : data/interim/equipements.parquet

CE QUE FAIT LE SCRIPT
    1. Garde la France métropolitaine (colonne EPSG = 2154, c'est-à-dire coordonnées Lambert-93).
       Les DROM utilisent d'autres systèmes de coordonnées : on ne mélange pas.
    2. Garde les 33 types du panier, et range chacun dans un SERVICE (ex. D502 et D509 -> petite enfance).
    3. Garde les colonnes utiles : commune (DEPCOM), service, type, X, Y, qualité de position.
    4. NE JETTE PAS les équipements sans coordonnées : ils servent à savoir qu'une commune possède
       le service (« présence »), même si on ne peut pas calculer de distance à partir d'eux.

USAGE
    Terminal :   python src/prepare_bpe.py
    Notebook :   import prepare_bpe ; prepare_bpe.main()
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
BPE = RACINE / "data" / "raw" / "BPE25.parquet"
SORTIE = RACINE / "data" / "interim" / "equipements.parquet"

# ---------------------------------------------------------------------------------------
# LE PANIER DE SERVICES : service -> codes TYPEQU qui comptent pour ce service
# ---------------------------------------------------------------------------------------
# Pour un service, la commune est « équipée » si elle possède AU MOINS UN des types listés
# (ex. une école maternelle OU primaire OU élémentaire). Libellés vérifiés dans TYPEQU_2025.csv.
# Modifiable : c'est ici qu'on ajuste le panier, nulle part ailleurs.
SERVICES: dict[str, list[str]] = {
    "boulangerie": ["B207"],                      # boulangerie-pâtisserie
    "alimentation": ["B201", "B202", "B105"],     # supérette, épicerie, supermarché
    "pharmacie": ["D307"],
    "medecin": ["D265"],                          # médecin généraliste
    "dentiste": ["D277"],
    "kine": ["D279"],                             # masseur-kinésithérapeute
    "infirmier": ["D281"],
    "sante_proximite": ["D108", "D113"],          # centre de santé, maison de santé
    "urgences": ["D106"],
    "maternite": ["D107"],
    "ecole": ["C107", "C108", "C109"],            # maternelle, primaire, élémentaire
    "college": ["C201"],
    "lycee": ["C301", "C302"],                    # général/techno, professionnel
    "poste": ["A206", "A207", "A208"],            # bureau, relais, agence postale
    "france_services": ["A128"],
    "petite_enfance": ["D502", "D509"],           # accueil jeune enfant, micro-crèche
    "personnes_agees": ["D401", "D402", "D403"],  # hébergement, soins, aide à domicile
    "proximite_sociale": ["D506", "D508"],        # centres sociaux, espaces de vie sociale
    "gare": ["E107", "E108", "E109"],             # gares nationale, régionale, locale
}


def table_de_correspondance() -> pd.DataFrame:
    """Transforme le dictionnaire SERVICES en tableau (TYPEQU, service) : une ligne par code."""
    lignes = [(code, service) for service, codes in SERVICES.items() for code in codes]
    table = pd.DataFrame(lignes, columns=["TYPEQU", "service"])
    doublons = table[table["TYPEQU"].duplicated()]
    if not doublons.empty:  # un code ne doit appartenir qu'à un seul service
        raise ValueError(f"Codes en double dans SERVICES : {doublons['TYPEQU'].tolist()}")
    return table


def preparer(bpe: Path = BPE, sortie: Path = SORTIE) -> pd.DataFrame:
    """Lit la BPE, filtre, et écrit `sortie`. Renvoie le tableau obtenu."""
    sortie.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    # On « enregistre » le tableau de correspondance pour pouvoir le joindre en SQL.
    con.register("correspondance", table_de_correspondance())

    # INNER JOIN avec la correspondance = ne garder que les types du panier.
    # EPSG peut être lu en texte ou en nombre selon le fichier : CAST(... AS VARCHAR) couvre les deux.
    # LAMBERT_X/Y sont convertis en nombres (DOUBLE) ; TRY_CAST donne NULL au lieu de planter si vide.
    requete = f"""
        SELECT
            b.DEPCOM                      AS depcom,
            c.service                     AS service,
            b.TYPEQU                      AS typequ,
            TRY_CAST(b.LAMBERT_X AS DOUBLE) AS x,
            TRY_CAST(b.LAMBERT_Y AS DOUBLE) AS y,
            b.QUALITE_XY                  AS qualite_xy
        FROM read_parquet('{bpe.as_posix()}') AS b
        INNER JOIN correspondance AS c ON b.TYPEQU = c.TYPEQU
        WHERE CAST(b.EPSG AS VARCHAR) = '2154'
    """
    equipements = con.sql(requete).df()
    equipements.to_parquet(sortie, index=False)
    return equipements


def resume(equipements: pd.DataFrame) -> pd.DataFrame:
    """Tableau de contrôle : par service, combien d'équipements, combien avec coordonnées."""
    tableau = (
        equipements.assign(avec_xy=equipements["x"].notna())
        .groupby("service")
        .agg(equipements=("typequ", "size"),
             avec_xy=("avec_xy", "sum"),
             communes=("depcom", "nunique"))
    )
    tableau["part_avec_xy_%"] = (100 * tableau["avec_xy"] / tableau["equipements"]).round(1)
    return tableau.sort_values("equipements", ascending=False)


def main() -> int:
    if not BPE.exists():
        print(f"Fichier introuvable : {BPE}. Lancez d'abord download.main().")
        return 1
    equipements = preparer()
    print(f"{len(equipements):,} équipements du panier en métropole -> {SORTIE}")
    print(resume(equipements).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
