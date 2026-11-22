import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from src.criteria import assess
from src.models import Institution
from src.sources import radon

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "radon_responses.json").read_text(encoding="utf-8"))
FIELDS = ["summary", "area", "type", "implementation_level", "trl", "novelty", "application_potential", "credibility"]


@pytest.fixture(autouse=True)
def no_pause(monkeypatch):
    monkeypatch.setattr(radon, "PAUSE", 0)


def client(fail: set[str] = frozenset()) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.rsplit("/", 1)[-1]
        if path in fail:
            return httpx.Response(503)
        return httpx.Response(200, json=FIXTURE[path])

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_load_returns_records_and_metadata():
    data = radon.load(["podkarpackie"], client=client())
    assert data.errors == []
    assert data.license == "CC0 1.0"
    assert data.data_date is not None
    patents = [r for r in data.records if not r.id.startswith("radon-project-")]
    projects = [r for r in data.records if r.id.startswith("radon-project-")]
    assert len(patents) == 3 and len(projects) == 4
    # Only active institutions: the liquidated school in the recorded response gives no records.
    assert {r.institution.name for r in data.records} == {"Państwowa Akademia Nauk Stosowanych w Krośnie"}
    assert {r.institution.voivodeship for r in data.records} == {"podkarpackie"}


def test_patent_card_follows_the_rules_of_the_issue():
    patent = next(r for r in radon.load(["podkarpackie"], client=client()).records if r.title.startswith("Uchwyt"))
    assert patent.area.value == "technological"
    assert (patent.implementation_level.value, patent.implementation_level.kind) == (2, "estimate")
    assert (patent.trl.value, patent.trl.kind) == (4, "estimate")
    assert patent.credibility.kind == "fact"
    assert patent.timeline and all(e.event == "patent" for e in patent.timeline)


def test_quotes_reasons_and_repeatable_assessment():
    for r in radon.load(["podkarpackie"], client=client()).records:
        base = r.title + "\n" + r.description
        for name in FIELDS:
            field = getattr(r, name)
            if field is None:
                continue
            if field.evidence:
                assert field.evidence in base, (r.id, name)
            if field.kind == "estimate":
                assert field.reason, (r.id, name)
        assert r.sources and r.sources[0].url.startswith(radon.BASE_URL)
        assert r.assessment.model_dump() == assess(r.model_dump()), r.id


def test_no_personal_data():
    raw = dict(FIXTURE["products"]["results"][0])
    raw["inventors"] = [{"persons": [{"firstName": "Jan", "lastName": "Testowyinwentor"}]}]
    institution = Institution(name="X", kind="university", voivodeship="podkarpackie")
    card = radon.patent_to_innovation(raw, institution, date(2026, 11, 22))
    assert "Testowyinwentor" not in card.model_dump_json()


def test_basic_research_projects_are_skipped():
    raw = {"receivedFunds": [{"financingInstitutionName": "Narodowe Centrum Nauki"}]}
    assert not radon.is_innovation_project(raw)
    raw["receivedFunds"].append({"financingInstitutionName": "Narodowe Centrum Badań i Rozwoju"})
    assert radon.is_innovation_project(raw)


def test_failed_source_part_does_not_stop_the_loader():
    data = radon.load(["podkarpackie"], client=client(fail={"products"}))
    assert len(data.errors) == 1 and data.errors[0].startswith("products")
    assert len(data.records) == 4
