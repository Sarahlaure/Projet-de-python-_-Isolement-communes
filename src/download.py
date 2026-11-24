"""
download.py : télécharge les fichiers de données du projet « Isolement des communes ».
 
CE QUE FAIT LE SCRIPT, EN BREF
    1. Télécharge 5 fichiers de l'INSEE (la BPE 2025 et sa documentation).
    2. Saute ceux qui sont déjà présents (on peut relancer sans risque).
    3. Vérifie que chaque fichier est bien ce qu'il prétend être (pas une page d'erreur).
    4. Télécharge et décompresse les contours IGN, la population et les revenus INSEE.
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
 
 
 
 
# ---------------------------------------------------------------------------------------
# 7. LES FICHIERS EXTERNES (IGN, POPULATION, REVENUS) : TÉLÉCHARGEMENT DEPUIS LE NOTEBOOK
# ---------------------------------------------------------------------------------------
# Ces trois fichiers étaient auparavant à récupérer à la main. Les adresses ci-dessous ont été
# vérifiées (novembre 2026). Si une adresse change, il suffit de la modifier ici.
#   - IGN Admin Express COG 2025 : archive .7z (~245 Mo) qui contient le GeoPackage (~1,1 Go).
#   - INSEE, populations de référence 2023 (en vigueur au 1er janvier 2026) : ensemble.xlsx.
#   - INSEE, Filosofi 2023 (API Melodi, jeu DS_FILOSOFI_CC) : archive .zip avec un CSV long.
GPKG_IGN = "ADE-COG_4-0_GPKG_LAMB93_FXX-ED2025-01-01.gpkg"
FICHIERS_EXTERNES: dict[str, dict[str, str]] = {
    "contours": {
        "url": "https://data.geopf.fr/telechargement/download/ADMIN-EXPRESS-COG/"
               "ADMIN-EXPRESS-COG_4-0__GPKG_LAMB93_FXX_2025-01-01/"
               "ADMIN-EXPRESS-COG_4-0__GPKG_LAMB93_FXX_2025-01-01.7z",
        "archive": "admin_express_cog_2025.7z",
        "cible": GPKG_IGN,
        "contenu": "IGN Admin Express COG 2025 : contours des communes et arrondissements "
                   "municipaux, et position des chefs-lieux (mairies).",
    },
    "population": {
        "url": "https://www.insee.fr/fr/statistiques/fichier/8680726/ensemble.xlsx",
        "cible": "population.xlsx",
        "contenu": "INSEE, populations de référence 2023 (géographie 2025), feuille « Communes ».",
    },
    "revenus": {
        "url": "https://api.insee.fr/melodi/file/DS_FILOSOFI_CC/DS_FILOSOFI_CC_2023_CSV_FR",
        "archive": "filosofi_2023.zip",
        "membre": "DS_FILOSOFI_CC_2023_data.csv",
        "cible": "filosofi_2023.csv",
        "contenu": "INSEE, Filosofi 2023 : niveau de vie médian (MED_SL) par commune.",
    },
}


def _extraire(archive: Path, membre_cherche: str, destination: Path) -> None:
    """Extrait d'une archive (.zip ou .7z) le fichier dont le nom se termine par `membre_cherche`."""
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory(dir=archive.parent) as dossier_tmp:
        dossier_tmp = Path(dossier_tmp)
        if archive.suffix == ".zip":
            import zipfile
            with zipfile.ZipFile(archive) as z:
                z.extractall(dossier_tmp)
        elif archive.suffix == ".7z":
            try:
                import py7zr
            except ImportError as erreur:
                raise ImportError("Le module py7zr est nécessaire pour ouvrir l'archive IGN : "
                                  "pip install py7zr") from erreur
            with py7zr.SevenZipFile(archive, mode="r") as z:
                z.extractall(path=dossier_tmp)
        else:
            raise ValueError(f"Format d'archive inconnu : {archive.name}")
        trouves = [p for p in dossier_tmp.rglob("*") if p.name.endswith(membre_cherche)]
        if not trouves:
            raise FileNotFoundError(f"{membre_cherche} introuvable dans {archive.name}")
        shutil.move(str(trouves[0]), destination)


def telecharger_externes(garder_archives: bool = False) -> list[str]:
    """Télécharge (et décompresse si besoin) les contours IGN, la population et les revenus.

    Comme pour la BPE, un fichier déjà présent dans data/raw/ n'est pas retéléchargé.
    Renvoie la liste des fichiers en échec.
    """
    RAW.mkdir(parents=True, exist_ok=True)
    echecs: list[str] = []
    print("Téléchargements externes (IGN, population, revenus) :")
    for cle, infos in FICHIERS_EXTERNES.items():
        cible = RAW / infos["cible"]
        print(f"- {cle} : {infos['contenu']}")
        if cible.exists() and cible.stat().st_size > 0:
            print(f"  déjà présent : {cible.name}")
            continue
        try:
            if "archive" in infos:
                archive = RAW / infos["archive"]
                telecharger(infos["url"], archive)
                print(f"  décompression de {archive.name} ...")
                _extraire(archive, infos.get("membre", infos["cible"]), cible)
                if not garder_archives:
                    archive.unlink()
            else:
                telecharger(infos["url"], cible)
            print(f"    ok : {cible.name} ({cible.stat().st_size / 1e6:.1f} Mo)")
        except Exception as erreur:  # noqa: BLE001 : on continue avec les autres fichiers
            echecs.append(cle)
            print(f"  ÉCHEC : {erreur}")
    return echecs


def tout_telecharger() -> int:
    """BPE + documentation + fichiers externes. Renvoie 0 si tout est présent, 1 sinon."""
    echecs = telecharger_tout() + telecharger_externes()
    if echecs:
        print(f"\nÉchecs : {echecs}. Relancez la cellule (les fichiers déjà présents sont conservés).")
        return 1
    print("\nTous les fichiers sont dans data/raw/.")
    return 0


# Ce bloc ne s'exécute que si on lance « python src/download.py » directement.
# Quand le notebook fait « import download », il est ignoré : on appelle alors
# download.tout_telecharger() nous-mêmes.
if __name__ == "__main__":
    sys.exit(tout_telecharger())
