from fastapi.testclient import TestClient
import pytest

from api.main import app, universes, store


@pytest.fixture(autouse=True)
def clean_registry():
    universes.clear()
    store.delete("test-api")
    yield
    universes.clear()
    store.delete("test-api")


def test_api_crud_and_steps():
    client = TestClient(app)

    # 1. Créer un univers
    res = client.post("/universes", json={"id": "test-api", "seed": 42})
    assert res.status_code == 201
    assert res.json()["info"]["id"] == "test-api"

    # 2. Lire les infos
    res = client.get("/universes/test-api")
    assert res.status_code == 200
    assert res.json()["tick"] == 0

    # 3. Avancer le temps de 10 jours
    res = client.post("/universes/test-api/step", json={"days": 10})
    assert res.status_code == 200
    assert res.json()["tick"] == 10

    # 4. Carte du monde
    res = client.get("/universes/test-api/map")
    assert res.status_code == 200
    assert "land_fraction" in res.json()

    # 5. Notables
    res = client.get("/universes/test-api/notables")
    assert res.status_code == 200
    notables = res.json()
    assert len(notables) > 0

    first_notable_id = notables[0]["id"]

    # 6. Dialoguer avec le notable
    res = client.post(f"/universes/test-api/notables/{first_notable_id}/ask", json={
        "question": "Que ressens-tu face à ce monde ?",
        "mock": True
    })
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert data["ai_budget"]["total_calls"] == 1

    # 7. Généalogie
    res = client.get(f"/universes/test-api/genealogy/{first_notable_id}")
    assert res.status_code == 200
    assert "ancestors" in res.json()
