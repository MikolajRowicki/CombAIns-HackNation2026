import json
from datetime import date
from pathlib import Path

import pytest
import sqlite_vec

from src.criteria import assess
from src.db import (
    EMBEDDING_DIM,
    connect,
    get_innovation,
    list_sources,
    set_source_status,
    upsert_innovation,
)
from src.models import (
    LABELS,
    Assessment,
    Innovation,
    InnovationDetail,
    SearchResponse,
    SourceStatus,
)

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["summary", "area", "type", "implementation_level", "trl", "novelty", "application_potential", "credibility"]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def records() -> list[Innovation]:
    return [Innovation.model_validate(r) for r in load(ROOT / "tests" / "fixtures" / "sample_innovations.json")]


def test_sample_set_covers_areas_and_regions(records):
    assert 15 <= len(records) <= 20
    assert len({r.id for r in records}) == len(records)
    assert {r.area.value for r in records} == set(LABELS["area"])
    assert len({r.institution.voivodeship for r in records}) >= 5


def test_facts_quote_the_source_and_estimates_have_a_reason(records):
    for r in records:
        base = r.title + "\n" + r.description
        for name in FIELDS:
            field = getattr(r, name)
            if field is None:
                continue
            if field.evidence:
                assert field.evidence in base, (r.id, name)
            if field.kind == "estimate":
                assert field.reason, (r.id, name)


def test_codes_have_labels(records):
    for r in records:
        assert r.area.value in LABELS["area"]
        assert r.institution.kind in LABELS["institution_kind"]
        assert r.institution.voivodeship in LABELS["voivodeship"]
        assert str(r.implementation_level.value) in LABELS["implementation_level"]


def test_web_samples_follow_the_contract(records):
    search = SearchResponse.model_validate(load(ROOT / "web" / "sample" / "search.json"))
    for result in search.results:
        assert result.rank_score == pytest.approx(0.7 * result.relevance + 0.3 * result.potential / 100, abs=1e-3)
    detail = InnovationDetail.model_validate(load(ROOT / "web" / "sample" / "innovation.json"))
    assert detail.similar


def test_assessment_is_repeatable(records):
    # The same record and the same criteria version must give the same score (AGENTS.md, rule 7).
    for r in records:
        assert r.assessment.model_dump() == Assessment.model_validate(assess(r.model_dump())).model_dump(), r.id


def test_database_round_trip(records):
    conn = connect(":memory:")
    for r in records:
        upsert_innovation(conn, r)
    upsert_innovation(conn, records[0])
    assert conn.execute("SELECT count(*) FROM innovations").fetchone()[0] == len(records)
    assert get_innovation(conn, records[0].id) == records[0]
    assert get_innovation(conn, "missing") is None

    status = SourceStatus(name="RAD-on", records=5, last_check=date(2026, 11, 22), error=None)
    set_source_status(conn, status)
    assert list_sources(conn) == [status]

    conn.execute(
        "INSERT INTO innovations_vec (id, embedding) VALUES (?, ?)",
        (records[0].id, sqlite_vec.serialize_float32([0.1] * EMBEDDING_DIM)),
    )
    conn.execute("INSERT INTO innovations_fts (id, title) VALUES (?, ?)", (records[0].id, records[0].title))
    assert conn.execute("SELECT id FROM innovations_fts WHERE innovations_fts MATCH 'symulacji'").fetchone()[0] == records[0].id
