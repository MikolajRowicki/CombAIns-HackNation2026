import csv
import io
import os
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles

from src import db, search
from src.criteria import CONFIDENCE_THRESHOLDS, CRITERIA, CRITERIA_VERSION
from src.models import LABELS, InnovationDetail, SearchResponse, SourceStatus

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
DB_PATH = Path(os.environ.get("RADAR_DB", db.DB_PATH))

app = FastAPI(title="Radar innowacji")


def connection():
    return db.connect(DB_PATH)


@app.on_event("startup")
def warm_up() -> None:
    # The first lemma loads the Polish dictionary (a few seconds). Do it before the first search.
    search.lemmatize("innowacja")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/criteria")
def criteria() -> dict:
    """Return the assessment criteria, so that the card shows the names, scales, weights and references."""
    return {"version": CRITERIA_VERSION, "confidence_thresholds": CONFIDENCE_THRESHOLDS, "criteria": CRITERIA}


@app.get("/api/search", response_model=SearchResponse)
def search_innovations(
    q: str = "",
    area: str | None = None,
    voivodeship: str | None = None,
    level_min: int | None = Query(None, ge=1, le=5),
    group: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=search.MAX_CANDIDATES),
) -> SearchResponse:
    with closing(connection()) as conn:
        return search.search(conn, q, area, voivodeship, level_min, group, limit, offset=offset)


CSV_COLUMNS = [
    "id", "tytuł", "obszar", "instytucja", "rodzaj instytucji", "województwo", "poziom wdrożenia",
    "poziom wdrożenia: fakt czy szacunek", "TRL", "potencjał", "przedział od", "przedział do", "pewność",
    "wersja kryteriów", "źródła", "data sprawdzenia", "link do karty",
]


@app.get("/api/export.csv")
def export_csv(
    q: str = "",
    area: str | None = None,
    voivodeship: str | None = None,
    level_min: int | None = Query(None, ge=1, le=5),
    group: str | None = None,
    limit: int = Query(500, ge=1, le=search.MAX_CANDIDATES),
) -> Response:
    """Return the results of a search as CSV (UTF-8 with BOM, so that a spreadsheet shows Polish letters)."""
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(CSV_COLUMNS)
    with closing(connection()) as conn:
        for result in search.search(conn, q, area, voivodeship, level_min, group, limit).results:
            card = db.get_innovation(conn, result.id)
            a = card.assessment
            writer.writerow([
                card.id,
                card.title,
                LABELS["area"].get(card.area.value, card.area.value),
                card.institution.name,
                LABELS["institution_kind"].get(card.institution.kind, card.institution.kind),
                card.institution.voivodeship or "",
                card.implementation_level.value or "",
                LABELS["kind"].get(card.implementation_level.kind, ""),
                "nie dotyczy" if card.trl is None else (card.trl.value or "brak danych"),
                "" if a.potential is None else a.potential,
                a.low,
                a.high,
                LABELS["confidence"][a.confidence],
                a.criteria_version,
                " | ".join(s.url for s in card.sources),
                max(s.retrieved for s in card.sources).isoformat(),
                f"innovation.html?id={card.id}",
            ])
    return Response(
        "﻿" + out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="radar-innowacji.csv"'},
    )


@app.get("/api/innovations/{innovation_id}", response_model=InnovationDetail)
def innovation(innovation_id: str) -> InnovationDetail:
    with closing(connection()) as conn:
        record = db.get_innovation(conn, innovation_id)
        if record is None:
            raise HTTPException(404, "Nie znaleziono innowacji")
        return search.detail(conn, record)


@app.get("/api/sources", response_model=list[SourceStatus])
def sources() -> list[SourceStatus]:
    """Return the status of each source: number of records, date of the last check, last error."""
    with closing(connection()) as conn:
        return db.list_sources(conn)


# Mount the web page last, so that the /api routes have priority.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
