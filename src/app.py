from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Radar innowacji")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# Mount the web page last, so that the /api routes have priority.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
