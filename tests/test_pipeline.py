import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from src import app as app_module
from src import db, pipeline, search
from src.sources import radon

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "radon_responses.json").read_text(encoding="utf-8"))


def mock_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=FIXTURE[request.url.path.rsplit("/", 1)[-1]])

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setattr(radon, "PAUSE", 0)
    path = tmp_path / "radar.db"
    conn = db.connect(path)
    pipeline.store(conn, radon.load(["podkarpackie"], client=mock_client()))

    def failing(voivodeships):
        raise RuntimeError("source down")

    monkeypatch.setitem(pipeline.SOURCES, "broken", ("Źródło testowe", failing))
    pipeline.update(conn, sources=["broken"])
    conn.close()
    monkeypatch.setattr(app_module, "DB_PATH", path)
    return path


def test_search_finds_inflected_words(db_path):
    conn = db.connect(db_path)
    # The title has "śmigłowców"; the query has another form of the word.
    response = search.search(conn, "śmigłowiec")
    assert response.results and "śmigłowców" in response.results[0].title
    for result in response.results:
        assert result.rank_score == pytest.approx(0.7 * result.relevance + 0.3 * (result.potential or 0) / 100, abs=1e-3)


def test_filters_and_total(db_path):
    conn = db.connect(db_path)
    everything = search.search(conn)
    assert everything.total == 7
    assert search.search(conn, area="educational").total == 0
    assert search.search(conn, voivodeship="mazowieckie").total == 0
    assert all(r.implementation_level.value >= 2 for r in search.search(conn, level_min=2).results)


def test_api(db_path):
    with TestClient(app_module.app) as client:
        results = client.get("/api/search", params={"q": "biszkopt"}).json()["results"]
        assert results
        card = client.get(f"/api/innovations/{results[0]['id']}").json()
        assert card["sources"] and "similar" in card
        assert client.get("/api/innovations/brak").status_code == 404
        sources = {s["name"]: s for s in client.get("/api/sources").json()}
        assert sources["RAD-on (OPI PIB)"]["records"] == 7
        assert sources["Źródło testowe"]["error"] == "source down"
