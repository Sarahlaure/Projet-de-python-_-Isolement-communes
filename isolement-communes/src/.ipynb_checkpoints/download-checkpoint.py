"""
download.py : télécharge les fichiers de données du projet « Isolement des communes ».
 
CE QUE FAIT LE SCRIPT, EN BREF
    1. Télécharge 5 fichiers de l'INSEE (la BPE 2025 et sa documentation).
    2. Saute ceux qui sont déjà présents (on peut relancer sans risque).
    3. Vérifie que chaque fichier est bien ce qu'il prétend être (pas une page d'erreur).
    4. Liste les fichiers à télécharger à la main (pas d'adresse stable) et dit s'ils manquent.
"""
from __future__ import annotations
 
import sys
from pathlib import Path
 
import requests
 
# ---------------------------------------------------------------------------------------
# 1. Dossier où seront stockés les fichiers
# ---------------------------------------------------------------------------------------

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
 
# ---------------------------------------------------------------------------------------
# 2. LES FICHIERS TÉLÉCHARGÉS AUTOMATIQUEMENT
# ---------------------------------------------------------------------------------------
# Chaque entrée : nom du fichier local -> (adresse, ce que c'est, à quoi il sert).
# Source : page INSEE « Équipements géolocalisés en 2025 - Fichier détail »
#          https://www.insee.fr/fr/statistiques/8217525
FICHIERS_AUTO: dict[str, dict[str, str]] = {
    "BPE25.parquet": {
        "url": "https://www.insee.fr/fr/statistiques/fichier/8217525/BPE25.parquet",
        "contenu": "La Base permanente des équipements 2025 : une ligne par équipement "
                   "(médecin, école, boulangerie, gare...), avec son type, sa commune et sa "
                   "position. Format parquet (colonnes compressées, ~163 Mo).",
        "utilite": "elle dit où se trouvent les services. "
                   "Les distances seront calculées à partir de ces positions.",
    },
    "TYPEQU_2025.csv": {
        "url": "https://www.insee.fr/fr/metadonnees/source/fichier/TYPEQU_2025.csv",
        "contenu": "Le dictionnaire des types d'équipements : à chaque code (ex. D265) "
                   "correspond un libellé (ex. médecin généraliste).",
        "utilite": "Comprendre les codes TYPEQU, choisir le panier de services et pouvoir ",

    },
    "BPE25_dessin_fichier.csv": {
        "url": "https://www.insee.fr/fr/metadonnees/source/fichier/BPE25_anonymisee_dessin_fichier.csv",
        "contenu": "Le « dessin de fichier » : la liste des colonnes de la BPE 2025 avec "
                   "leur nom, leur type et leur longueur.",
        "utilite": "Savoir quelle colonne contient le code commune, les coordonnées, etc. ",
                  
    },
    "BPE25_varmod.csv": {
        "url": "https://www.insee.fr/fr/metadonnees/source/fichier/BPE25_anonymisee_varmod.csv",
        "contenu": "Le dictionnaire des variables et de leurs modalités : pour chaque colonne, "
                   "les valeurs possibles et leur signification (ex. les niveaux de qualité "
                   "de la géolocalisation).",
        "utilite": "Interpréter correctement les colonnes codées, notamment la qualité des "
                   "coordonnées, pour décider quels équipements garder.",
    },
    "BPE25_table_passage.csv": {
        "url": "https://www.insee.fr/fr/metadonnees/source/fichier/BPE25_table_passage.csv",
        "contenu": "La table de passage domaine -> sous-domaine -> type d'équipement : elle "
                   "range les types dans de grandes familles (commerces, santé, "
                   "enseignement, transports...).",
        "utilite": "Organiser le panier de services par thème et expliquer à quelle famille "
                   "appartient chaque service.",
    },
}
 
 
# ---------------------------------------------------------------------------------------
# 3. LES FICHIERS À TÉLÉCHARGER À LA MAIN
# ---------------------------------------------------------------------------------------

