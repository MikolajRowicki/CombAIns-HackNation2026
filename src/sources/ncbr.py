"""NCBR "Wyszukiwarka sukcesów beneficjentów": finished projects with results, as NCBR describes them.

The list page has about 316 projects. Each project has a page with the sections "Jaki problem rozwiązuje
nasz projekt?" and "Kto korzysta/skorzysta z wyników projektu?". The loader takes only these sections.
It does not take the section about the team, and it removes names of persons from the list of beneficiaries.
The list is small and national, so the loader reads all of it. The voivodeship filter does not apply.
"""

import difflib
import re
from datetime import date

import httpx
from bs4 import BeautifulSoup

from src.criteria import assess, estimate_implementation_level, estimate_novelty
from src.models import (
    LABELS,
    FieldValue,
    Innovation,
    Institution,
    Source,
    TimelineEvent,
)
from src.sources import USER_AGENT, PageFetcher, SourceData, fe_projects, summary_quote

URL = "https://www.gov.pl/web/ncbr/wyszukiwarka-sukcesow-beneficjentow"
NAME = "NCBR: Wyszukiwarka sukcesów beneficjentów"
LICENSE = "Informacja publiczna (gov.pl); licencja nie jest podana; radar zapisuje opis z linkiem"

SECTIONS = ("Jaki problem rozwiązuje nasz projekt?", "Kto korzysta/skorzysta z wyników projektu?")
_INSTITUTION = re.compile(
    r"uniwersytet|politechnika|akademia|uczelnia|instytut|centrum|sp\.|spółka|s\.\s?a\.|fundacja|stowarzysz"
    r"|szkoła|gmina|miasto|powiat|województwo|zakład|przedsiębiorstwo|łukasiewicz|szpital|konsorcjum|grupa"
    r"|polsk|laborator|ośrodek|park|klaster|izba|związek|technolog|systems|solutions|tech|\bpan\b"
    r"|wydział|komendant|główn|policj|straż|wojsk|ministerstw|urząd",
    re.IGNORECASE,
)
_PERSON = re.compile(r"^[A-ZŁŚŻŹĆÓ][a-ząćęłńóśźż]+(?:-[A-ZŁŚŻŹĆÓ][a-ząćęłńóśźż]+)?(?:\s+[A-ZŁŚŻŹĆÓ][a-ząćęłńóśźż]+(?:-[A-ZŁŚŻŹĆÓ][a-ząćęłńóśźż]+)?){1,3}$")
_TITLE_OF_PERSON = re.compile(r"\b(?:dr|prof|mgr|inż|hab)\.?\s+(?:hab\.\s+)?(?:inż\.\s+)?[A-ZŁŚŻŹĆÓ][a-ząćęłńóśźż]+")
_DATES = re.compile(r"(\d{2})[.-](\d{2})[.-](\d{4})")
_TRL = re.compile(r"\bTRL\s*(\d)\b")


def _valid(d: str, m: str, y: str) -> bool:
    try:
        date(int(y), int(m), int(d))
    except ValueError:
        return False
    return True


def _clean(name: str) -> str:
    """Remove labels such as "Beneficjent:" or "Lider konsorcjum:" before a name."""
    name = name.replace("\xa0", " ").strip()
    label = r"^(?:beneficjent|lider(?: konsorcjum)?|partner(?:zy)?(?: zagraniczni)?|konsorcjum)\s*:\s*"
    return re.sub(label, "", name, flags=re.IGNORECASE).strip()


def is_person(name: str) -> bool:
    name = name.strip()
    return bool(_PERSON.match(name)) and not _INSTITUTION.search(name)


def institution_kind(name: str) -> str:
    low = name.lower()
    if re.search(r"uniwersytet|politechnika|akademia|uczelnia|instytut|łukasiewicz|szkoła wyższa|\bpan\b", low):
        return "university"
    if re.search(r"szkoła|liceum|przedszkol|technikum", low):
        return "school"
    if re.search(r"\bgmina|\bmiasto|\bpowiat|województwo", low):
        return "jst"
    if re.search(r"sp\.|spółka|s\.\s?a\.|\bsa\b", low):
        return "company"
    return "other"


