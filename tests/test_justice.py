from starlette.testclient import TestClient

from api.main import app
from engine.engine import Universe
from engine.justice import JusticeSystem


def test_justice_system_laws_and_ranks():
    u = Universe("test_justice", seed=42)
    assert isinstance(u.justice, JusticeSystem)
    # Plus de grades assignés à la genèse (émergence)
    assert isinstance(u.justice.person_ranks, dict)

    # Step universe across 30 days
    u.step(30)
    info = u.info()
    assert "legal_codes_count" in info
    assert "trials_count" in info

    # Serialization test
    snap = u.snapshot()
    restored = Universe.from_snapshot(snap)
    assert isinstance(restored.justice, JusticeSystem)
    assert len(restored.justice.legal_codes) == len(u.justice.legal_codes)


def test_justice_api_endpoint():
    client = TestClient(app)

    # Step main universe by 365 days to ensure year transitions and justice progression
    client.post("/universes/main/step", json={"days": 365})

    # Get justice endpoint
    res_j = client.get("/universes/main/justice")
    assert res_j.status_code == 200
    data = res_j.json()
    assert "legal_codes" in data
    assert "trials" in data
    assert "person_ranks" in data
    assert isinstance(data["person_ranks"], dict)
