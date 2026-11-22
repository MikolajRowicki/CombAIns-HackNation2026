import json
from datetime import date
from pathlib import Path

from src import db, pipeline, search
from src.criteria import assess
from src.models import Innovation

SAMPLES = {r["id"]: r for r in json.loads((Path(__file__).parent / "fixtures" / "sample_innovations.json").read_text(encoding="utf-8"))}


def variant(record_id: str, new_id: str, title: str, source_name: str, event_date: date) -> Innovation:
    data = json.loads(json.dumps(SAMPLES[record_id]))
    data["id"] = new_id
    data["title"] = title
    data["sources"][0]["name"] = source_name
    data["sources"][0]["url"] = f"https://example.org/{new_id}"
    data["timeline"] = [{"date": event_date.isoformat(), "event": "grant", "label": f"Grant {new_id}", "source_url": data["sources"][0]["url"]}]
    data["assessment"] = assess(data)
    return Innovation.model_validate(data)


def test_link_and_merge_records_of_different_sources():
    conn = db.connect(":memory:")
    base = "radon-241314"
    patent = variant(base, "a-patent", "Układ do symulacji intruzów w ruchu powietrznym", "Źródło A", date(2022, 9, 5))
    project = variant(base, "b-project", "Symulacja intruzów w ruchu powietrznym dla dronów", "Źródło B", date(2019, 1, 1))
    copy = variant(base, "c-copy", "Układ do symulacji intruzów w ruchu powietrznym", "Źródło C", date(2023, 1, 1))
    other = variant(base, "d-other", "Inny wynalazek bez związku", "Źródło B", date(2020, 1, 1))
    for record in (patent, project, copy, other):
        db.upsert_innovation(conn, record)
        search.index(conn, record)

    merged, linked = pipeline.link_records(conn)
    assert merged == 1 and linked >= 1
    ids = {r.id for r in db.all_innovations(conn)}
    assert len(ids) == 3 and "d-other" in ids

    kept = next(db.get_innovation(conn, i) for i in ("a-patent", "c-copy") if i in ids)
    names = {s.name for s in kept.sources}
    assert len(names) >= 2
    assert kept.credibility.value == 4 and kept.credibility.kind == "fact"
    assert [e.date for e in kept.timeline] == sorted(e.date for e in kept.timeline)
    assert kept.assessment.model_dump() == assess(kept.model_dump())

    # The step is idempotent: a second run adds nothing new.
    before = db.get_innovation(conn, kept.id).model_dump()
    pipeline.link_records(conn)
    assert db.get_innovation(conn, kept.id).model_dump() == before
    assert db.get_innovation(conn, "d-other").credibility.value == SAMPLES[base]["credibility"]["value"]