def _fields(details) -> dict:
    """Read the pairs "heading -> value" of one <details> block of the list page."""
    # A consortium can be one paragraph with line breaks: a break separates two beneficiaries.
    for br in details.find_all("br"):
        br.replace_with("|")
    out = {"title": details.find("summary").get_text(" ", strip=True).replace("\xa0", " ")}
    label = None
    for node in details.find_all(["h3", "p", "li"]):
        if node.name == "p" and node.find_parent("li"):
            continue
        text = node.get_text(" ", strip=True).replace("\xa0", " ")
        if not text or "więcej" in text:
            continue
        # The page writes the same heading in different ways ("Słowa Kluczowe", "Słowa kluczowe").
        key = text.rstrip(":").strip().lower()
        if node.name == "h3" or key in ("region", "słowa kluczowe"):
            label = key
        elif label:
            # A value can have several paragraphs or list items, for example the members of a consortium.
            out[label] = f"{out[label]}, {text}" if label in out else text
    link = next((a.get("href") for a in details.find_all("a") if "więcej" in a.get_text()), None)
    out["link"] = link
    return out


def parse_list(html: str) -> list[dict]:
    return [_fields(d) for d in BeautifulSoup(html, "html.parser").select("details")]


def parse_sections(html: str) -> str:
    """Return the text of the sections about the problem and the users. Sentences with names of persons go out."""
    import trafilatura

    text = trafilatura.extract(html, favor_recall=True) or ""
    lines = [line.strip() for line in text.replace("\xa0", " ").splitlines()]
    parts, keep = [], False
    for line in lines:
        if line in SECTIONS:
            keep = True
            continue
        if line.endswith("?") or line.startswith(("Nasza rada", "Poznajcie", "Zobacz efekt")):
            keep = False
            continue
        if keep and line:
            parts.append(line)
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(parts))
    # A sentence with a title and a name, or with a first name and a surname ("Wojciech Wieczorek"), goes out.
    return " ".join(
        s for s in sentences if not _TITLE_OF_PERSON.search(s) and not fe_projects.person_name(s)
    ).strip()


def _region(text: str | None) -> str | None:
    """Return the official name of the voivodeship. The page has typing errors, for example "zachodnioporskie"."""
    if not text:
        return None
    word = text.lower().replace("województwo", "").split(",")[0].strip().replace(" ", "-")
    match = difflib.get_close_matches(word, LABELS["voivodeship"], n=1, cutoff=0.75)
    return match[0] if match else None


def _institution_name(name: str) -> str:
    """Remove the role in a consortium: "Politechnika Białostocka – lider konsorcjum" -> "Politechnika Białostocka"."""
    name = re.split(r"\s*\((?:lider|konsorcjant|członek)", name, flags=re.IGNORECASE)[0]
    name = re.split(r"\s+[–-]\s+(?:lider|członek|konsorcjant)", name, flags=re.IGNORECASE)[0]
    return re.sub(r"^konsorcjum\s+", "", name, flags=re.IGNORECASE).strip()


