"""Tests pour le module des Technologies Primitives et Troc (M13)."""
from fastapi.testclient import TestClient

from api.main import app
from engine.engine import Universe
from engine.technology import TECH_CATALOG, ClanTechState, TechnologyRegistry


def test_tech_catalog_definitions():
    assert "flint_knapping" in TECH_CATALOG
    assert "fire_mastery" in TECH_CATALOG
    assert "bow_and_arrow" in TECH_CATALOG
    assert "herbal_remedies" in TECH_CATALOG
    # Vérifier que les prérequis existent
    for tid, tdef in TECH_CATALOG.items():
        for req in tdef.prerequisites:
            assert req in TECH_CATALOG, f"Prérequis {req} manquant pour {tid}"


def test_clan_tech_state():
    state = ClanTechState(1, unlocked_techs=["flint_knapping", "fire_mastery"])
    assert state.has("flint_knapping")
    assert not state.has("bow_and_arrow")
    assert state.total_food_bonus() > 0.2
    assert state.total_health_bonus() > 0.15

    d = state.to_dict()
    state2 = ClanTechState.from_dict(d)
    assert state2.clan_id == state.clan_id
    assert state2.unlocked_techs == state.unlocked_techs


def test_technology_registry_genesis_and_step():
    u = Universe("u-tech-test", seed=77)
    reg = u.technology
    assert len(reg.clan_states) > 0
    first_clan_id = next(iter(u.society.clans.keys()))
    assert reg.get_or_create(first_clan_id).has("flint_knapping")

    # Step technique
    evs = reg.step(u.tick, 1, u.society, u.world, u.rng)
    assert isinstance(evs, list)


def test_universe_snapshot_with_technology():
    u = Universe("tech-save-u", 33)
    snap = u.snapshot()
    u2 = Universe.from_snapshot(snap)
    assert len(u2.technology.clan_states) == len(u.technology.clan_states)
    assert "technologies_known" in u2.info()


def test_api_technology_endpoints():
    client = TestClient(app)
    res = client.get("/universes/main/technology")
    assert res.status_code == 200
    data = res.json()
    assert "catalog" in data
    assert "clans_technology" in data
    assert len(data["catalog"]) >= 8
    assert len(data["clans_technology"]) >= 1

    # Vérifier enrichissement de /clans/{id}
    res_clan = client.get("/universes/main/clans/1")
    assert res_clan.status_code == 200
    clan_data = res_clan.json()
    assert "technologies" in clan_data
    assert "language" in clan_data
    assert isinstance(clan_data["technologies"], list)
