from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Radar innowacji" in response.text


def test_criteria():
    response = client.get("/api/criteria")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "v0.1"
    assert set(data["criteria"]) == {"K1", "K2", "K3", "K4", "K5"}
    assert data["criteria"]["K1"]["scale"]["5"] == "Stosowane w praktyce"
