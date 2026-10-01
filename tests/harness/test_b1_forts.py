"""R11 test-fort programme (scripts/b1-forts.py) and its eco-run baseline blocks, offline."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


b1 = load("b1forts", "b1-forts.py")


def test_pick_on_region6_survey_covers_every_need_and_biome():
    survey = b1.read_tsv(ROOT / "data/forts/region6-survey.tsv")
    picks = b1.pick(survey)
    needs = {p["need"] for p in picks if p.get("save")}
    assert {"shore", "lake", "river", "savage", "calm", "good", "evil"} <= needs
    land_biomes = {r["biome"] for r in survey if not r["biome"].startswith(("OCEAN", "LAKE"))}
    assert {n[6:] for n in needs if n.startswith("biome:")} == land_biomes
    saves = [p["save"] for p in picks if p.get("save")]
    assert len(saves) == len(set(saves))
    assert len({(p["rx"], p["ry"]) for p in picks if p.get("save")}) == len(saves)   # one fort per tile
    for p in picks:
        if p["need"] == "good":
            assert int(p["evil"]) < 33
        if p["need"] == "evil":
            assert int(p["evil"]) >= 66
        if p["need"] == "calm":
            assert int(p["sav"]) < 33
        if p["need"] == "savage":
            assert int(p["sav"]) >= 66


def test_shore_offset_faces_the_ocean():
    grid = {(5, 5): {"biome": "TUNDRA"}, (6, 5): {"biome": "OCEAN_ARCTIC"}}
    assert b1.ocean_side(grid, 5, 5) == (15, 7)
    grid = {(5, 5): {"biome": "TUNDRA"}, (5, 4): {"biome": "OCEAN_ARCTIC"}}
    assert b1.ocean_side(grid, 5, 5) == (7, 0)


def test_missing_needs_are_reported_not_invented():
    survey = [dict(x="0", y="0", biome="MOUNTAIN", sav="50", evil="50", site="0", same8="8", volcano="0",
                   river="0", major="0", lake="0", nbr_ocean="0")]
    picks = b1.pick(survey)
    missing = {p["need"] for p in picks if not p.get("save")}
    assert {"shore", "lake", "river", "savage", "calm", "good", "evil"} == missing


def test_eco_run_builds_a_baseline_block_per_registered_fort(tmp_path, monkeypatch):
    sys.argv = ["eco-run.py"]
    er = load("ecorun", "eco-run.py")
    reg = tmp_path / "b1-forts.tsv"
    reg.write_text("save\tstatus\tspot\nB1-R8-FTCN-12_40\tok\tland\nB1-R8-OCNT-03_17-SHORE\tfailed\tland\n")
    er._b1_blocks(reg)
    assert "B1BASE_B1-R8-FTCN-12_40" in er.BLOCKS
    assert "B1BASE_B1-R8-OCNT-03_17-SHORE" not in er.BLOCKS
    blk = er.BLOCKS["B1BASE_B1-R8-FTCN-12_40"]
    assert blk["wipe"] is False and blk["fort"] == "B1-R8-FTCN-12_40"
    assert any(s.startswith("groups3") for s in blk["cells"]["baseline"]["steps"])
