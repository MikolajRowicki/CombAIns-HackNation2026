import json
from datetime import date, datetime
from pathlib import Path

import httpx
import openpyxl
import pytest

from src.criteria import assess
from src.models import Assessment
from src.sources import fe_projects as fe

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "fe_projects.json").read_text(encoding="utf-8"))
FIELDS = ["summary", "area", "type", "implementation_level", "trl", "novelty", "application_potential", "credibility"]
DATE_COLUMNS = (16, 17)


@pytest.fixture
def xlsx(tmp_path) -> Path:
    """Write the recorded rows as an XLSX file with the layout of the real file (title row, header row)."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    for row in FIXTURE["header"]:
        sheet.append(row)
    for row in FIXTURE["rows"]:
        sheet.append([datetime.fromisoformat(v) if i in DATE_COLUMNS and v else v for i, v in enumerate(row)])
    path = tmp_path / "fe_test.xlsx"
    workbook.save(path)
    return path


def by_title(records, start):
    return next(r for r in records if r.title.startswith(start))


def test_load_filters_by_signal_and_region(xlsx):
    data = fe.load(["podkarpackie"], path=xlsx)
    assert data.errors == []
    assert data.license == "CC0 1.0"
    assert any(r.title.startswith("e-Urząd w Gminie Krasiczyn") for r in data.records)
    # A project for the whole country serves all regions. A project in another voivodeship does not.
    assert any(r.institution.voivodeship is None for r in data.records)
    assert not any(r.institution.voivodeship == "mazowieckie" for r in data.records)
    # A project without an innovation signal (equipment of an office) is not a card.
    assert not any(r.institution.name == "Wojewoda Podkarpacki" for r in data.records)
    assert len(data.records) == 6
    assert len(fe.load(None, path=xlsx).records) == 7


def test_area_and_institution_rules(xlsx):
    records = fe.load(["podkarpackie"], path=xlsx).records
    office = by_title(records, "e-Urząd w Gminie Krasiczyn")
    assert office.area.value == "administrative" and office.area.kind == "estimate"
    assert (office.institution.kind, office.institution.city) == ("jst", "Krasiczyn")
    assert office.trl is None
    school = by_title(records, "Wydobyć sukces")
    assert school.area.value == "educational"
    lab = by_title(records, "Rozbudowa Laboratorium Wodorowego")
    assert lab.institution.kind == "university"
    assert lab.area.value == "technological" and lab.trl is not None and lab.trl.value is None


def test_level_comes_from_the_dates():
    row = {**dict(zip(fe.COLUMNS, [None] * len(fe.COLUMNS), strict=True))}
    row.update(title="Platforma e-usług", description="Projekt obejmuje uruchomienie platformy e-usług. " * 3)
    row.update(beneficiary="Gmina Przykładowa", category="016 Rozwiązania TIK", start=date(2024, 1, 1))
    page = "https://dane.gov.pl/pl/dataset/13939/resource/1"
    ended = fe.row_to_innovation({**row, "end": date(2025, 6, 30)}, page, None, date(2026, 11, 22))
    running = fe.row_to_innovation({**row, "end": date(2027, 6, 30)}, page, None, date(2026, 11, 22))
    future = fe.row_to_innovation({**row, "start": date(2027, 1, 1)}, page, None, date(2026, 11, 22))
    assert [r.implementation_level.value for r in (ended, running, future)] == [4, 2, 1]
    assert all(r.implementation_level.kind == "estimate" for r in (ended, running, future))
    assert [e.event for e in ended.timeline] == ["grant", "implementation"]


def test_natural_person_is_hidden(xlsx):
    record = by_title(fe.load(["podkarpackie"], path=xlsx).records, "Innowacyjna linia produkcyjna")
    assert record.institution.name == fe.HIDDEN_NAME
    assert "Testowy" not in json.dumps(record.model_dump(mode="json"), ensure_ascii=False)


def test_name_in_title_is_hidden_without_a_beneficiary():
    # Synthetic data: some rows have no beneficiary, but the title names the owner of the firm.
    row = dict.fromkeys(fe.COLUMNS)
    row.update(
        title="Zwiększenie konkurencyjności firmy ABC-BUD Adam Przykładowy",
        description="Firma ABC-BUD Adam Przykładowy wdroży nową linię. Szkoła im. Marii Konopnickiej jest partnerem. "
        * 2,
        category="027 Procesy innowacji w MŚP",
        start=date(2024, 1, 1),
    )
    record = fe.row_to_innovation(row, "https://dane.gov.pl/pl/dataset/13939/resource/1", None, date(2026, 11, 22))
    text = json.dumps(record.model_dump(mode="json"), ensure_ascii=False)
    assert "Przykładowy" not in text and "Adam" not in text
    assert "Konopnickiej" in text


@pytest.mark.parametrize(
    "beneficiary,name",
    [
        ("Politechnika Rzeszowska im. Ignacego Łukasiewicza", None),
        ("Szkoła Podstawowa im. Marii Konopnickiej", None),
        ("Uniwersytet Rzeszowski", None),
        ("Wojewoda Podkarpacki", None),
        ("Gmina Krasiczyn", None),
        ("P.P.H.U. Adam Przykładowy", "Adam Przykładowy"),
        ("JAN PRZYKŁADOWY", "JAN PRZYKŁADOWY"),
        ("Usługi Techniczne Anna Testowa", "Anna Testowa"),
    ],
)
def test_person_name(beneficiary, name):
    assert fe.person_name(beneficiary) == name


def test_quotes_and_repeatable_assessment(xlsx):
    for r in fe.load(None, path=xlsx).records:
        base = r.title + "\n" + r.description
        for name in FIELDS:
            field = getattr(r, name)
            if field is not None and field.evidence:
                assert field.evidence in base, (r.id, name)
            if field is not None and field.kind == "estimate":
                assert field.reason, (r.id, name)
        assert Assessment.model_validate(assess(r.model_dump())).model_dump() == r.assessment.model_dump()
        assert r.sources[0].license == "CC0 1.0"


def test_newest_resource_and_cached_file(tmp_path, monkeypatch):
    listing = {
        "data": [
            {"id": "99", "attributes": {"format": "csv", "data_date": "2026-11-02", "link": "x"}},
            {
                "id": "98",
                "attributes": {"format": "xlsx", "data_date": "2026-11-02", "link": "https://example.org/f.xlsx"},
            },
        ]
    }
    ok = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=listing)))
    resource = fe.newest_resource(ok)
    assert (resource["id"], resource["data_date"]) == ("98", date(2026, 11, 2))
    assert resource["page"].endswith("/dataset/13939/resource/98")

    # Without the API, the loader uses a file that a person put into data/cache/.
    monkeypatch.setattr(fe, "CACHE", tmp_path)
    (tmp_path / "fe_2912686.xlsx").write_bytes(b"")
    down = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503)))
    path, resource = fe.download(down)
    assert path.name == "fe_2912686.xlsx" and resource["id"] == "2912686"


def test_school_project_with_a_teaching_method_is_kept():
    from src.sources import fe_projects

    description = "Projekt wprowadzi zajęcia z robotyki i programowania dla uczniów szkół podstawowych w gminie."
    row = {
        "title": "Mała szkoła - wielkie możliwości",
        "description": description,
        "category": "149 Wsparcie na rzecz szkolnictwa podstawowego i średniego",
    }
    assert fe_projects.is_innovation(row)
    row["description"] = "Projekt sfinansuje remont sali gimnastycznej i zakup ławek dla uczniów szkoły w gminie."
    assert not fe_projects.is_innovation(row)
    row["category"] = "145 Wsparcie dla rozwoju umiejętności cyfrowych"
    row["description"] = description
    assert not fe_projects.is_innovation(row) or fe_projects.INNOVATION_CATEGORY.search(row["category"])
