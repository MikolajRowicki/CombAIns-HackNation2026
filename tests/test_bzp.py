import json
from pathlib import Path

import httpx
import pytest

from src import db, search
from src.models import Innovation
from src.sources import bzp

TESTS = Path(__file__).parent
NOTICES = json.loads((TESTS / "fixtures" / "bzp_notices.json").read_text(encoding="utf-8"))
SAMPLES = {r["id"]: r for r in json.loads((TESTS / "fixtures" / "sample_innovations.json").read_text(encoding="utf-8"))}


@pytest.fixture(autouse=True)
def no_pause(monkeypatch):
    monkeypatch.setattr(bzp, "PAUSE", 0)


def client(fail: bool = False) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if fail:
            return httpx.Response(403, text="Dostęp zablokowany")
        return httpx.Response(200, json=NOTICES)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_load_keeps_institutions_and_no_contractors():
    data = bzp.load(cpv_groups=["72000000"], client=client())
    assert data["errors"] == [] and len(data["notices"]) == len(NOTICES)
    notice = data["notices"][0]
    assert set(notice) == {"id", "number", "date", "subject", "cpv", "buyer", "city", "voivodeship", "url"}
    assert {n["voivodeship"] for n in data["notices"]} >= {"mazowieckie", "lubelskie"}
    assert notice["url"].startswith("https://ezamowienia.gov.pl/")


def test_blocked_api_gives_an_error_not_an_exception():
    data = bzp.load(cpv_groups=["72000000"], client=client(fail=True))
    assert data["notices"] == [] and data["errors"]


def test_demand_matches_rare_common_words(monkeypatch):
    # The fixture has only 5 notices, so the IDF weights are small. A lower threshold checks the mechanism.
    monkeypatch.setattr(search, "MIN_DEMAND_SCORE", 2.0)
    conn = db.connect(":memory:")
    for notice in bzp.load(cpv_groups=["72000000"], client=client())["notices"]:
        search.index_notice(conn, notice)

    record = dict(SAMPLES["insam7-zawoja-wirtualny-urzednik"])
    record["title"] = "Cyberbezpieczne wodociągi gminne"
    signals = search.demand(conn, Innovation.model_validate(record))
    assert signals and "MIĘDZYRZEC" in signals[0].buyer
    assert "wodociąg" in signals[0].reason

    record["title"] = "Trenażer zabiegu chirurgii"
    record["summary"] = {**record["summary"], "value": "Model do nauki zabiegu."}
    assert search.demand(conn, Innovation.model_validate(record)) == []
