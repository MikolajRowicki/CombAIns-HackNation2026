"""RAD-on open data (OPI PIB): patents and research projects of Polish science units.

API: https://radon.nauka.gov.pl/opendata/polon (no key, CC0 1.0).
The loader does not read or store the data of persons (inventors, project managers).
"""

import argparse
import re
import time
from datetime import UTC, date, datetime

import httpx

from src.criteria import assess, estimate_implementation_level, estimate_novelty
from src.models import FieldValue, Innovation, Institution, Source, TimelineEvent
from src.sources import SourceData, summary_quote

BASE_URL = "https://radon.nauka.gov.pl/opendata/polon"
NAME = "RAD-on (OPI PIB)"
LICENSE = "CC0 1.0"
PAGE_SIZE = 100
PAUSE = 0.3  # seconds between requests: the API has no published rate limit
TIMEOUT = 60

# Funders of basic research and of mobility. Their projects are not innovations in the sense
# of the Oslo Manual 2018 (no solution available to users), so the loader skips them.
NON_INNOVATION_FUNDERS = {
    "Narodowe Centrum Nauki",
    "Narodowa Agencja Wymiany Akademickiej",
    "Polsko-Amerykańska Komisja Fulbrighta",
}
EDUCATION_FUNDERS = {
    "Fundacja Rozwoju Systemu Edukacji",
    "European Education and Culture Executive Agency",
}


def _pages(client: httpx.Client, path: str, params: dict, limit: int | None = None):
    """Yield the results of all pages. The API uses a token for the next page."""
    params = {**params, "resultNumbers": PAGE_SIZE}
    count = 0
    while True:
        response = client.get(f"{BASE_URL}/{path}", params=params)
        response.raise_for_status()
        body = response.json()
        results = body.get("results") or []
        for result in results:
            yield result
            count += 1
            if limit is not None and count >= limit:
                return
        token = (body.get("pagination") or {}).get("token")
        if len(results) < PAGE_SIZE or not token:
            return
        params["token"] = token
        time.sleep(PAUSE)


def fetch_institutions(client: httpx.Client, voivodeships: list[str] | None = None) -> list[Institution]:
    """Return the active science units. None means all of Poland."""
    found = []
    for raw in _pages(client, "institutions", {}):
        if raw.get("status") != "Działająca":
            continue
        if voivodeships and raw.get("voivodeship") not in voivodeships:
            continue
        found.append(
            Institution(name=raw["name"], kind="university", city=raw.get("city"), voivodeship=raw.get("voivodeship"))
        )
    return found


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value[:10]) if value else None


def _refresh_date(raw: dict) -> date | None:
    ms = raw.get("lastRefresh")
    return datetime.fromtimestamp(int(ms) / 1000, tz=UTC).date() if ms else None


def _assessed(**fields) -> Innovation:
    data = {**fields}
    data["assessment"] = assess({k: v.model_dump() if isinstance(v, FieldValue) else v for k, v in fields.items()})
    return Innovation.model_validate(data)


def patent_to_innovation(raw: dict, institution: Institution, retrieved: date) -> Innovation:
    """Map one record of /products to a card. Patent law requires novelty, but the source has no data about use."""
    url = f"{BASE_URL}/products?resultNumbers=1&protectionUuid={raw['protectionUuid']}"
    title = raw.get("protectionTitle") or ""
    description = re.sub(r"\s+", " ", raw.get("productDescription") or title).strip()
    protection = raw.get("protectionType") or "Ochrona własności przemysłowej"
    region = raw.get("protectionRegion") or "Polska"

    def estimate(value, reason):
        return FieldValue(value=value, kind="estimate", source_url=url, reason=reason)

    timeline = []
    if raw.get("applicationDate"):
        timeline.append(
            TimelineEvent(
                date=_date(raw["applicationDate"]),
                event="patent",
                label=f"Zgłoszenie w urzędzie patentowym (nr zgłoszenia {raw.get('applicationNumber')})",
                source_url=url,
            )
        )
    if raw.get("publicationDate") and raw.get("publicationNumber"):
        timeline.append(
            TimelineEvent(
                date=_date(raw["publicationDate"]),
                event="patent",
                label=f"{protection} nr {raw['publicationNumber']}",
                source_url=url,
            )
        )

    return _assessed(
        id=f"radon-{raw.get('publicationNumber') or raw['protectionUuid']}",
        title=title,
        summary=summary_quote(description, url),
        description=description,
        area=estimate("technological", "Źródłem jest prawo ochronne uczelni w RAD-on: rozwiązanie techniczne."),
        type=FieldValue(value=protection.lower(), kind="fact", source_url=url),
        institution=institution,
        implementation_level=estimate(
            2, "Prawo ochronne potwierdza opis działającego rozwiązania. Źródło nie podaje informacji o wdrożeniu."
        ),
        trl=estimate(
            4, "Wynalazek opisany do poziomu, który pozwala go wykonać; brak danych o testach poza laboratorium."
        ),
        novelty=estimate(
            3 if region == "Polska" else 4,
            f"Prawo ochronne wymaga nowości rozwiązania. Ochrona obejmuje: {region}.",
        ),
        application_potential=estimate(None, "Źródło nie podaje danych o zastosowaniu w innych instytucjach."),
        credibility=FieldValue(value=3, kind="fact", source_url=url),
        sources=[
            Source(
                name="RAD-on: patenty i prawa ochronne (OPI PIB)",
                url=url,
                data_date=_refresh_date(raw),
                retrieved=retrieved,
                license=LICENSE,
            )
        ],
        timeline=timeline,
    )


