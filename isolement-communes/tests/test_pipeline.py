"""Tests des fonctions de calcul sur de petits jeux de données FICTIFS dont on connaît la réponse."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import communes as cm  # noqa: E402
import descriptif as dsc  # noqa: E402
import distances as dist  # noqa: E402
import indice as idx  # noqa: E402


def petit_jeu():
    """3 communes (A, B, C) et 2 services. Coordonnées en mètres."""
    communes = pd.DataFrame({"code": ["A", "B", "C"], "x": [0.0, 10000.0, 0.0], "y": [0.0, 0.0, 20000.0]})
    equipements = pd.DataFrame({
        "depcom": ["A", "B", "B"],
        "service": ["boul", "boul", "pharm"],
        "x": [500.0, np.nan, 10000.0],
        "y": [0.0, np.nan, 0.0],
        "qualite_xy": ["B", "_Z", "M"],
    })
    return communes, equipements


def test_presence():
    communes, equipements = petit_jeu()
    p = dist.presence_par_service(communes["code"], equipements, ["boul", "pharm"])
    assert p.loc["A"].tolist() == [True, False]
    assert p.loc["B"].tolist() == [True, True]
    assert p.loc["C"].tolist() == [False, False]


def test_distances_regle_principale():
    communes, equipements = petit_jeu()
    d, _ = dist.distances_par_service(communes, equipements, ["boul", "pharm"])
    # boulangerie : A et B ont le service (B n'a pas de coordonnées mais compte) -> 0
    assert d.loc["A", "boul"] == 0 and d.loc["B", "boul"] == 0
    assert d.loc["C", "boul"] == pytest.approx(np.hypot(500, 20000) / 1000)
    # pharmacie : seule B en a une ; A est à 10 km, C à sqrt(10^2 + 20^2) km
    assert d.loc["B", "pharm"] == 0
    assert d.loc["A", "pharm"] == pytest.approx(10.0)
    assert d.loc["C", "pharm"] == pytest.approx(np.hypot(10000, 20000) / 1000)


def test_distances_filtre_qualite_et_variante():
    communes, equipements = petit_jeu()
    # La pharmacie de B a la qualité « M » : exclue avec qualites=["A", "B"]
    d, _ = dist.distances_par_service(communes, equipements, ["pharm"], qualites=["A", "B"])
    assert d.loc["B", "pharm"] == 0               # la présence n'est pas filtrée
    assert np.isnan(d.loc["A", "pharm"])          # plus aucun équipement localisé
    # Variante sans règle de présence : A est à 0,5 km de sa boulangerie, pas à 0
    d2, _ = dist.distances_par_service(communes, equipements, ["boul"], regle_presence=False)
    assert d2.loc["A", "boul"] == pytest.approx(0.5)


def test_controle_codes():
    _, equipements = petit_jeu()
    bilan = dist.controle_codes(equipements, ["A", "C"])
    assert bilan["equipements_sans_commune"] == 2 and bilan["codes_inconnus"] == ["B"]


def test_standardiser():
    t = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [5.0, 5.0, 5.0]})
    z = idx.standardiser(t)
    assert z["a"].mean() == pytest.approx(0) and z["a"].std(ddof=0) == pytest.approx(1)
    assert (z["b"] == 0).all()


def test_poids():
    services = ["boulangerie", "pharmacie", "ecole", "gare"]
    assert idx.poids_egaux(services) == {s: 1.0 for s in services}
    assert idx.poids_vitaux(services)["pharmacie"] == 2.0 and idx.poids_vitaux(services)["gare"] == 1.0
    pt = idx.poids_themes_equilibres(["pharmacie", "medecin", "gare"])
    assert pt["pharmacie"] == pytest.approx(0.5) and pt["gare"] == pytest.approx(1.0)


def test_indice_et_acp():
    rng = np.random.default_rng(0)
    d = pd.DataFrame(rng.exponential(5, size=(200, 3)), columns=["pharmacie", "ecole", "gare"],
                     index=[f"c{i}" for i in range(200)])
    z = idx.standardiser(idx.log_distance(d))
    i_egal = idx.indice_pondere(z, idx.poids_egaux(z.columns))
    assert i_egal.mean() == pytest.approx(0, abs=1e-9)
    # la commune la plus loin de tout a l'indice le plus haut
    assert i_egal.idxmax() == z.sum(axis=1).idxmax()
    scores, part = idx.indice_acp(z, i_egal)
    assert 0 < part <= 1
    assert np.corrcoef(scores, i_egal)[0, 1] > 0  # orienté comme la référence
    rho = idx.comparer_classements(pd.DataFrame({"egal": i_egal, "acp": scores}))
    assert rho.loc["egal", "egal"] == pytest.approx(1)


def test_assembler_base():
    communes = pd.DataFrame({
        "code": ["75056", "13055", "01001", "2A004", "97101"],
        "nom": list("abcde"), "population": [1000, 800, 50, 30, 400],
        "x": 0.0, "y": 0.0, "surface_km2": [100, 80, 5, 3, 40]})
    arr = pd.DataFrame({
        "code": ["75101", "75102", "13201"], "nom": list("fgh"),
        "population": [10, 20, 30], "x": 0.0, "y": 0.0, "surface_km2": [1, 2, 3],
        "parent": ["75056", "75056", "13055"]})
    base = cm.assembler_base(communes, arr)
    assert base["code"].tolist() == ["01001", "13201", "2A004", "75101", "75102"]
    assert base.loc[base.code == "01001", "densite"].iloc[0] == pytest.approx(10.0)
    doublon = pd.concat([communes, communes.iloc[[2]]], ignore_index=True)
    with pytest.raises(ValueError):
        cm.assembler_base(doublon, arr)


def test_fusionner_population():
    base = pd.DataFrame({"code": ["01001", "01002", "2A004"], "population": [np.nan, 10.0, np.nan],
                         "surface_km2": [1.0, 2.0, 4.0]})
    ext = pd.DataFrame({"COM": [1001, "2A004", "99999"], "PMUN": ["200", 80, 5]})  # 1001 = code sans zéro
    res, journal = cm.fusionner_population(base, ext, "COM", "PMUN")
    assert res.set_index("code")["population"].to_dict() == {"01001": 200.0, "01002": 10.0, "2A004": 80.0}
    assert journal["communes_sans_population_ext"] == 1 and journal["codes_ext_hors_base"] == 1
    assert res.set_index("code").loc["2A004", "densite"] == pytest.approx(20.0)


def test_descriptif():
    d = pd.DataFrame({"s": [0.0, 5.0, 20.0]}, index=["a", "b", "c"])
    pop = pd.Series([100, 100, 800], index=["a", "b", "c"])
    part = dsc.part_population_eloignee(d, pop, [10])
    assert part.loc["s", "> 10 km"] == pytest.approx(80.0)
    r = dsc.resume_par_service(d)
    assert r.loc["s", "communes_equipees_%"] == pytest.approx(33.3)


def test_chaine_complete_fictive():
    """Mini-France : 400 communes, 4 services. L'indice doit être élevé pour une commune isolée."""
    rng = np.random.default_rng(1)
    n = 400
    communes = pd.DataFrame({"code": [f"{i:05d}" for i in range(n)],
                             "x": rng.uniform(0, 100000, n), "y": rng.uniform(0, 100000, n)})
    # un hameau très isolé, loin de tout, dans un coin
    communes.loc[0, ["x", "y"]] = [-200000.0, -200000.0]
    services = ["boulangerie", "pharmacie", "ecole", "gare"]
    lignes = []
    for s, p in zip(services, [0.5, 0.3, 0.6, 0.05]):
        choisies = communes.sample(frac=p, random_state=2)
        choisies = choisies[choisies["code"] != "00000"]
        lignes.append(pd.DataFrame({"depcom": choisies["code"], "service": s,
                                    "x": choisies["x"] + 100, "y": choisies["y"], "qualite_xy": "B"}))
    equipements = pd.concat(lignes, ignore_index=True)
    d, presence = dist.distances_par_service(communes, equipements, services)
    assert not d.isna().any().any()
    assert (d.where(presence, 0) == 0).all().all()  # présence -> 0
    i = idx.calculer_indice(d, idx.poids_egaux(services))
    assert i.idxmax() == "00000"
