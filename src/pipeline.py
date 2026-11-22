"""Update job: load each source, write the records and the full-text index, record the status of each source.

Start it from a scheduler (cron) for the regular update (FAQ, section 4):
    python -m src.pipeline update --voivodeship podkarpackie
"""

import argparse
import re
import sqlite3
import time
import unicodedata
from collections.abc import Callable
from datetime import date

import httpx

from src import applications, db, search
from src.criteria import assess, estimate_application_potential
from src.models import FieldValue, Innovation, SourceStatus
from src.sources import (
    SourceData,
    bzp,
    competitions,
    epo,
    fe_projects,
    interreg,
    kohesio,
    ncbr,
    radon,
)

# Each source is one function. A new source is one more entry here.
SOURCES: dict[str, tuple[str, Callable[..., SourceData]]] = {
    "radon": (radon.NAME, lambda voivodeships: radon.load(voivodeships)),
    "fe": (fe_projects.NAME, lambda voivodeships: fe_projects.load(voivodeships)),
    "competitions": (competitions.NAME, lambda voivodeships: competitions.load(voivodeships)),
    "ncbr": (ncbr.NAME, lambda voivodeships: ncbr.load(voivodeships)),
    "interreg": (interreg.NAME, lambda voivodeships: interreg.load(voivodeships)),
    "kohesio": (kohesio.NAME, lambda voivodeships: kohesio.load(voivodeships)),
    "epo": (epo.NAME, lambda voivodeships: epo.load(voivodeships)),
}


def store(conn: sqlite3.Connection, data: SourceData) -> None:
    for record in data.records:
        db.upsert_innovation(conn, record)
        search.index(conn, record)
    # A record that the source does not give any more (for example after a change of a filter) goes out.
    # If the source gave no records (an error), the old records stay.
    if data.records:
        new = {r.id for r in data.records}
        for record in db.all_innovations(conn):
            if record.sources[0].name == data.name and record.id not in new:
                db.delete_innovation(conn, record.id)
    db.set_source_status(
        conn,
        SourceStatus(
            name=data.name,
            records=len(data.records),
            last_check=data.retrieved,
            error="; ".join(data.errors[:3]) or None,
        ),
    )
    conn.commit()


def update_demand(conn: sqlite3.Connection) -> None:
    """Load the BZP notices for the demand signals. The card matches them when a user opens it."""
    start = time.monotonic()
    try:
        data = bzp.load()
    except Exception as error:  # noqa: BLE001 - a failed source must not stop the update
        data = {"notices": [], "errors": [str(error)], "retrieved": date.today()}
    for notice in data["notices"]:
        search.index_notice(conn, notice)
    db.set_source_status(
        conn,
        SourceStatus(
            name=bzp.NAME,
            records=len(data["notices"]),
            last_check=data["retrieved"],
            error="; ".join(data["errors"][:3]) or None,
        ),
    )
    conn.commit()
    print(f"bzp: {len(data['notices'])} notices, {len(data['errors'])} errors, {time.monotonic() - start:.0f} s")


# Two records of different sources describe the same innovation if the institution is the same and the titles
# share enough words (Jaccard index of lemmas). Above MERGE_SIMILARITY the records are one project: one card.
LINK_SIMILARITY = 0.33
MERGE_SIMILARITY = 0.9
_INSTITUTION_WORDS = re.compile(
    r"\b(?:gmina|miasto|powiat|województwo|urząd|im|w|z|siedzibą|sp|o|spółka|ograniczoną|odpowiedzialnością|s\.a)\b"
)


def _institution_key(name: str) -> str:
    return " ".join(re.findall(r"\w+", _INSTITUTION_WORDS.sub(" ", name.lower())))


def _title_lemmas(title: str) -> set[str]:
    return {search._lemma(t) for t in search.tokens(title)} - search._GENERIC


def _join(target: Innovation, other: Innovation) -> Innovation:
    """Add the sources and the timeline of another record. Two sources raise K5 (credibility) to 4."""
    urls = {s.url for s in target.sources}
    sources = [*target.sources, *(s for s in other.sources if s.url not in urls)]
    events = {(e.date, e.label) for e in target.timeline}
    timeline = sorted([*target.timeline, *(e for e in other.timeline if (e.date, e.label) not in events)], key=lambda e: e.date)
    data = target.model_dump()
    data["sources"] = [s.model_dump() for s in sources]
    data["timeline"] = [e.model_dump() for e in timeline]
    names = {s.name for s in sources}
    if len(names) >= 2 and (target.credibility.value or 0) < 4:
        data["credibility"] = FieldValue(
            value=4, kind="fact", source_url=other.sources[0].url,
            reason=None,
        ).model_dump()
    data["assessment"] = assess(data)
    return Innovation.model_validate(data)


