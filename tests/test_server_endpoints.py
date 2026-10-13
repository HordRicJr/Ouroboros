from fastapi.testclient import TestClient

from api.main import app


def test_api_health_endpoint():
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data.get("api") == "ok"
    assert data.get("status") == "ok"

def test_api_universes_endpoint():
    client = TestClient(app)
    res = client.get("/api/universes")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["id"] == "main"
