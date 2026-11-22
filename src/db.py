"""SQLite database: innovation records, full-text index, vector index and source status."""

import json
import sqlite3
from pathlib import Path

import sqlite_vec

from src.models import Innovation, SourceStatus

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cache" / "radar.db"
EMBEDDING_DIM = 768  # sdadas/mmlw-roberta-base

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS innovations (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    area TEXT,
    voivodeship TEXT,
    implementation_level INTEGER,
    potential INTEGER,
    updated TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_innovations_area ON innovations(area);
CREATE INDEX IF NOT EXISTS idx_innovations_voivodeship ON innovations(voivodeship);

-- The search module writes lemmatized text into this table.
CREATE VIRTUAL TABLE IF NOT EXISTS innovations_fts USING fts5(
    id UNINDEXED, title, summary, description, keywords,
    tokenize = 'unicode61 remove_diacritics 2'
);

CREATE VIRTUAL TABLE IF NOT EXISTS innovations_vec USING vec0(
    id TEXT PRIMARY KEY,
    embedding FLOAT[{EMBEDDING_DIM}] distance_metric=cosine
);

-- Notices of public purchases (BZP): demand signals. The search module writes lemmas into notices_fts.
CREATE TABLE IF NOT EXISTS notices (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    date TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS notices_fts USING fts5(
    id UNINDEXED, subject,
    tokenize = 'unicode61 remove_diacritics 2'
);

-- Anonymous usage counters (FAQ, section 7): no query text, no IP address, no user identifier.
CREATE TABLE IF NOT EXISTS usage (
    day TEXT NOT NULL,
    kind TEXT NOT NULL,
    value TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, kind, value)
);

CREATE TABLE IF NOT EXISTS sources (
    name TEXT PRIMARY KEY,
    records INTEGER NOT NULL DEFAULT 0,
    last_check TEXT,
    error TEXT
);
"""


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.executescript(SCHEMA)
    return conn


def upsert_innovation(conn: sqlite3.Connection, innovation: Innovation) -> None:
    conn.execute(
        """INSERT INTO innovations (id, data, area, voivodeship, implementation_level, potential)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET data = excluded.data, area = excluded.area,
               voivodeship = excluded.voivodeship,
               implementation_level = excluded.implementation_level,
               potential = excluded.potential, updated = datetime('now')""",
        (
            innovation.id,
            innovation.model_dump_json(),
            innovation.area.value,
            innovation.institution.voivodeship,
            innovation.implementation_level.value,
            innovation.assessment.potential,
        ),
    )


def get_innovation(conn: sqlite3.Connection, innovation_id: str) -> Innovation | None:
    row = conn.execute("SELECT data FROM innovations WHERE id = ?", (innovation_id,)).fetchone()
    return Innovation.model_validate(json.loads(row["data"])) if row else None


def set_source_status(conn: sqlite3.Connection, status: SourceStatus) -> None:
    conn.execute(
        """INSERT INTO sources (name, records, last_check, error) VALUES (?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET records = excluded.records,
               last_check = excluded.last_check, error = excluded.error""",
        (status.name, status.records, status.last_check.isoformat() if status.last_check else None, status.error),
    )


def list_sources(conn: sqlite3.Connection) -> list[SourceStatus]:
    rows = conn.execute("SELECT name, records, last_check, error FROM sources ORDER BY name").fetchall()
    return [SourceStatus(**dict(row)) for row in rows]


def delete_innovation(conn: sqlite3.Connection, innovation_id: str) -> None:
    for table in ("innovations", "innovations_fts", "innovations_vec"):
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (innovation_id,))


def all_innovations(conn: sqlite3.Connection) -> list[Innovation]:
    return [Innovation.model_validate(json.loads(r["data"])) for r in conn.execute("SELECT data FROM innovations ORDER BY id")]


def count_usage(conn: sqlite3.Connection, kind: str, value: str) -> None:
    conn.execute(
        """INSERT INTO usage (day, kind, value, count) VALUES (date('now'), ?, ?, 1)
           ON CONFLICT(day, kind, value) DO UPDATE SET count = count + 1""",
        (kind, value),
    )
    conn.commit()


def usage_stats(conn: sqlite3.Connection, days: int = 30, top: int = 10) -> dict[str, list[dict]]:
    rows = conn.execute(
        """SELECT kind, value, SUM(count) AS n FROM usage WHERE day >= date('now', ?)
           GROUP BY kind, value ORDER BY kind, n DESC""",
        (f"-{days} days",),
    ).fetchall()
    stats: dict[str, list[dict]] = {}
    for row in rows:
        items = stats.setdefault(row["kind"], [])
        if len(items) < top:
            items.append({"value": row["value"], "count": row["n"]})
    return stats