def to_innovation(item: dict, description: str, retrieved: date) -> Innovation | None:
    url = item["link"] or URL
    beneficiaries = [_clean(b) for b in re.split(r"[,;|]", item.get("nazwa beneficjenta/beneficjentów", ""))]
    institutions = [b for b in beneficiaries if b and not b.endswith(":") and not is_person(b)]
    if not institutions:
        return None
    name = _institution_name(institutions[0])
    title = item["title"]
    description = description or title
    program = item.get("nazwa programu", "")
    contest = item.get("konkurs", "")
    keywords = [k.strip() for k in re.split(r"[,;]", item.get("słowa kluczowe", "")) if k.strip()]
    period = item.get("okres realizacji projektu", "")
    dates = [date(int(y), int(m), int(d)) for d, m, y in _DATES.findall(period) if _valid(d, m, y)]

    def estimate(value, reason, evidence=None):
        return FieldValue(value=value, kind="estimate", source_url=url, evidence=evidence, reason=reason)

    text = f"{title} {' '.join(keywords)} {program} {contest}".lower()
    if re.search(r"eduk|pedagog|nauczan|szkoł|kompetencj|dydakty|uczel", text) or "wiedza edukacja" in text:
        area = estimate("educational", "Program lub słowa kluczowe dotyczą edukacji.")
    elif institution_kind(name) == "jst" or re.search(r"administrac|samorząd|usług\w* publiczn", text):
        area = estimate("administrative", "Beneficjent lub słowa kluczowe dotyczą administracji publicznej.")
    else:
        area = estimate("technological", "Projekt B+R z listy sukcesów NCBR.")

    level = estimate_implementation_level(description, url)
    finished = bool(dates) and dates[-1] < retrieved
    # The section "Kto skorzysta" is often in the future tense. For a finished project with a result, a plan word
    # does not mean a concept: the level is at least 3 (tests).
    if level["value"] is None or (finished and level["value"] < 3):
        if finished:
            level = estimate(3, "Projekt zakończony z opisanym rezultatem (lista sukcesów NCBR); źródło nie potwierdza stałego użycia.")
        else:
            level = estimate(2, "Projekt w trakcie realizacji.")
    trl = None
    if area.value == "technological":
        m = _TRL.search(description)
        trl = (
            estimate(int(m.group(1)), "Tekst źródła podaje poziom TRL.", m.group(0))
            if m and 1 <= int(m.group(1)) <= 9
            else estimate(None, "Źródło nie podaje poziomu TRL.")
        )
    novelty = estimate_novelty(description, url)

    fields = {
        "id": "ncbr-" + re.sub(r"[^a-z0-9]+", "-", url.rsplit("/", 1)[-1].lower())[:70].strip("-"),
        "title": title,
        "summary": summary_quote(description, url),
        "description": description,
        "area": area,
        "type": FieldValue(value=f"projekt {contest or program}".strip(), kind="fact", source_url=url),
        "institution": Institution(name=name, kind=institution_kind(name), voivodeship=_region(item.get("region"))),
        "implementation_level": FieldValue.model_validate(level),
        "trl": trl,
        "novelty": FieldValue.model_validate(novelty),
        "application_potential": estimate(None, "Źródło nie podaje kosztu ani dokumentacji dla innych odbiorców."),
        "credibility": FieldValue(value=3, kind="fact", source_url=url),
        "keywords": keywords,
    }
    assessment = assess({k: v.model_dump() if isinstance(v, FieldValue) else v for k, v in fields.items()})
    timeline = []
    if dates:
        value = item.get("wartość dofinansowania")
        label = f"Dofinansowanie NCBR ({contest or program})" + (f", {value}" if value else "")
        timeline.append(TimelineEvent(date=dates[0], event="grant", label=label, source_url=url))
    return Innovation(
        **fields,
        assessment=assessment,
        sources=[Source(name=NAME, url=url, data_date=None, retrieved=retrieved, license=LICENSE)],
        timeline=timeline,
    )


def load(voivodeships: list[str] | None = None, client: httpx.Client | None = None) -> SourceData:
    """Return the cards of all projects of the list. The voivodeship filter does not apply (see the docstring)."""
    retrieved = date.today()
    data = SourceData(name=NAME, url=URL, license=LICENSE, retrieved=retrieved)
    own_client = client is None
    client = client or httpx.Client(timeout=60, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    fetcher = PageFetcher(client)
    try:
        items = parse_list(fetcher.get(URL))
    except (httpx.HTTPError, PermissionError) as error:
        data.errors.append(f"list: {error}")
        items = []
    seen = set()
    for item in items:
        description = ""
        if item.get("link"):
            try:
                description = parse_sections(fetcher.get(item["link"]))
            except (httpx.HTTPError, PermissionError) as error:
                data.errors.append(f"{item['link']}: {error}")
        record = to_innovation(item, description, retrieved)
        if record and record.id not in seen:
            seen.add(record.id)
            data.records.append(record)
    if own_client:
        client.close()
    return data
