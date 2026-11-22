"""Notices of public purchases from the Biuletyn Zamówień Publicznych (e-Zamówienia API, no key).

A notice shows that a public institution buys a solution now: a demand signal for similar innovations.
The loader stores only the buyer (an institution), the subject, the CPV codes and the dates.
It does not store contractors, because a contractor can be a natural person.
"""

import argparse
import time
from datetime import date, datetime, timedelta

import httpx

URL = "https://ezamowienia.gov.pl/mo-board/api/v1/notice"
NOTICE_URL = "https://ezamowienia.gov.pl/mo-client-board/bzp/notice-details/id/{}"
NAME = "BZP (e-Zamówienia)"
LICENSE = "Informacja publiczna; API BZP bezpłatne i bez wniosku (regulamin API UZP)"
PAGE_SIZE = 500
PAUSE = 3.0  # seconds between requests: the API blocked fast requests in a test
TIMEOUT = 120
DAYS = 180

# Groups of the Common Procurement Vocabulary (EU Regulation 2195/2002) that can buy innovations.
CPV_GROUPS = {
    "48000000": "pakiety oprogramowania i systemy informatyczne",
    "72000000": "usługi informatyczne",
    "80000000": "usługi edukacyjne i szkoleniowe",
    "33000000": "urządzenia medyczne i rehabilitacyjne",
    "34000000": "sprzęt transportowy",
    "09300000": "energia elektryczna, cieplna, słoneczna",
    "38000000": "sprzęt laboratoryjny, optyczny i precyzyjny",
}

# TERYT codes of the voivodeships, as the API gives them in organizationProvince (PLxx).
PROVINCES = {
    "PL02": "dolnośląskie", "PL04": "kujawsko-pomorskie", "PL06": "lubelskie", "PL08": "lubuskie",
    "PL10": "łódzkie", "PL12": "małopolskie", "PL14": "mazowieckie", "PL16": "opolskie",
    "PL18": "podkarpackie", "PL20": "podlaskie", "PL22": "pomorskie", "PL24": "śląskie",
    "PL26": "świętokrzyskie", "PL28": "warmińsko-mazurskie", "PL30": "wielkopolskie",
    "PL32": "zachodniopomorskie",
}


def _notice(raw: dict) -> dict:
    return {
        "id": raw["objectId"],
        "number": raw.get("noticeNumber"),
        "date": (raw.get("publicationDate") or "")[:10],
        "subject": (raw.get("orderObject") or "").strip(),
        "cpv": raw.get("cpvCode") or "",
        "buyer": (raw.get("organizationName") or "").strip(),
        "city": raw.get("organizationCity"),
        "voivodeship": PROVINCES.get(raw.get("organizationProvince") or ""),
        "url": NOTICE_URL.format(raw["objectId"]),
    }


def _window(client: httpx.Client, cpv: str, start: date, end: date) -> list[dict]:
    """Return the notices of one CPV group. If the page is full, split the window into two halves."""
    params = {
        "NoticeType": "ContractNotice",
        "PublicationDateFrom": start.isoformat(),
        "PublicationDateTo": end.isoformat(),
        "PageSize": PAGE_SIZE,
        "CpvCode": cpv,
    }
    response = client.get(URL, params=params)
    response.raise_for_status()
    rows = response.json()
    time.sleep(PAUSE)
    if len(rows) >= PAGE_SIZE and end > start:
        middle = start + (end - start) / 2
        return _window(client, cpv, start, middle) + _window(client, cpv, middle + timedelta(days=1), end)
    return rows


def load(days: int = DAYS, cpv_groups: list[str] | None = None, client: httpx.Client | None = None) -> dict:
    """Return the notices of the last `days` days and the metadata: source, dates, license, errors."""
    today = date.today()
    own_client = client is None
    client = client or httpx.Client(timeout=TIMEOUT, headers={"User-Agent": "RadarInnowacji/0.1"})
    notices: dict[str, dict] = {}
    errors = []
    for cpv in cpv_groups or list(CPV_GROUPS):
        try:
            for raw in _window(client, cpv, today - timedelta(days=days), today):
                if raw.get("objectId") and raw.get("organizationName"):
                    notices[raw["objectId"]] = _notice(raw)
        except (httpx.HTTPError, ValueError) as error:
            errors.append(f"CPV {cpv}: {error}")
    if own_client:
        client.close()
    dates = [n["date"] for n in notices.values() if n["date"]]
    return {
        "name": NAME,
        "url": URL,
        "license": LICENSE,
        "retrieved": today,
        "data_date": datetime.fromisoformat(max(dates)).date() if dates else None,
        "notices": list(notices.values()),
        "errors": errors,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load BZP notices and print a short report.")
    parser.add_argument("--days", type=int, default=DAYS)
    args = parser.parse_args()
    result = load(args.days)
    print(f"{len(result['notices'])} notices, data date {result['data_date']}, errors: {result['errors']}")
