from starlette.testclient import TestClient

from api.main import app
from engine.economy import EconomyManager
from engine.engine import Universe
from engine.erudition import EruditionManager
from engine.ouroboros_cycle import OuroborosCycleManager
from engine.realms import RealmManager


def test_final_civilization_cycle_and_snapshots():
    u = Universe("test_cycle_u", seed=42)
    assert isinstance(u.economy, EconomyManager)
    assert isinstance(u.realms, RealmManager)
    assert isinstance(u.erudition, EruditionManager)
    assert isinstance(u.ouroboros, OuroborosCycleManager)

    # Step simulation by 30 days
    u.step(30)
    info = u.info()
    assert "currencies_count" in info
    assert "kingdoms_count" in info
    assert "wonders_count" in info
    assert "civilization_phase" in info
    assert "ouroboros_cycle" in info

    # Persistence snapshot
    snap = u.snapshot()
    restored = Universe.from_snapshot(snap)
    assert isinstance(restored.economy, EconomyManager)
    assert isinstance(restored.realms, RealmManager)
    assert isinstance(restored.erudition, EruditionManager)
    assert isinstance(restored.ouroboros, OuroborosCycleManager)
    assert restored.ouroboros.cycle.cycle_number == u.ouroboros.cycle.cycle_number


def test_final_civilization_api_endpoints():
    client = TestClient(app)

    # Step main universe
    client.post("/universes/main/step", json={"days": 10})

    # Economy
    res_econ = client.get("/universes/main/economy")
    assert res_econ.status_code == 200
    assert "currencies" in res_econ.json()

    # Realms
    res_realm = client.get("/universes/main/realms")
    assert res_realm.status_code == 200
    assert isinstance(res_realm.json(), list)

    # Erudition
    res_erud = client.get("/universes/main/erudition")
    assert res_erud.status_code == 200
    assert "wonders" in res_erud.json()

    # Ouroboros Cycle
    res_cycle = client.get("/universes/main/cycle")
    assert res_cycle.status_code == 200
    assert "current_phase" in res_cycle.json()
    assert "cycle_number" in res_cycle.json()
