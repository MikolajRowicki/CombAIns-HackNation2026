from datetime import date
from pathlib import Path

import httpx

from src.criteria import assess
from src.sources import PageFetcher, ncbr

FIXTURES = Path(__file__).parent / "fixtures"
LIST = (FIXTURES / "ncbr_list.html").read_text(encoding="utf-8")
DETAIL = (FIXTURES / "ncbr_detail.html").read_text(encoding="utf-8")


def load(tmp_path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text=LIST if "wyszukiwarka" in request.url.path else DETAIL)

    monkeypatch.setattr("src.sources.ncbr.PageFetcher", lambda client: PageFetcher(client, cache=tmp_path))
    monkeypatch.setattr("src.sources.MIN_PAUSE", 0)
    return ncbr.load(client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_cards_without_persons(tmp_path, monkeypatch):
    data = load(tmp_path, monkeypatch)
    assert data.errors == []
    cards = {r.title: r for r in data.records}
    # The third project has only a natural person as the beneficiary: no card.
    assert set(cards) == {"Czujnik odkształceń na bazie światłowodów", "Program nauczania dla szkół"}
    for card in cards.values():
        assert "Testow" not in card.model_dump_json().replace("Testowe", "").replace("Testowy w", "")


def test_fields_of_a_card(tmp_path, monkeypatch):
    cards = {r.title: r for r in load(tmp_path, monkeypatch).records}
    sensor = cards["Czujnik odkształceń na bazie światłowodów"]
    assert sensor.institution.name == "Polskie Centrum Testowe Sp. z o.o."
    assert sensor.institution.kind == "company"
    assert sensor.institution.voivodeship == "zachodniopomorskie"
    assert "lotniczym" in sensor.description and "rada" not in sensor.description
    assert sensor.keywords == ["Inżynieria materiałowa", "fotonika"]
    assert sensor.timeline[0].date == date(2016, 2, 1)
    assert sensor.area.value == "technological"
    assert sensor.assessment.model_dump() == assess(sensor.model_dump())

    school = cards["Program nauczania dla szkół"]
    assert school.area.value == "educational" and school.trl is None
    assert school.institution.name == "Uniwersytet Testowy w Rzeszowie"
    assert school.institution.voivodeship == "podkarpackie"
