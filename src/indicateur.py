"""
indicateur.py : calcule l'indicateur d'éloignement aux services de chaque commune.

CE QUE FAIT LE SCRIPT, EN BREF
    1. Définit le panier de 19 services et le poids de chacun (grille de notation).
    2. Récupère la liste des communes (geo.api.gouv.fr) et leur centre.
    3. Pour chaque commune et chaque service :
         - 0 km si la commune possède le service,
         - sinon la distance (km, à vol d'oiseau) entre son centre et l'équipement le plus proche.
    4. Agrège ces 19 distances en un indicateur unique : la moyenne pondérée des distances.
    5. Écrit les résultats dans data/processed/.

Champ : France métropolitaine (Corse incluse). Paris, Lyon et Marseille sont traités par
arrondissement municipal, comme dans la BPE.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.neighbors import BallTree 

#Ball Tree : structure de donnée de sklearn qui permet rapidement de trouver le point le plus proche

RACINE = Path(__file__).resolve().parents[1]
RAW = RACINE / "data" / "raw"
PROCESSED = RACINE / "data" / "processed"

RAYON_TERRE_KM = 6371.0

# ---------------------------------------------------------------------------------------
# 1. LE PANIER DE SERVICES ET LEURS POIDS
# ---------------------------------------------------------------------------------------
# Chaque service est noté sur trois critères :
#   E (essentialité)  : 2 = vital ou obligatoire, 1 = important, 0 = confort / loisir
#   F (fréquence)     : 2 = quotidien ou hebdomadaire, 1 = mensuel à quelques fois par an,
#                       0 = rare ou exceptionnel
#   P (public)        : 1 = presque toute la population, 0 = un public particulier
# Score = 1 + E + F + P (entre 1 et 6). Poids = score / somme des scores.
# Un service peut regrouper plusieurs codes TYPEQU (ex. école = maternelle, primaire,
# élémentaire) : la commune « possède » le service si elle a au moins un de ces codes.

# Les pondérations sont faite à la main, à revoir pour être sûr qu'il n'y a pas de biais.
PANIER: dict[str, dict] = {
    "alimentation": {
        "libelle": "Commerce alimentaire général",
        "codes": ["B104", "B105", "B201", "B202"],
        "E": 2, "F": 2, "P": 1,
        "raison": "Hypermarché, supermarché, supérette ou épicerie : se nourrir, "
                  "plusieurs fois par semaine, pour tous.",
    },
    "medecin": {
        "libelle": "Médecin généraliste",
        "codes": ["D265"],
        "E": 2, "F": 1, "P": 1,
        "raison": "Porte d'entrée du système de soins (médecin traitant), recours "
                  "plusieurs fois par an pour toute la population.",
    },
    "pharmacie": {
        "libelle": "Pharmacie",
        "codes": ["D307"],
        "E": 2, "F": 1, "P": 1,
        "raison": "Seul accès aux médicaments ; recours régulier, surtout des personnes âgées.",
    },
    "ecole": {
        "libelle": "École maternelle ou élémentaire",
        "codes": ["C107", "C108", "C109"],
        "E": 2, "F": 2, "P": 0,
        "raison": "Instruction obligatoire dès 3 ans, trajet quotidien, "
                  "mais concerne seulement les familles avec jeunes enfants.",
    },
    "college": {
        "libelle": "Collège",
        "codes": ["C201"],
        "E": 2, "F": 2, "P": 0,
        "raison": "Scolarité obligatoire jusqu'à 16 ans, trajet quotidien, public : 11-15 ans.",
    },
    "boulangerie": {
        "libelle": "Boulangerie-pâtisserie",
        "codes": ["B207"],
        "E": 1, "F": 2, "P": 1,
        "raison": "Commerce de proximité le plus fréquenté ; substituable en partie "
                  "par le commerce alimentaire général.",
    },
    "urgences": {
        "libelle": "Service d'urgences",
        "codes": ["D106"],
        "E": 2, "F": 0, "P": 1,
        "raison": "Vital : le temps d'accès conditionne la survie (AVC, infarctus), "
                  "mais recours rare.",
    },
    "poste": {
        "libelle": "Bureau, agence ou relais de poste",
        "codes": ["A206", "A207", "A208"],
        "E": 1, "F": 1, "P": 1,
        "raison": "Courrier, colis, services bancaires de base ; recours mensuel.",
    },
    "station_service": {
        "libelle": "Station-service",
        "codes": ["B316"],
        "E": 1, "F": 1, "P": 1,
        "raison": "Indispensable là où la voiture est le seul moyen de transport.",
    },
    "lycee": {
        "libelle": "Lycée (général, techno. ou pro.)",
        "codes": ["C301", "C302", "C303"],
        "E": 1, "F": 2, "P": 0,
        "raison": "Formation obligatoire jusqu'à 18 ans, trajet quotidien, public : 15-18 ans.",
    },
    "petite_enfance": {
        "libelle": "Crèche ou micro-crèche",
        "codes": ["D502", "D509"],
        "E": 1, "F": 2, "P": 0,
        "raison": "Condition de l'emploi des parents, trajet quotidien, public : 0-3 ans.",
    },
    "infirmier": {
        "libelle": "Infirmier",
        "codes": ["D281"],
        "E": 1, "F": 1, "P": 0,
        "raison": "Soins réguliers pour les malades chroniques et les personnes âgées.",
    },
    "dentiste": {
        "libelle": "Chirurgien-dentiste",
        "codes": ["D277"],
        "E": 1, "F": 0, "P": 1,
        "raison": "Soins courants pour tous, une à deux fois par an.",
    },
    "maternite": {
        "libelle": "Maternité",
        "codes": ["D107"],
        "E": 2, "F": 0, "P": 0,
        "raison": "Vital lors de l'accouchement, mais rare et pour un public particulier.",
    },
    "securite": {
        "libelle": "Gendarmerie ou commissariat de police",
        "codes": ["A104", "A140"],
        "E": 1, "F": 0, "P": 1,
        "raison": "Dépôt de plainte, sécurité ; recours rare (l'intervention vient à "
                  "domicile).",
    },
    "banque": {
        "libelle": "Agence bancaire",
        "codes": ["A203"],
        "E": 1, "F": 0, "P": 1,
        "raison": "Retrait d'espèces et conseil ; largement remplacée par la banque en ligne.",
    },
    "france_services": {
        "libelle": "France Services",
        "codes": ["A128"],
        "E": 1, "F": 0, "P": 1,
        "raison": "Aide aux démarches administratives (CAF, impôts, retraite), "
                  "occasionnelle.",
    },
    "gare": {
        "libelle": "Gare de voyageurs",
        "codes": ["E107", "E108", "E109"],
        "E": 0, "F": 1, "P": 1,
        "raison": "Seule alternative à la voiture pour les longs trajets ; non vitale.",
    },
    "bibliotheque": {
        "libelle": "Bibliothèque",
        "codes": ["F307"],
        "E": 0, "F": 0, "P": 1,
        "raison": "Accès à la culture, ouvert à tous ; confort plutôt que besoin.",
    },
}

DEPARTEMENTS_METRO = {f"{i:02d}" for i in range(1, 96) if i != 20} | {"2A", "2B"}
CODES_PLM = {"75056", "69123", "13055"}  # remplacés par leurs arrondissements


def table_poids() -> pd.DataFrame:
    """Tableau du panier : une ligne par service, avec notes, score et poids."""
    t = pd.DataFrame.from_dict(PANIER, orient="index")
    t["score"] = 1 + t["E"] + t["F"] + t["P"]
    t["poids"] = t["score"] / t["score"].sum()
    return t


# ---------------------------------------------------------------------------------------
# 2. LES COMMUNES ET LEUR CENTRE
# ---------------------------------------------------------------------------------------


#Le point important ici, l'indicateur utilisera la distance entre la ville et le service le plus proche si il n'est pas
## disponible dans la ville. Pour cela il faut choisir un point de référence pour la ville, j'ai choisi la mairie.

def charger_communes() -> pd.DataFrame:
    """Liste des communes et arrondissements municipaux de métropole (geo.api.gouv.fr).

    Le fichier est gardé dans data/raw/communes_geoapi.json pour ne pas le retélécharger.
    """
    fichier = RAW / "communes_geoapi.json"
    if not fichier.exists():
        champs = "code,nom,centre,population,surface,codeDepartement"
        url = "https://geo.api.gouv.fr/communes"
        communes = requests.get(url, params={"fields": champs}, timeout=120).json()
        arrondissements = requests.get(
            url, params={"fields": champs, "type": "arrondissement-municipal"}, timeout=120
        ).json()
        fichier.write_text(json.dumps(communes + arrondissements, ensure_ascii=False))

    c = pd.DataFrame(json.loads(fichier.read_text()))
    c = c[c["codeDepartement"].isin(DEPARTEMENTS_METRO) & ~c["code"].isin(CODES_PLM)]
    c["lon_geo"] = c["centre"].map(lambda p: p["coordinates"][0])
    c["lat_geo"] = c["centre"].map(lambda p: p["coordinates"][1])
    c = c.rename(columns={"code": "DEPCOM", "codeDepartement": "DEP"})
    # surface en hectares dans l'API -> densité en habitants par km²
    c["densite"] = c["population"] / (c["surface"] / 100)
    return c[["DEPCOM", "nom", "DEP", "population", "densite", "lat_geo", "lon_geo"]]


def charger_bpe() -> pd.DataFrame:
    """Équipements de la BPE 2025 situés en métropole (EPSG 2154 = Lambert 93)."""
    colonnes = ["DEPCOM", "TYPEQU", "LATITUDE", "LONGITUDE", "QUALITE_XY", "EPSG"]
    bpe = pd.read_parquet(RAW / "BPE25.parquet", columns=colonnes)
    return bpe[bpe["EPSG"] == "2154"].drop(columns="EPSG")


def centres_communes(communes: pd.DataFrame, bpe: pd.DataFrame) -> pd.DataFrame:
    """Choisit le point de départ de chaque commune.

    - Par défaut : la mairie (code A129), bien géolocalisée (qualité A ou B). C'est le
      chef-lieu, cœur historique du bourg, là où vivent la plupart des habitants.
    - Sinon (pas de mairie, ou mairie mal géolocalisée) : le centre géographique fourni par
      geo.api.gouv.fr.
    - Si une commune a plusieurs mairies (communes nouvelles avec mairies annexes), on garde
      la plus proche du centre géographique.
    """
    mairies = bpe[(bpe["TYPEQU"] == "A129") & bpe["QUALITE_XY"].isin(["A", "B"])]
    mairies = mairies.merge(communes[["DEPCOM", "lat_geo", "lon_geo"]], on="DEPCOM")
    mairies["ecart"] = np.hypot(
        mairies["LATITUDE"] - mairies["lat_geo"], mairies["LONGITUDE"] - mairies["lon_geo"]
    )
    mairies = mairies.sort_values("ecart").drop_duplicates("DEPCOM")
    mairies = mairies.set_index("DEPCOM")[["LATITUDE", "LONGITUDE"]]

    c = communes.set_index("DEPCOM")
    c["source_centre"] = np.where(c.index.isin(mairies.index), "mairie", "centre geo.api")
    c["lat"] = mairies["LATITUDE"].reindex(c.index).fillna(c["lat_geo"])
    c["lon"] = mairies["LONGITUDE"].reindex(c.index).fillna(c["lon_geo"])
    return c.reset_index()


# ---------------------------------------------------------------------------------------
# 3. DISTANCE AU SERVICE LE PLUS PROCHE
# ---------------------------------------------------------------------------------------

def en_radians(lat: pd.Series, lon: pd.Series) -> np.ndarray:
    """BallTree avec la métrique « haversine » (vol d'oiseau) attend des [latitude, longitude] en radians."""
    return np.radians(np.column_stack([lat.to_numpy(float), lon.to_numpy(float)]))


def distances_services(centres: pd.DataFrame, bpe: pd.DataFrame) -> pd.DataFrame:
    """Tableau commune x service des distances en km (0 si la commune a le service).

    La présence se lit sur le code commune (DEPCOM) : un équipement sans coordonnées
    compte donc quand même. La distance, elle, n'utilise que les équipements géolocalisés.
    """
    points_communes = en_radians(centres["lat"], centres["lon"])
    resultat = pd.DataFrame({"DEPCOM": centres["DEPCOM"]})

    for service, infos in PANIER.items():
        equipements = bpe[bpe["TYPEQU"].isin(infos["codes"])]
        presents = set(equipements["DEPCOM"])

        geolocalises = equipements.dropna(subset=["LATITUDE", "LONGITUDE"])
        arbre = BallTree(en_radians(geolocalises["LATITUDE"], geolocalises["LONGITUDE"]),
                         metric="haversine")
        distance, _ = arbre.query(points_communes, k=1)
        distance_km = distance[:, 0] * RAYON_TERRE_KM

        resultat[service] = np.where(centres["DEPCOM"].isin(presents), 0.0, distance_km)
    return resultat


# ---------------------------------------------------------------------------------------
# 4. L'INDICATEUR
# ---------------------------------------------------------------------------------------
def indicateur(distances: pd.DataFrame, poids: pd.Series) -> pd.Series:
    """Moyenne des distances pondérée par l'importance des services (en km)."""
    return distances[poids.index] @ (poids / poids.sum())


def calculer() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chaîne complète. Renvoie (table des poids, table finale par commune)."""
    poids = table_poids()
    bpe = charger_bpe()
    centres = centres_communes(charger_communes(), bpe)
    d = distances_services(centres, bpe)

    final = centres.merge(d, on="DEPCOM")
    services = list(PANIER)
    final["indicateur"] = indicateur(final, poids["poids"])

    # Variantes pour tester la robustesse du choix des poids et de l'échelle
    final["indic_poids_egaux"] = final[services].mean(axis=1) # tout les poids = 1/19
    distance_moyenne = final[services].mean()  # distance moyenne nationale par service
    final["indic_normalise"] = indicateur(final[services] / distance_moyenne, poids["poids"]) # plus normalisée
    final["nb_services_absents"] = (final[services] > 0).sum(axis=1)
    return poids, final


if __name__ == "__main__":
    PROCESSED.mkdir(parents=True, exist_ok=True)
    poids, final = calculer()
    poids.drop(columns="codes").to_csv(PROCESSED / "poids_services.csv") 
    final.to_csv(PROCESSED / "indicateur_communes.csv", index=False)
    print(poids[["libelle", "E", "F", "P", "score", "poids"]].round(3).to_string())
    print(final[["indicateur", "indic_poids_egaux", "indic_normalise"]].describe().round(2))

