from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.criteria import CONFIDENCE_THRESHOLDS, CRITERIA, CRITERIA_VERSION

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Radar innowacji")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/criteria")
def criteria() -> dict:
    """Return the assessment criteria, so that the card shows the names, scales, weights and references."""
    return {"version": CRITERIA_VERSION, "confidence_thresholds": CONFIDENCE_THRESHOLDS, "criteria": CRITERIA}


# Mount the web page last, so that the /api routes have priority.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
