"""Update job: load each source, write the records and the full-text index, record the status of each source.

Start it from a scheduler (cron) for the regular update (FAQ, section 4):
    python -m src.pipeline update --voivodeship podkarpackie
"""

import argparse
import sqlite3
import time
from collections.abc import Callable
from datetime import date

from src import db, search
from src.models import SourceStatus
from src.sources import SourceData, bzp, competitions, fe_projects, radon

# Each source is one function. A new source is one more entry here.
SOURCES: dict[str, tuple[str, Callable[..., SourceData]]] = {
    "radon": (radon.NAME, lambda voivodeships: radon.load(voivodeships)),
    "fe": (fe_projects.NAME, lambda voivodeships: fe_projects.load(voivodeships)),
    "competitions": (competitions.NAME, lambda voivodeships: competitions.load(voivodeships)),
}


def store(conn: sqlite3.Connection, data: SourceData) -> None:
    for record in data.records:
        db.upsert_innovation(conn, record)
        search.index(conn, record)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update the database of Radar innowacji.")
    parser.add_argument("command", choices=["update"])
    parser.add_argument("--voivodeship", action="append", help="for example podkarpackie; default: all of Poland")
    parser.add_argument("--source", action="append", choices=[*SOURCES, "bzp"], help="default: all sources")
    args = parser.parse_args()
    update(db.connect(), args.voivodeship, args.source)
