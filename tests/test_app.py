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
