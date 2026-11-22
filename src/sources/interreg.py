"""Interreg 2021-2027 projects managed by Poland (dane.gov.pl, dataset 15971, CC0 1.0).

The file has the same fields as the list of FE projects (art. 49 CPR), so the loader uses the rules of
src/sources/fe_projects.py: the same innovation filter, the same areas and levels, and the same removal of persons.
A project is cross-border, so the lead partner can be in another country. Then the card has no voivodeship.
"""

import re
from datetime import date
from pathlib import Path

import httpx
import openpyxl

from src.models import FieldValue, Innovation, Source
from src.sources import SourceData, fe_projects

DATASET_ID = 15971
API = "https://api.dane.gov.pl/1.4"
NAME = "Interreg 2021-2027 (dane.gov.pl)"
LICENSE = "CC0 1.0"
CACHE = Path(__file__).resolve().parents[2] / "data" / "cache"
HEADER_ROW = 3  # rows 1-2 have the title of the sheet
# Interreg uses other categories of intervention than the FE list (for example crisis management or climate).
# A project is kept also if its text describes a solution: a system, a platform, a method or a technology.
SOLUTION = re.compile(
    r"innowac|cyfrow|platform|aplikac|narzędzi|e-usług|technolog|wdroż|model\w* (?:współpracy|zarządzania)"
    r"|system\w* (?:informac|monitor|wczesnego)|metod",
    re.IGNORECASE,
)

COLUMNS = {
    "programme": "Program",
    "contract": "Numer projektu",
    "title": "Tytul projektu",
    "description": "Opis projektu",
    "start": "Data rozpoczęcia",
    "end": "Data zakończenia",
    "eu": "Wydatki",
    "beneficiary": "Nazwa partnera wiodącego/",
    "country": "Kraj",
    "voivodeship": "Województwo",
    "poviat": "Powiat",
    "commune": "Gmina",
    "partners": "Nazwa partnera wiodącego i partnerów",
    "category": "Zakres interwencji",
}


def read_rows(path: Path) -> list[dict]:
    sheet = openpyxl.load_workbook(path, read_only=True).worksheets[0]
    rows = sheet.iter_rows(min_row=HEADER_ROW, values_only=True)
    header = [str(h or "") for h in next(rows)]
    index = {key: next(i for i, h in enumerate(header) if h.startswith(prefix)) for key, prefix in COLUMNS.items()}
    out = []
    for values in rows:
        row = {key: values[i] for key, i in index.items()}
        if not row["title"]:
            continue
        # The format of the location is the format of the FE list, so that fe_projects can read it.
        if str(row.get("country") or "").strip().lower() == "polska" and row.get("voivodeship"):
            row["location"] = f"WOJ.: {row['voivodeship']}, POW.: {row.get('poviat') or ''}, GM.: {row.get('commune') or ''}"
        else:
            row["location"] = ""
        out.append(row)
    return out


def to_innovation(row: dict, url: str, data_date: date | None, retrieved: date) -> Innovation:
    card = fe_projects.row_to_innovation(row, url, data_date, retrieved, foreign=True)
    data = card.model_dump()
    programme = str(row.get("programme") or "").split("/")[0].strip()
    data["id"] = "interreg-" + card.id.removeprefix("fe-")
    data["sources"] = [Source(name=NAME, url=url, data_date=data_date, retrieved=retrieved, license=LICENSE).model_dump()]
    data["type"] = FieldValue(value=f"projekt transgraniczny: {programme}", kind="fact", source_url=url).model_dump()
    partners = str(row.get("partners") or "")
    if partners:
        data["keywords"] = [*card.keywords, f"partnerów: {len(re.split(r'\s*\|\s*', partners))}"]
    return Innovation.model_validate(data)


def _resource(client: httpx.Client) -> dict:
    response = client.get(f"{API}/datasets/{DATASET_ID}/resources", params={"sort": "-data_date", "per_page": 5})
    response.raise_for_status()
    for item in response.json()["data"]:
        attributes = item["attributes"]
        if attributes.get("format") == "xlsx":
            return {
                "id": item["id"],
                "file_url": attributes["file_url"],
                "data_date": date.fromisoformat(attributes["data_date"]) if attributes.get("data_date") else None,
                "page": f"https://dane.gov.pl/pl/dataset/{DATASET_ID}/resource/{item['id']}",
            }
    raise ValueError("no XLSX resource in the dataset")


def load(voivodeships: list[str] | None = None, client: httpx.Client | None = None) -> SourceData:
    """Return the innovation projects. A voivodeship filter keeps also projects with a foreign lead partner."""
    retrieved = date.today()
    data = SourceData(name=NAME, url=f"https://dane.gov.pl/pl/dataset/{DATASET_ID}", license=LICENSE, retrieved=retrieved)
    own_client = client is None
    client = client or httpx.Client(timeout=120, headers=fe_projects.HEADERS, follow_redirects=True)
    try:
        resource = _resource(client)
        path = CACHE / f"interreg_{resource['id']}.xlsx"
        if not path.exists():
            CACHE.mkdir(parents=True, exist_ok=True)
            response = client.get(resource["file_url"])
            response.raise_for_status()
            path.write_bytes(response.content)
    except (httpx.HTTPError, ValueError, KeyError) as error:
        cached = sorted(CACHE.glob("interreg_*.xlsx"))
        if not cached:
            data.errors.append(f"download: {error}")
            return data
        data.errors.append(f"API: {error}; the loader uses the file {cached[-1].name}")
        path = cached[-1]
        resource = {"data_date": None, "page": data.url}
    if own_client:
        client.close()
    data.data_date = resource["data_date"]
    for row in read_rows(path):
        text = f"{row['title']} {row.get('description') or ''}"
        if not (fe_projects.is_innovation(row) or SOLUTION.search(text)):
            continue
        card = to_innovation(row, resource["page"], resource["data_date"], retrieved)
        if voivodeships and card.institution.voivodeship not in (None, *voivodeships):
            continue
        data.records.append(card)
    return data