FICHIERS_MANUELS: dict[str, dict[str, str]] = {
    "population": {
        "ou": "https://www.data.gouv.fr/datasets/populations-de-reference",
        "choisir": "Population municipale 2023, en géographie 2025 (communes + arrondissements).",
        "utilite": "Compter les HABITANTS concernés par l'éloignement (et non les communes) "
                   "et calculer la densité.",
    },
    "contours": {
        "ou": "https://geoservices.ign.fr/adminexpress",
        "choisir": "Admin Express, édition COG 2025 : couches COMMUNE et "
                   "ARRONDISSEMENT_MUNICIPAL.",
        "utilite": "Donner à chaque commune un point de départ (son centre) pour les "
                   "distances, et fabriquer les cartes. Les arrondissements sont "
                   "indispensables : la BPE code Paris, Lyon et Marseille par arrondissement.",
    },
    "revenus": {
        "ou": "https://www.insee.fr (chercher « Filosofi » niveau commune)",
        "choisir": "Dernier millésime communal disponible (le millésime 2022 n'a pas été "
                   "produit par l'INSEE).",
        "utilite": "Savoir si l'isolement recoupe la pauvreté (revenu médian par commune).",
    },
}
 
 
# ---------------------------------------------------------------------------------------
# 4. TÉLÉCHARGER UN FICHIER
# ---------------------------------------------------------------------------------------
def telecharger(url: str, destination: Path, taille_bloc: int = 1 << 20) -> None:
    """Télécharge `url` vers `destination`, par blocs, sans tout charger en mémoire.
 
    - Si le fichier existe déjà et n'est pas vide, on ne le retélécharge pas.
    - On écrit d'abord dans un fichier temporaire « .part », renommé seulement à la fin.
      Ainsi, si la connexion coupe en route, on ne garde pas un fichier tronqué qu'on
      prendrait ensuite pour un fichier complet.
    - `taille_bloc` = 1 << 20 = 1 Mo : on lit et on écrit 1 Mo à la fois (utile pour un
      fichier de 163 Mo).
    """
    if destination.exists() and destination.stat().st_size > 0:
        print(f"  déjà présent : {destination.name}")
        return
 
    print(f"  téléchargement : {destination.name} ...")
    temporaire = destination.with_suffix(destination.suffix + ".part")
 
    with requests.get(
        url, stream=True, timeout=120, headers={"User-Agent": "projet-ensae-python"}
    ) as reponse:
        reponse.raise_for_status()  # lève une erreur si le serveur répond 403, 404, 500...
        with open(temporaire, "wb") as fichier:
            for bloc in reponse.iter_content(chunk_size=taille_bloc):
                fichier.write(bloc)
 
    temporaire.rename(destination)  # le fichier est complet : on lui donne son vrai nom
    print(f"    ok ({destination.stat().st_size / 1e6:.1f} Mo)")
 
 
# ---------------------------------------------------------------------------------------
# 5. VÉRIFIER QU'UN FICHIER EST BIEN CE QU'IL PRÉTEND ÊTRE
# ---------------------------------------------------------------------------------------
def verifier(destination: Path) -> bool:
    """Contrôle simple de cohérence d'un fichier téléchargé.
 
    Un site peut répondre « succès » mais renvoyer une page web (HTML) à la place du
    fichier demandé. On vérifie donc :
    - un fichier .parquet commence toujours par les 4 octets « PAR1 » (sa « signature »),
    - un fichier .csv ne doit pas commencer par « < » (début d'une page HTML).
    """
    with open(destination, "rb") as fichier:
        debut = fichier.read(4)
    if destination.suffix == ".parquet":
        return debut == b"PAR1"
    if destination.suffix == ".csv":
        return not debut.lstrip().startswith(b"<")
    return True
 
 
# ---------------------------------------------------------------------------------------
# 6. LE PROGRAMME PRINCIPAL
# ---------------------------------------------------------------------------------------
def telecharger_tout() -> list[str]:
    """Télécharge les fichiers automatiques et renvoie la liste de ceux qui ont échoué."""
    RAW.mkdir(parents=True, exist_ok=True)  # crée data/raw/ s'il n'existe pas encore
    echecs: list[str] = []
 
    print("Téléchargements automatiques (INSEE, BPE 2025) :")
    for nom, infos in FICHIERS_AUTO.items():
        print(f"- {nom} : {infos['contenu']}")
        try:
            telecharger(infos["url"], RAW / nom)
            if not verifier(RAW / nom):
                # On supprime le fichier invalide, sinon le prochain lancement le
                # prendrait pour un fichier correct (« déjà présent »).
                (RAW / nom).unlink()
                raise ValueError("le contenu ne ressemble pas au format attendu")
        except Exception as erreur:  # noqa: BLE001 : on veut continuer avec les autres
            echecs.append(nom)
            print(f"  ÉCHEC : {erreur}")
    return echecs
 
 
def afficher_fichiers_manuels() -> None:
    """Explique les fichiers à télécharger à la main et signale ceux qui manquent."""
    print("\nFichiers à télécharger À LA MAIN (à placer dans data/raw/) :")
    for cle, infos in FICHIERS_MANUELS.items():
        print(f"- {cle}")
        print(f"    où      : {infos['ou']}")
        print(f"    choisir : {infos['choisir']}")
        print(f"    utilité : {infos['utilite']}")
 
    presents = sorted(p.name for p in RAW.iterdir()) if RAW.exists() else []
    print(f"\nContenu actuel de data/raw/ : {presents}")
 
 
def main() -> int:
    """Point d'entrée : télécharge, signale les échecs, rappelle les fichiers manuels.
 
    Renvoie 0 si tout s'est bien passé, 1 s'il y a eu au moins un échec.
    """
    echecs = telecharger_tout()
    afficher_fichiers_manuels()
    if echecs:
        print(f"\nÉchecs : {echecs}. Relancez, ou téléchargez-les à la main depuis la page INSEE.")
        return 1
    print("\nTéléchargements automatiques terminés.")
    return 0
 
 
# Ce bloc ne s'exécute que si on lance « python src/download.py » directement.
# Quand le notebook fait « import download », il est ignoré : on appelle alors
# download.main() nous-mêmes.
if __name__ == "__main__":
    sys.exit(main())

