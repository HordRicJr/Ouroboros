"""Tests pour M14 (Warfare), M15 (Chronicles) et M16 (Multiverse)."""
from fastapi.testclient import TestClient

from api.main import app
from engine.chronicles import ChronicleKeeper
from engine.ecology import Ecosystem
from engine.engine import Universe
from engine.multiverse import MultiverseRegistry
from engine.warfare import WarfareManager


def test_warfare_declaration_and_skirmish():
    # Créer un écosystème avec 2 campements pour avoir 2 clans belligérants
    u_tmp = Universe("test-war-u", seed=88)
    eco = Ecosystem.genesis(u_tmp.world, u_tmp.consts, u_tmp.rng, u_tmp.tick, initial_camps=2)
    u = Universe("test-war-u", seed=88, eco=eco)
    warfare: WarfareManager = u.warfare

    c_ids = list(u.society.clans.keys())
    assert len(c_ids) >= 2
    c1, c2 = c_ids[0], c_ids[1]

    # Déclaration de guerre
    war = warfare.declare_war(c1, c2, tick=u.tick, year=0, reason="Dispute territoriale")
    assert war.active is True
    assert warfare.is_at_war(c1, c2) is not None
    assert len(warfare.active_wars()) == 1

    # Step warfare
    evs = warfare.step(u.tick, 0, u.society, u.people, u.technology, u.world, u.rng)
    assert len(evs) > 0
    # Une escarmouche a eu lieu
    assert war.skirmishes_count >= 1


def test_chronicles_recording_and_tales():
    keeper = ChronicleKeeper()
    entry = keeper.record(
        tick=100,
        year=1,
        category="guerre",
        title="L'attaque des falaises",
        narrative="Un combat mémorable s'est déroulé sur les falaises.",
        clans=["Clan du Cerf", "Clan du Loup"],
    )
    assert entry.id == 1
    assert len(keeper.entries) == 1
    assert len(keeper.recent_tales(5)) == 1

    # Roundtrip serialization
    d = keeper.to_dict()
    keeper2 = ChronicleKeeper.from_dict(d)
    assert len(keeper2.entries) == 1
    assert keeper2.entries[0].title == "L'attaque des falaises"


def test_multiverse_spawn_and_lineage():
    multiverse = MultiverseRegistry()
    parent = Universe("parent-u", seed=42)
    multiverse.register(parent)

    child = multiverse.spawn_child(parent, "child-u", amplitude=0.1)
    assert child.parent_id == "parent-u"
    assert child.id == "child-u"
    assert child.consts.gravity != parent.consts.gravity or child.seed != parent.seed

    # Vérification de la lignée
    lineage = multiverse.get_lineage("child-u")
    assert lineage["universe"]["id"] == "child-u"
    assert len(lineage["ancestors"]) == 1
    assert lineage["ancestors"][0]["id"] == "parent-u"


def test_universe_step_and_snapshot_with_all_modules():
    u = Universe("full-save-u", seed=55)
    u.step(365)  # Une année complète
    info = u.info()
    assert "active_wars_count" in info
    assert "chronicles_count" in info

    snap = u.snapshot()
    u2 = Universe.from_snapshot(snap)
    assert u2.id == u.id
    assert u2.info()["chronicles_count"] == u.info()["chronicles_count"]


def test_api_advanced_endpoints():
    client = TestClient(app)

    # 1. Chronicles
    res_chronicles = client.get("/universes/main/chronicles")
    assert res_chronicles.status_code == 200
    assert isinstance(res_chronicles.json(), list)

    # 2. Wars
    res_wars = client.get("/universes/main/wars")
    assert res_wars.status_code == 200
    wars_data = res_wars.json()
    assert "active_wars" in wars_data
    assert "all_wars" in wars_data
    assert "peace_treaties" in wars_data

    # 3. Spawn child universe
    from api.main import store, universes
    universes.pop("child-test-01", None)
    if hasattr(store, "_conn"):
        with store._conn() as conn:
            conn.execute("DELETE FROM universes WHERE id='child-test-01'")
            conn.execute("DELETE FROM snapshots WHERE universe_id='child-test-01'")
    res_spawn = client.post("/universes/main/spawn", json={
        "child_id": "child-test-01",
        "amplitude": 0.05
    })
    assert res_spawn.status_code == 201
    spawn_data = res_spawn.json()
    assert spawn_data["parent_id"] == "main"
    assert spawn_data["child_id"] == "child-test-01"

    # 4. Multiverse Lineage
    res_lineage = client.get("/universes/child-test-01/lineage")
    assert res_lineage.status_code == 200
    lineage_data = res_lineage.json()
    assert lineage_data["universe"]["id"] == "child-test-01"
    assert len(lineage_data["ancestors"]) >= 1
    assert lineage_data["ancestors"][0]["id"] == "main"