def link_records(conn: sqlite3.Connection) -> tuple[int, int]:
    """Join records of different sources about the same innovation (docs/project.md, section 8: signal timeline).

    The result does not depend on the order of the updates: the step reads all records and sorts them by id.
    """
    records = db.all_innovations(conn)
    groups: dict[str, list[Innovation]] = {}
    for record in records:
        groups.setdefault(_institution_key(record.institution.name), []).append(record)
    merged = linked = 0
    removed: set[str] = set()
    for group in groups.values():
        if len({r.sources[0].name for r in group}) < 2:
            continue
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if a.id in removed or b.id in removed or a.sources[0].name == b.sources[0].name:
                    continue
                la, lb = _title_lemmas(a.title), _title_lemmas(b.title)
                if not la or not lb:
                    continue
                similarity = len(la & lb) / len(la | lb)
                if similarity < LINK_SIMILARITY:
                    continue
                a2, b2 = db.get_innovation(conn, a.id), db.get_innovation(conn, b.id)
                if similarity >= MERGE_SIMILARITY:
                    # Keep the record with the longer description; the other becomes a source of it.
                    keep, drop = (a2, b2) if len(a2.description) >= len(b2.description) else (b2, a2)
                    db.upsert_innovation(conn, _join(keep, drop))
                    db.delete_innovation(conn, drop.id)
                    removed.add(drop.id)
                    merged += 1
                else:
                    db.upsert_innovation(conn, _join(a2, b2))
                    db.upsert_innovation(conn, _join(b2, a2))
                    linked += 1
    conn.commit()
    return merged, linked


_COST = re.compile(r"\d[\d\s,.]*\s*(?:zł|mln zł|EUR)", re.IGNORECASE)


def application_checks(conn: sqlite3.Connection, record: Innovation) -> dict[int, str | None]:
    """Check the items of K4 with the data of the card (the order of CRITERIA["K4"]["items"])."""
    patent = re.search(r"patent|wzór użytkowy|prawo ochronne", str(record.type.value or ""), re.IGNORECASE)
    cost = next((e.label for e in record.timeline if _COST.search(e.label)), None)
    sectors = [s.label for s in applications.find_sectors(record)]
    demand = search.demand(conn, record)
    return {
        0: "opublikowany opis patentowy" if patent else None,
        1: f"wartość projektu w źródle: {_COST.search(cost).group().strip()}" if cost else None,
        3: f"sektory: {', '.join(sectors)}" if len(sectors) >= 2 else None,
        4: f"{len(demand)} zamówień o podobnym przedmiocie w BZP" if demand else None,
    }


def estimate_application_potential_all(conn: sqlite3.Connection) -> int:
    """Propose K4 for each card without a K4 value from the source. Then calculate the assessment again."""
    changed = 0
    for record in db.all_innovations(conn):
        if record.application_potential.kind == "fact" and record.application_potential.value is not None:
            continue
        data = record.model_dump()
        url = record.sources[0].url
        data["application_potential"] = estimate_application_potential(application_checks(conn, record), url)
        data["assessment"] = assess(data)
        db.upsert_innovation(conn, Innovation.model_validate(data))
        changed += 1
    conn.commit()
    return changed


def _name_key(name: str) -> str:
    """Compare names without Polish letters, case and punctuation ("Politechnika Gdanska" = "Politechnika Gdańska")."""
    text = unicodedata.normalize("NFKD", name.lower().replace("ł", "l"))
    return " ".join(re.findall(r"[a-z0-9]+", text.encode("ascii", "ignore").decode()))


def add_institution_contacts(conn: sqlite3.Connection) -> int:
    """Add the official web page and the general e-mail of science units (RAD-on) to cards of all sources."""
    try:
        with httpx.Client(timeout=60, headers={"User-Agent": "RadarInnowacji/0.1"}) as client:
            units = radon.fetch_institutions(client)
    except httpx.HTTPError as error:
        print(f"contacts: ERROR {error}")
        return 0
    full = {_name_key(u.name): u for u in units if u.website or u.email}
    # A short name without the patron ("Politechnika Rzeszowska" for "... im. Ignacego Łukasiewicza") must be unique.
    short: dict[str, list] = {}
    for key, unit in full.items():
        short.setdefault(key.split(" im ")[0], []).append(unit)
    changed = 0
    for record in db.all_innovations(conn):
        key = _name_key(record.institution.name)
        candidates = short.get(key, [])
        unit = full.get(key) or (candidates[0] if len(candidates) == 1 else None)
        if unit is None or (record.institution.website, record.institution.email) == (unit.website, unit.email):
            continue
        data = record.model_dump()
        data["institution"]["website"] = unit.website
        data["institution"]["email"] = unit.email
        db.upsert_innovation(conn, Innovation.model_validate(data))
        changed += 1
    conn.commit()
    return changed


def update(conn: sqlite3.Connection, voivodeships: list[str] | None = None, sources: list[str] | None = None) -> None:
    """Load the sources one by one. If a source fails, record the error and continue (AGENTS.md, rule 14)."""
    for name in sources or [*SOURCES, "bzp"]:
        if name == "bzp":
            update_demand(conn)
            continue
        label, load = SOURCES[name]
        start = time.monotonic()
        try:
            data = load(voivodeships)
        except Exception as error:  # noqa: BLE001 - one failed source must not stop the update
            db.set_source_status(conn, SourceStatus(name=label, records=0, last_check=date.today(), error=str(error)))
            conn.commit()
            print(f"{name}: ERROR {error}")
            continue
        store(conn, data)
        print(f"{name}: {len(data.records)} records, {len(data.errors)} errors, {time.monotonic() - start:.0f} s")
    merged, linked = link_records(conn)
    print(f"link: {merged} merged, {linked} linked")
    print(f"contacts: {add_institution_contacts(conn)} cards")
    print(f"K4: {estimate_application_potential_all(conn)} cards")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update the database of Radar innowacji.")
    parser.add_argument("command", choices=["update"])
    parser.add_argument("--voivodeship", action="append", help="for example podkarpackie; default: all of Poland")
    parser.add_argument("--source", action="append", choices=[*SOURCES, "bzp"], help="default: all sources")
    args = parser.parse_args()
    update(db.connect(), args.voivodeship, args.source)
