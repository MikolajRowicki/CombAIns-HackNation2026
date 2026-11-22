from datetime import date
from pathlib import Path

import httpx
import pytest

from src.criteria import assess
from src.sources import PageFetcher, competitions

HTML = (Path(__file__).parent / "fixtures" / "competition_page.html").read_text(encoding="utf-8")
URL = "https://example.org/laureaci"


@pytest.fixture(scope="module")
def records():
    return {r.title: r for r in competitions.parse_innowacyjny_samorzad(HTML, URL, date(2026, 11, 22))}


def test_one_card_for_each_laureate(records):
    names = {r.institution.name for r in records.values()}
    assert names >= {
        "Województwo podkarpackie",
        "Powiat ostrowiecki",
        "Zawoja",
        "Gmina Hażlach",
        "Gmina Murów",
    }
    assert records["Regionalny Model Ruchu dla Województwa Podkarpackiego"].institution.voivodeship == "podkarpackie"


def test_award_date_and_label(records):
    card = records["Wirtualny Urzędnik"]
    assert card.timeline[0].date == date(2026, 5, 29)
    assert card.timeline[0].label.startswith("Nagroda")
    assert records["Centrum Usług Publicznych w Murowie"].timeline[0].label.startswith("Wyróżnienie")


def test_facts_quote_the_source(records):
    for card in records.values():
        base = card.title + "\n" + card.description
        for field in (card.summary, card.implementation_level, card.credibility):
            if field.evidence:
                assert field.evidence in base
        assert card.implementation_level.kind == "fact" and card.implementation_level.value == 5
        assert card.area.value == "administrative" and card.trl is None
        assert card.assessment.model_dump() == assess(card.model_dump())


def test_no_names_of_persons(records):
    for card in records.values():
        assert "Testowy" not in card.model_dump_json()


def test_robots_txt_is_obeyed(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /laureaci\n")
        return httpx.Response(200, text=HTML)

    fetcher = PageFetcher(httpx.Client(transport=httpx.MockTransport(handler)), cache=tmp_path)
    with pytest.raises(PermissionError):
        fetcher.get(URL)


def test_old_pages_are_deleted(tmp_path):
    import os
    import time

    old = tmp_path / "old.html"
    old.write_text("x", encoding="utf-8")
    ten_days = time.time() - 10 * 24 * 3600
    os.utime(old, (ten_days, ten_days))
    fresh = tmp_path / "fresh.html"
    fresh.write_text("y", encoding="utf-8")
    PageFetcher(httpx.Client(), cache=tmp_path)
    assert not old.exists() and fresh.exists()