def _funders(raw: dict) -> list[str]:
    return sorted(
        {f["financingInstitutionName"] for f in raw.get("receivedFunds") or [] if f.get("financingInstitutionName")}
    )


def is_innovation_project(raw: dict) -> bool:
    funders = _funders(raw)
    return not funders or not set(funders) <= NON_INNOVATION_FUNDERS


def project_to_innovation(raw: dict, institution: Institution, retrieved: date) -> Innovation:
    """Map one record of /projects to a card. The level and the novelty come from keyword rules."""
    url = f"{BASE_URL}/projects?resultNumbers=1&projectUuid={raw['projectUuid']}"
    title = raw.get("projectTitlePl") or raw.get("projectTitleEn") or ""
    description = re.sub(r"\s+", " ", raw.get("projectAbstractPl") or raw.get("projectAbstractEn") or title).strip()
    funders = _funders(raw)
    program = raw.get("projectClassification")
    program = None if program in (None, "Inna") else program
    end = _date(raw.get("projectEndDate"))

    def estimate(value, reason):
        return FieldValue(value=value, kind="estimate", source_url=url, reason=reason)

    educational = bool(set(funders) & EDUCATION_FUNDERS) or bool(
        re.search(r"edukac|erasmus", raw.get("projectClassification") or "", re.IGNORECASE)
    )
    area = estimate(
        "educational" if educational else "technological",
        "Projekt finansuje instytucja programów edukacyjnych." if educational else "Projekt B+R jednostki naukowej.",
    )

    level = estimate_implementation_level(description, url)
    if level["value"] is None:
        if end and end < retrieved:
            level = estimate(2, "Projekt zakończony. Źródło nie podaje informacji o wdrożeniu wyników.")
        else:
            level = estimate(1, "Projekt w trakcie realizacji. Źródło nie podaje wyników.")

    timeline = []
    grant_date = _date(raw.get("projectGrantDate") or raw.get("projectStartDate"))
    if grant_date:
        label = "Dofinansowanie projektu"
        details = ", ".join(x for x in [program, *funders] if x)
        timeline.append(
            TimelineEvent(
                date=grant_date, event="grant", label=f"{label} ({details})" if details else label, source_url=url
            )
        )

    keywords = [k.strip() for k in (raw.get("keywords") or "").split(",") if k.strip()]

    return _assessed(
        id=f"radon-project-{raw['projectUuid']}",
        title=title,
        summary=summary_quote(description, url),
        description=description,
        area=area,
        type=FieldValue(value="projekt " + (program or "badawczo-rozwojowy"), kind="fact", source_url=url),
        institution=institution,
        implementation_level=FieldValue.model_validate(level),
        trl=None if educational else estimate(None, "Źródło nie podaje poziomu TRL."),
        novelty=FieldValue.model_validate(estimate_novelty(description, url)),
        application_potential=estimate(None, "Źródło nie podaje danych o zastosowaniu w innych instytucjach."),
        credibility=FieldValue(value=3, kind="fact", source_url=url),
        sources=[
            Source(
                name="RAD-on: projekty badawcze (OPI PIB)",
                url=url,
                data_date=_refresh_date(raw),
                retrieved=retrieved,
                license=LICENSE,
            )
        ],
        timeline=timeline,
        keywords=keywords,
    )


def load(
    voivodeships: list[str] | None = None,
    limit_per_institution: int | None = None,
    include_projects: bool = True,
    client: httpx.Client | None = None,
) -> SourceData:
    """Return the patents and the innovation projects of the science units in the given voivodeships.

    None means all of Poland. If one request fails, the loader records the error and continues.
    """
    retrieved = date.today()
    data = SourceData(name=NAME, url=BASE_URL, license=LICENSE, retrieved=retrieved)
    own_client = client is None
    client = client or httpx.Client(timeout=TIMEOUT, headers={"User-Agent": "RadarInnowacji/0.1"})
    seen: set[str] = set()

    def add(record: Innovation, raw: dict) -> None:
        if record.id in seen:
            return
        seen.add(record.id)
        data.records.append(record)
        refreshed = _refresh_date(raw)
        if refreshed and (data.data_date is None or refreshed > data.data_date):
            data.data_date = refreshed

    try:
        institutions = fetch_institutions(client, voivodeships)
    except httpx.HTTPError as error:
        data.errors.append(f"institutions: {error}")
        institutions = []

    for institution in institutions:
        filters = [("products", {"institutionName": institution.name}, patent_to_innovation)]
        if include_projects:
            filters.append(("projects", {"entityShowingAchievementsName": institution.name}, project_to_innovation))
        for path, params, mapper in filters:
            try:
                for raw in _pages(client, path, params, limit_per_institution):
                    if path == "projects" and not is_innovation_project(raw):
                        continue
                    add(mapper(raw, institution, retrieved), raw)
            except (httpx.HTTPError, ValueError, KeyError) as error:
                data.errors.append(f"{path} {institution.name}: {error}")
            time.sleep(PAUSE)

    if own_client:
        client.close()
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load RAD-on records and print a short report.")
    parser.add_argument("--voivodeship", action="append", help="for example podkarpackie; default: all of Poland")
    parser.add_argument("--limit", type=int, default=None, help="records of each type for one institution")
    args = parser.parse_args()
    result = load(args.voivodeship, args.limit)
    print(f"{len(result.records)} records, data date {result.data_date}, errors: {len(result.errors)}")
    for error in result.errors:
        print("  ", error)
