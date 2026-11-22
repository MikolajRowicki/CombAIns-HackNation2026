import json
import time
from pathlib import Path

import httpx
import pytest

from src import db, pipeline, search
from src.applications import APPLICATIONS_VERSION, recommend
from src.criteria import CRITERIA_VERSION
from src.models import Innovation
from src.sources import radon

TESTS = Path(__file__).parent
CASES = json.loads((TESTS / "cases.json").read_text(encoding="utf-8"))
FIXTURE = json.loads((TESTS / "fixtures" / "radon_responses.json").read_text(encoding="utf-8"))


def radon_records() -> dict[str, Innovation]:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=FIXTURE[request.url.path.rsplit("/", 1)[-1]])

    data = radon.load(["podkarpackie"], client=httpx.Client(transport=httpx.MockTransport(handler)))
    return {r.id: r for r in data.records}


def sample_records() -> dict[str, Innovation]:
    rows = json.loads((TESTS / "fixtures" / "sample_innovations.json").read_text(encoding="utf-8"))
    return {r["id"]: Innovation.model_validate(r) for r in rows}


@pytest.fixture(scope="module")
def records():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(radon, "PAUSE", 0)
        return {"radon_fixture": radon_records(), "sample": sample_records()}


def check_trl(innovation: Innovation, expected: str | int) -> None:
    if expected == "not_applicable":
        assert innovation.trl is None
    elif expected == "missing":
        assert innovation.trl is not None and innovation.trl.value is None
    elif expected == "present":
        assert innovation.trl is not None and innovation.trl.value is not None
    else:
        assert innovation.trl.value == expected


def test_versions_match_the_cases():
    assert CASES["criteria_version"] == CRITERIA_VERSION
    assert CASES["applications_version"] == APPLICATIONS_VERSION


@pytest.mark.parametrize("case", CASES["cases"], ids=[c["id"] for c in CASES["cases"]])
def test_case(case, records):
    innovation = records[case["data"]][case["id"]]
    expected = case["expected"]
    assert innovation.area.value == expected["area"]
    assert innovation.implementation_level.value == expected["implementation_level"]
    check_trl(innovation, expected["trl"])
    assert innovation.institution.voivodeship == expected["voivodeship"]
    low, high = expected["potential"]
    assert low <= innovation.assessment.potential <= high
    if "confidence" in expected:
        assert innovation.assessment.confidence == expected["confidence"]

    applications = recommend(innovation, [])
    sectors = {s.label for s in applications.sectors}
    assert set(expected["sectors_include"]) <= sectors
    paths = {p.id for p in applications.paths}
    assert set(expected["paths_include"]) <= paths
    for sector in applications.sectors:
        assert sector.evidence in f"{innovation.title}\n{innovation.description}"
    for path in applications.paths:
        assert path.reason and path.measures and path.reference


@pytest.mark.slow
@pytest.mark.parametrize("demo", CASES["demo"], ids=[d["id"] for d in CASES["demo"]])
def test_demo_with_the_network(demo, tmp_path):
    """Full process with the network: source, record, assessment, index, search, card (task section 6)."""
    if demo["source"] not in pipeline.SOURCES:
        pytest.skip(f"source {demo['source']} is not in the pipeline yet")
    conn = db.connect(tmp_path / "radar.db")
    start = time.monotonic()
    pipeline.update(conn, [demo["voivodeship"]], [demo["source"]])
    load_seconds = time.monotonic() - start

    expected = demo["expected"]
    response = search.search(conn, demo["query"], area=expected["area"], voivodeship=expected["voivodeship"])
    assert response.total >= expected["min_results"]
    card = search.detail(conn, db.get_innovation(conn, response.results[0].id))
    assert card.sources and card.assessment.criteria_version == CRITERIA_VERSION
    check_trl(card, expected["trl"])
    assert {p.id for p in card.applications.paths} & set(expected["paths_include"])
    print(f"{demo['id']}: load {load_seconds:.0f} s, card: {card.title}")


@pytest.mark.slow
def test_new_card_in_30_seconds():
    """AGENTS.md, rule 13: the card of a new innovation in 30 seconds or less."""
    start = time.monotonic()
    data = radon.load(["podkarpackie"], limit_per_institution=1, include_projects=False)
    assert data.records, data.errors
    card = data.records[0]
    assert card.sources and card.assessment
    assert time.monotonic() - start <= 30


def test_contacts_are_institutions_or_links(records):
    from src.applications import find_contacts

    card = records["sample"]["web-mobilny-urzednik-rzeszow"]
    links, note = find_contacts(card)
    assert {link.kind for link in links} <= {"institution", "source", "search"}
    assert any(link.kind == "source" for link in links)
    assert any("BIP" in link.label for link in links)
    assert note
