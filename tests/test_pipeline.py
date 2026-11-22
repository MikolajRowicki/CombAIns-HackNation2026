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


def test_csv_export(db_path):
    with TestClient(app_module.app) as client:
        response = client.get("/api/export.csv", params={"q": "biszkopt"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        text = response.content.decode("utf-8-sig")
        header, first = text.splitlines()[:2]
        assert header.startswith("id;tytuł;obszar")
        assert "radon-" in first and "v0.1" in first and "https://radon.nauka.gov.pl" in first


def test_group_bonus_changes_the_order_only_a_little(db_path):
    conn = db.connect(db_path)
    plain = search.search(conn).results
    science = search.search(conn, group="science").results
    assert {r.id for r in plain} == {r.id for r in science}
    patent = next(r for r in plain if not r.id.startswith("radon-project-"))
    card = db.get_innovation(conn, patent.id)
    assert search.group_bonus("science", card) == search.GROUP_BONUS
    assert search.group_bonus(None, card) == 0
    for result in science:
        assert result.rank_score == pytest.approx(0.7 * result.relevance + 0.3 * (result.potential or 0) / 100, abs=1e-3)


def test_anonymous_usage_counters(db_path):
    with TestClient(app_module.app) as client:
        first = client.get("/api/search", params={"q": "Jan Kowalski", "area": "technological"}).json()["results"]
        client.get("/api/search", params={"area": "technological", "group": "investors"})
        client.get(f"/api/innovations/{first[0]['id']}") if first else None
        stats = client.get("/api/stats").json()["counters"]
    assert {"value": "technological", "count": 2} in stats["area"]
    assert stats["group"][0]["value"] == "investors"
    # The text of a query is never stored.
    assert "Kowalski" not in str(stats)
    conn = db.connect(db_path)
    assert "Kowalski" not in str([tuple(r) for r in conn.execute("SELECT * FROM usage")])
