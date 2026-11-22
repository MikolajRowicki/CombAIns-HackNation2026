"""Kohesio (European Commission, DG REGIO): finished EU projects of 2014-2020 in Poland.

The API has no documentation and no key: /api/projects (search) and /api/projects/project (details).
A finished project of 2014-2020 is a result that exists, so it fits the definition of an innovation better
than a plan. The loader searches a few Polish phrases, reads the details of each project through the shared
PageFetcher (cache, robots.txt, pause) and maps the record with the rules of the FE list (src/sources/fe_projects.py).
Kohesio has no stated licence. The reuse policy of the Commission (Decision 2011/833/EU) allows reuse with the
source: this is an assumption, written on each card.
"""

import json
import re
from datetime import date
from urllib.parse import quote, urlencode

import httpx

from src.criteria import assess
from src.models import LABELS, FieldValue, Innovation, Source
from src.sources import USER_AGENT, PageFetcher, SourceData, fe_projects

API = "https://kohesio.ec.europa.eu/api"
POLAND = "https://linkedopendata.eu/entity/Q13"
NAME = "Kohesio: projekty UE 2014-2020 (Komisja Europejska)"
LICENSE = "Brak podanej licencji; zasady ponownego wykorzystania treści KE (decyzja 2011/833/UE) – założenie"
# Phrases of the search. Each phrase gives up to PER_PHRASE projects.
PHRASES = ("innowacyjny", "e-usługi", "wdrożenie systemu", "pracownia", "aplikacja")
PER_PHRASE = 50

# Categories of intervention 2014-2020 (Regulation 215/2014), other than the codes of 2021-2027.
ADMINISTRATION = re.compile(r"^0(?:78|79|80)$")  # e-government services, access to public sector information, e-inclusion
EDUCATION = re.compile(r"^(?:049|050|051|052|115|116|117|118)$")


def _voivodeship(programme: str) -> str | None:
    m = re.search(r"[Ww]ojewództwo\s+([a-ząćęłńóśźż-]+)", programme)
    return m.group(1).lower() if m and m.group(1).lower() in LABELS["voivodeship"] else None


def to_innovation(detail: dict, retrieved: date) -> Innovation | None:
    beneficiaries = [b.get("beneficiaryLabel") for b in detail.get("beneficiaries") or [] if b.get("beneficiaryLabel")]
    if not beneficiaries or not detail.get("description"):
        return None
    programme = " ".join(p.get("programFullLabel", "") for p in detail.get("program") or [])
    voivodeship = _voivodeship(programme)
    codes = detail.get("categoryIDs") or []
    labels = detail.get("categoryLabels") or []
    url = f"https://kohesio.ec.europa.eu/pl/projects/{detail['item']}"
    row = {
        "title": detail.get("label") or detail.get("originalLabel"),
        "description": detail.get("description") or detail.get("originalDescription"),
        "contract": detail["item"],
        "beneficiary": beneficiaries[0].title() if beneficiaries[0].isupper() else beneficiaries[0],
        "programme": programme.split(" - ", 1)[-1],
        "eu": str(detail.get("euBudget") or "").lstrip("+"),
        "location": f"WOJ.: {voivodeship}" if voivodeship else "",
        "start": detail.get("startTime"),
        "end": detail.get("endTime"),
        "category": f"{codes[0]} {labels[0]}" if codes and labels else "",
    }
    # The same filter as the FE list: a project of construction or of equipment only is not an innovation.
    if not (fe_projects.is_innovation(row) or ADMINISTRATION.match(codes[0] if codes else "")):
        return None
    card = fe_projects.row_to_innovation(row, url, None, retrieved)
    data = card.model_dump()
    data["id"] = f"kohesio-{detail['item'].lower()}"
    data["sources"] = [Source(name=NAME, url=url, data_date=None, retrieved=retrieved, license=LICENSE).model_dump()]
    data["type"] = FieldValue(value="projekt UE 2014-2020", kind="fact", source_url=url).model_dump()
    code = codes[0] if codes else ""
    if ADMINISTRATION.match(code):
        data["area"] = FieldValue(
            value="administrative", kind="estimate", source_url=url,
            reason=f"Kategoria interwencji {code}: e-usługi i e-administracja.",
        ).model_dump()
        data["trl"] = None
    elif EDUCATION.match(code):
        data["area"] = FieldValue(
            value="educational", kind="estimate", source_url=url, reason=f"Kategoria interwencji {code}: edukacja."
        ).model_dump()
        data["trl"] = None
    data["assessment"] = assess(data)
    return Innovation.model_validate(data)


def load(voivodeships: list[str] | None = None, client: httpx.Client | None = None) -> SourceData:
    """Return finished projects of the search phrases. The search covers all of Poland.

    A voivodeship filter keeps the projects of the regional programmes of these voivodeships and the national ones.
    """
    retrieved = date.today()
    data = SourceData(name=NAME, url=API, license=LICENSE, retrieved=retrieved)
    own_client = client is None
    client = client or httpx.Client(timeout=60, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    fetcher = PageFetcher(client)
    items: list[str] = []
    for phrase in PHRASES:
        query = urlencode({"language": "pl", "keywords": phrase, "country": POLAND, "offset": 0, "limit": PER_PHRASE})
        try:
            found = json.loads(fetcher.get(f"{API}/projects?{query}")).get("list") or []
        except (httpx.HTTPError, PermissionError, ValueError) as error:
            data.errors.append(f"search {phrase}: {error}")
            continue
        items.extend(i["item"] for i in found if i.get("item") and i["item"] not in items)
    seen = set()
    for item in items:
        try:
            detail = json.loads(fetcher.get(f"{API}/projects/project?id={quote(f'https://linkedopendata.eu/entity/{item}', safe='')}&language=pl"))
        except (httpx.HTTPError, PermissionError, ValueError) as error:
            data.errors.append(f"{item}: {error}")
            continue
        end = str(detail.get("endTime") or "")
        if not end or date.fromisoformat(end[:10]) >= retrieved:
            continue  # only finished projects
        card = to_innovation(detail, retrieved)
        if card is None or card.id in seen:
            continue
        if voivodeships and card.institution.voivodeship not in (None, *voivodeships):
            continue
        seen.add(card.id)
        data.records.append(card)
    if own_client:
        client.close()
    return data
