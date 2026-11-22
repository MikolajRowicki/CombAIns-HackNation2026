import json
from datetime import date

import httpx

from src.criteria import assess
from src.sources import PageFetcher, kohesio


def detail(item, title, beneficiary, code, end, programme="2014PL16RFOP018 - Województwo podkarpackie – RPO"):
    return {
        "item": item,
        "label": title,
        "description": f"Projekt {title.lower()} uruchomił usługi elektroniczne dla mieszkańców gminy i urzędu.",
        "beneficiaries": [{"beneficiaryLabel": beneficiary}],
        "program": [{"programFullLabel": programme}],
        "categoryIDs": [code],
        "categoryLabels": ["Usługi i aplikacje w zakresie e-administracji"],
        "startTime": "2017-01-01",
        "endTime": end,
        "euBudget": "+1000000.00",
    }


DETAILS = {
    "Q1": detail("Q1", "Elektroniczny urząd w gminie Testowo", "GMINA TESTOWO", "078", "2020-12-31"),
    "Q2": detail("Q2", "Innowacyjna pracownia dla szkoły w gminie Testowo", "Gmina Testowo", "050", "2021-06-30"),
    "Q3": detail("Q3", "Aplikacja usług przyszłości", "Gmina Testowo", "078", "2099-12-31"),
    "Q5": detail("Q5", "Rozbudowa budynku przychodni", "Gmina Testowo", "053", "2020-12-31"),
    "Q4": detail("Q4", "Wdrożenie innowacyjnej technologii w firmie", "Jan Kowalski", "001", "2019-12-31"),
}


def test_finished_projects_without_persons(tmp_path, monkeypatch):
    monkeypatch.setattr(kohesio, "PHRASES", ("e-usługi",))
    monkeypatch.setattr("src.sources.MIN_PAUSE", 0)
    monkeypatch.setattr("src.sources.kohesio.PageFetcher", lambda client: PageFetcher(client, cache=tmp_path))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path.endswith("/projects"):
            return httpx.Response(200, json={"list": [{"item": i} for i in DETAILS]})
        item = request.url.params["id"].rsplit("/", 1)[-1]
        return httpx.Response(200, text=json.dumps(DETAILS[item]))

    data = kohesio.load(client=httpx.Client(transport=httpx.MockTransport(handler)))
    cards = {c.id: c for c in data.records}
    assert data.errors == []
    # Q3 is not finished. Q5 is construction only, not an innovation. Q4 has a natural person as the beneficiary: the name is hidden.
    assert set(cards) == {"kohesio-q1", "kohesio-q2", "kohesio-q4"}
    assert cards["kohesio-q1"].area.value == "administrative" and cards["kohesio-q1"].trl is None
    assert cards["kohesio-q1"].institution.name == "Gmina Testowo"
    assert cards["kohesio-q1"].institution.voivodeship == "podkarpackie"
    assert cards["kohesio-q2"].area.value == "educational"
    assert "Kowalski" not in cards["kohesio-q4"].model_dump_json()
    for card in cards.values():
        assert card.implementation_level.value == 4
        assert card.sources[0].license == kohesio.LICENSE
        assert card.assessment.model_dump() == assess(card.model_dump())
    assert cards["kohesio-q1"].timeline[0].date == date(2017, 1, 1)
