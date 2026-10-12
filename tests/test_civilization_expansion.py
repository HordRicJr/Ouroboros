"""Tests pour M17 (Disasters), M18 (Religion/Pantheon) et M19 (Settlement Tiers)."""
from fastapi.testclient import TestClient

from api.main import app
from engine.disasters import DisasterManager
from engine.engine import Universe
from engine.religion import ReligionRegistry
from engine.settlement import SettlementManager


def test_disaster_trigger_and_effects():
    u = Universe("disaster-test-u", seed=101)
    dm: DisasterManager = u.disasters
    d = dm.trigger_disaster(
        kind="volcano",
        name="L'Éruption Noire",
        center=(50, 50),
        radius=30,
        severity=0.8,
        duration=365,
        tick=u.tick,
    )
    assert d.id == 1
    assert d.active is True
    assert len(dm.active_disasters()) == 1

    evs = dm.step(u.tick, 0, u.world, u.climate, u.eco, u.society, u.people, u.rng)
    assert dm.climate_temp_offset < 0.0  # Refroidissement volcanique actif
    assert isinstance(evs, list)


def test_religion_pantheon_and_sacred_sites():
    reg = ReligionRegistry.genesis(Universe("u-rel", 42).rng)
    assert len(reg.deities) >= 4
    first_deity = next(iter(reg.deities.values()))
    assert first_deity.name
    assert first_deity.domain

    d = reg.to_dict()
    reg2 = ReligionRegistry.from_dict(d)
    assert len(reg2.deities) == len(reg.deities)


def test_settlement_tiers_and_defense():
    u = Universe("u-settle", 77)
    sm = SettlementManager.genesis(u.society)
    assert len(sm.settlements) >= 1
    first_st = next(iter(sm.settlements.values()))
    assert first_st.tier == 1
    assert "Campement" in first_st.tier_title

    # Upgrade
    first_st.tier = 3
    first_st.defense_bonus = 0.35
    assert "Village Palissadé" in first_st.tier_title


def test_universe_step_and_snapshot_with_m17_m18_m19():
    u = Universe("u-civ-full", 99)
    u.step(365)
    info = u.info()
    assert "active_disasters_count" in info
    assert "sacred_sites_count" in info
    assert "settlements_count" in info

    snap = u.snapshot()
    u2 = Universe.from_snapshot(snap)
    assert u2.info()["settlements_count"] == u.info()["settlements_count"]


def test_api_expansion_endpoints():
    client = TestClient(app)

    # 1. Disasters
    res_d = client.get("/universes/main/disasters")
    assert res_d.status_code == 200
    d_data = res_d.json()
    assert "active_disasters" in d_data
    assert "climate_cooling_offset" in d_data

    # 2. Pantheon
    res_p = client.get("/universes/main/pantheon")
    assert res_p.status_code == 200
    p_data = res_p.json()
    assert "deities" in p_data
    assert "sacred_sites" in p_data
    assert len(p_data["deities"]) >= 4

    # 3. Settlements
    res_s = client.get("/universes/main/settlements")
    assert res_s.status_code == 200
    s_data = res_s.json()
    assert isinstance(s_data, list)
    assert len(s_data) >= 1
    assert "tier" in s_data[0]
    assert "tier_title" in s_data[0]
