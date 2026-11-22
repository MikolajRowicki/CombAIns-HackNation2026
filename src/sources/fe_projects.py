"""List of projects of the EU funds 2021-2027 in Poland (Ministry of Funds and Regional Policy, dane.gov.pl, CC0 1.0).

The ministry publishes one XLSX file each month. The loader takes the newest file of the dataset.
The loader keeps projects with an innovation signal and hides the names of natural persons (AGENTS.md).
"""

import argparse
import hashlib
import itertools
import re
from datetime import date, datetime
from pathlib import Path

import httpx
import openpyxl

from src.criteria import assess, estimate_novelty
from src.models import FieldValue, Innovation, Institution, Source, TimelineEvent
from src.sources import SourceData, summary_quote

DATASET_ID = 13939
API = "https://api.dane.gov.pl/1.4"
NAME = "Lista projektów FE 2021-2027 (dane.gov.pl)"
LICENSE = "CC0 1.0"
CACHE = Path(__file__).resolve().parents[2] / "data" / "cache"
TIMEOUT = 120
HEADERS = {"User-Agent": "RadarInnowacji/0.1"}

# Columns of the file (header row 2). The loader finds them by the Polish part of the name.
COLUMNS = {
    "title": "Nazwa projektu",
    "description": "Opis projektu",
    "contract": "Numer umowy/decyzji",
    "beneficiary": "Nazwa beneficjenta",
    "programme": "Program",
    "total": "Wartość projektu",
    "eu": "Dofinansowanie z UE",
    "location": "Miejsce realizacji projektu",
    "start": "Data rozpoczęcia projektu",
    "end": "Data zakończenia projektu",
    "category": "Kategoria wsparcia",
}

# Innovation signal: a category of intervention of research, innovation or ICT, or a word in the title.
# The categories come from Annex I of Regulation (EU) 2021/1060 (codes 002-030, 016 and others).
INNOVATION_CATEGORY = re.compile(
    r"innowac|badawcz|TIK|cyfryz|transfer technologii|usługi elektroniczne|e-zdrow|inteligentn", re.IGNORECASE
)
INNOVATION_TITLE = re.compile(
    r"innowac|e-usług|nowatorsk|sztuczn\w* inteligenc|robotyz|automatyzac|cyfryzac|platform[aęy] (?:cyfrow|e-|internet)",
    re.IGNORECASE,
)
MIN_DESCRIPTION = 80

EDUCATION_CATEGORY = re.compile(r"^1(?:4[5-9]|5[0-2])\b")  # 145-152: education and training
EDUCATION_TITLE = re.compile(r"szkoł|edukac|uczni|nauczyc|przedszk|dydakt|studen", re.IGNORECASE)
# A project of a school (categories 148-150: pre-school, primary and secondary, higher education) is an educational
# innovation if its text names a method or a tool of teaching (FAQ, section 2: methods and tools of education).
SCHOOL_CATEGORY = re.compile(r"^1(?:48|49|50)\b")
SCHOOL_METHOD = re.compile(
    r"robot|programowani|STEAM|\bSTEM\b|metod\w* (?:nauczania|aktywizując|eksperyment|projekt)|eksperyment"
    r"|pracowni\w* (?:przyrodnicz|cyfrow|robot|chemiczn|fizyczn|matematyczn)|druk\w* 3D|wirtualn\w* rzeczywist"
    r"|innowac\w* pedagog|tutoring|oceniani\w* kształtując|nauczani\w* zdaln|platform\w* (?:edukac|e-learning)",
    re.IGNORECASE,
)
ADMINISTRATION_CATEGORY = re.compile(r"^016\b")  # ICT solutions and e-services for the public administration
PUBLIC_BODY = re.compile(
    r"\b(?:gmina|miasto|powiat|województwo|urząd|starostwo|wojewoda|ministerstwo|minister|marszał|"
    r"związek\s+(?:gmin|powiatów|komunalny)|komenda|zarząd\s+(?:dróg|województwa))",
    re.IGNORECASE,
)
SCHOOL = re.compile(r"\b(?:szkoła|zespół szkół|liceum|technikum|przedszkole|szkół)\b", re.IGNORECASE)
UNIVERSITY = re.compile(
    r"\b(?:uniwersytet|politechnika|akademia|uczelnia|instytut|szkoła wyższa|wyższa szkoła)\b", re.IGNORECASE
)
INSTITUTION_WORDS = re.compile(
    r"stowarzysz|fundacj|caritas|zrzeszen|wojewod|polsk|politechnik|uniwersytet|akademi|uczelni|instytut|szpital"
    r"|centrum|zakład|przedsiębiorstw|spółdzielni|muzeum|teatr|bibliotek|ośrod|agencj|izba|park|klaster|szkoł|zespół",
    re.IGNORECASE,
)
# Foreign partners of Interreg projects, for example "Obec Skalité" or "Cardinal Stefan Wyszynski Hospital".
# A name with one of these words is an institution, also if it has a first name of a patron.
FOREIGN_INSTITUTION = re.compile(
    r"municipalit|commune|\bobec\b|\bmesto\b|město|euroregion|universit|county|region|voivodeship|administration"
    r"|department|centre|center|association|foundation|hochschule|gemeinde|stadt|savivaldyb|council|office|agency"
    r"|hospital|college|cluster",
    re.IGNORECASE,
)
COMPANY = re.compile(r"\b(?:sp\.?\s*z\s*o\.?\s*o|spółka|s\.\s*a\.|sp\.\s*k\.|sp\.\s*j\.|s\.c\.)", re.IGNORECASE)

# Common Polish first names (nominative). A beneficiary name with a first name and a surname is a natural
# person or a sole trader. The loader hides this name, because it is personal data (AGENTS.md).
FIRST_NAMES = frozenset(
    [
        "adam",
        "adrian",
        "agata",
        "agnieszka",
        "aleksander",
        "aleksandra",
        "alicja",
        "andrzej",
        "aneta",
        "anna",
        "antoni",
        "arkadiusz",
        "artur",
        "barbara",
        "bartosz",
        "beata",
        "bogdan",
        "bogusław",
        "bożena",
        "czesław",
        "damian",
        "daniel",
        "dariusz",
        "dawid",
        "dominik",
        "dorota",
        "edyta",
        "elżbieta",
        "emil",
        "ewa",
        "ewelina",
        "filip",
        "franciszek",
        "grażyna",
        "grzegorz",
        "halina",
        "hanna",
        "henryk",
        "irena",
        "iwona",
        "jacek",
        "jadwiga",
        "jakub",
        "jan",
        "janina",
        "janusz",
        "jarosław",
        "jerzy",
        "joanna",
        "jolanta",
        "józef",
        "julia",
        "julian",
        "justyna",
        "kamil",
        "karol",
        "karolina",
        "katarzyna",
        "kazimierz",
        "kinga",
        "konrad",
        "krystian",
        "krystyna",
        "krzysztof",
        "leszek",
        "lucyna",
        "łukasz",
        "maciej",
        "magdalena",
        "małgorzata",
        "marcin",
        "marek",
        "maria",
        "mariusz",
        "marta",
        "marzena",
        "mateusz",
        "michalina",
        "michał",
        "mieczysław",
        "mirosław",
        "monika",
        "natalia",
        "norbert",
        "oliwia",
        "patryk",
        "paweł",
        "piotr",
        "przemysław",
        "radosław",
        "rafał",
        "renata",
        "robert",
        "roman",
        "ryszard",
        "sebastian",
        "sławomir",
        "stanisław",
        "stefan",
        "sylwia",
        "szymon",
        "tadeusz",
        "teresa",
        "tomasz",
        "urszula",
        "wacław",
        "waldemar",
        "wiesław",
        "wiktor",
        "wiktoria",
        "wioletta",
        "witold",
        "władysław",
        "wojciech",
        "zbigniew",
        "zdzisław",
        "zenon",
        "zofia",
    ]
)
_WORD = re.compile(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż-]+")
HIDDEN_NAME = "osoba fizyczna lub przedsiębiorca indywidualny (dane ukryte)"


def person_name(beneficiary: str, foreign: bool = False) -> str | None:
    """Return the part of the name that is a first name and a surname, or None.

    A patron after "im." (for example "Szkoła Podstawowa im. Marii Konopnickiej") is not a beneficiary.
    """
    # Only for lists with foreign partners (Interreg). In the FE list, "Jan Kowalski Auto Center" is a sole trader.
    if foreign and FOREIGN_INSTITUTION.search(beneficiary):
        return None
    text = re.split(r"\bim\.|\bimienia\b", beneficiary, maxsplit=1)[0]
    words = _WORD.findall(text)
    for first, last in itertools.pairwise(words):
        if first.lower() in FIRST_NAMES and last[:1].isupper() and last.lower() not in FIRST_NAMES | {"sp", "spółka"}:
            return f"{first} {last}"
    # Two words such as "Jan Kowalski" or "JAN KOWALSKI", without a legal form, are a natural person.
    if (
        len(words) == 2
        and not PUBLIC_BODY.search(text)
        and not COMPANY.search(text)
        and all(w[:1].isupper() for w in words)
        and not INSTITUTION_WORDS.search(text)
    ):
        return text.strip()
    return None


def hide(text: str, name: str | None) -> str:
    """Remove the name of a person from the text. The name can be in the title or in the description."""
    if not name or not text:
        return text
    for part in [name, *name.split()]:
        if len(part) > 2:
            text = re.sub(rf"\b{re.escape(part)}\b", "[dane ukryte]", text, flags=re.IGNORECASE)
    return text


def _voivodeships(location: str) -> list[str]:
    return [v.strip().lower() for v in re.findall(r"WOJ\.:\s*([^,;]+)", location or "")]


def _city(location: str) -> str | None:
    match = re.search(r"GM\.:\s*([^,;]+)", location or "")
    return re.sub(r"\s*[-(].*$", "", match.group(1)).strip() if match else None


def _institution_kind(name: str) -> str:
    if SCHOOL.search(name) and not UNIVERSITY.search(name):
        return "school"
    if UNIVERSITY.search(name):
        return "university"
    if PUBLIC_BODY.search(name):
        return "jst"
    if COMPANY.search(name):
        return "company"
    return "other"


def _date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _millions(value) -> str | None:
    try:
        return f"{float(value) / 1e6:.1f}".replace(".", ",") + " mln zł"
    except (TypeError, ValueError):
        return None


def is_innovation(row: dict) -> bool:
    if len(str(row.get("description") or "")) < MIN_DESCRIPTION:
        return False
    if SCHOOL_CATEGORY.search(str(row.get("category") or "")) and SCHOOL_METHOD.search(
        f"{row.get('title') or ''} {row.get('description') or ''}"
    ):
        return True
    return bool(
        INNOVATION_CATEGORY.search(str(row.get("category") or ""))
        or INNOVATION_TITLE.search(str(row.get("title") or ""))
    )


def row_to_innovation(
    row: dict, resource_url: str, data_date: date | None, retrieved: date, foreign: bool = False
) -> Innovation:
    """Map one row of the file to a card. The description comes from the application, so the text is in the future tense.

    Thus the implementation level comes from the dates of the project, not from the text (test on the real file).
    """
    beneficiary = str(row.get("beneficiary") or "").strip()
    person = person_name(beneficiary, foreign)
    title = hide(re.sub(r"\s+", " ", str(row["title"])).strip(), person)
    description = hide(re.sub(r"\s+", " ", str(row["description"])).strip(), person)
    category = re.sub(r"\s+", " ", str(row.get("category") or "")).strip()
    category_label = re.sub(r"^\S+\s+", "", category) or "projekt FE"
    programme = str(row.get("programme") or "").strip()
    contract = str(row.get("contract") or "").strip()
    location = str(row.get("location") or "")
    regions = _voivodeships(location)
    start, end = _date(row.get("start")), _date(row.get("end"))
    url = resource_url

    def estimate(value, reason, evidence=None):
        return FieldValue(value=value, kind="estimate", source_url=url, evidence=evidence, reason=reason)

    name = HIDDEN_NAME if person else beneficiary
    institution = Institution(
        name=name or "brak nazwy beneficjenta",
        kind="company" if person else _institution_kind(beneficiary),
        city=_city(location),
        voivodeship=regions[0] if regions else None,
    )

    if EDUCATION_CATEGORY.search(category) or EDUCATION_TITLE.search(title):
        area = estimate("educational", "Kategoria wsparcia lub tytuł projektu dotyczy edukacji.")
    elif ADMINISTRATION_CATEGORY.search(category) or (institution.kind == "jst" and not person):
        area = estimate(
            "administrative", "Beneficjent to instytucja publiczna lub projekt dotyczy e-usług administracji."
        )
    else:
        area = estimate("technological", f"Kategoria wsparcia: {category_label}.")

    text = f"{title}. {description}"
    if end and end < retrieved:
        level = estimate(
            4, f"Projekt zakończony ({end:%d.%m.%Y}). Opis pochodzi z wniosku; źródło nie potwierdza stałego użycia."
        )
    elif start and start <= retrieved:
        until = f" do {end:%d.%m.%Y}" if end else ""
        level = estimate(2, f"Projekt w realizacji{until}. Wynik nie jest jeszcze potwierdzony.")
    else:
        level = estimate(1, "Projekt jeszcze się nie rozpoczął.")

    novelty = estimate_novelty(text, url)
    if novelty["value"] is None and re.search(r"innowac|badawcz", category, re.IGNORECASE):
        novelty = estimate(
            1, "Wsparcie w kategorii innowacji lub B+R wymaga nowości co najmniej w instytucji (Oslo Manual)."
        )

    timeline = []
    if start and start <= retrieved:
        money = _millions(row.get("eu"))
        details = ", ".join(x for x in [programme, f"dofinansowanie UE {money}" if money else None] if x)
        timeline.append(
            TimelineEvent(
                date=start, event="grant", label=f"Start projektu z dofinansowaniem ({details})", source_url=url
            )
        )
    if end and end < retrieved:
        timeline.append(
            TimelineEvent(date=end, event="implementation", label="Zakończenie projektu (data z umowy)", source_url=url)
        )

    record = {
        "id": "fe-"
        + (re.sub(r"[^a-z0-9]+", "-", contract.lower()).strip("-") or hashlib.md5(title.encode()).hexdigest()[:12]),
        "title": title,
        "summary": summary_quote(description, url),
        "description": description,
        "area": area,
        "type": FieldValue(value=f"projekt FE: {category_label[:1].lower()}{category_label[1:]}", kind="fact", source_url=url),
        "institution": institution,
        "implementation_level": FieldValue.model_validate(level),
        "trl": estimate(None, "Źródło nie podaje poziomu TRL.") if area.value == "technological" else None,
        "novelty": FieldValue.model_validate(novelty),
        "application_potential": estimate(None, "Źródło nie podaje danych o zastosowaniu w innych instytucjach."),
        "credibility": FieldValue(value=3, kind="fact", source_url=url),
        "sources": [Source(name=NAME, url=url, data_date=data_date, retrieved=retrieved, license=LICENSE)],
        "timeline": timeline,
        "keywords": [category_label.lower()] if category_label else [],
    }
    plain = {k: v.model_dump() if isinstance(v, FieldValue) else v for k, v in record.items()}
    return Innovation.model_validate({**record, "assessment": assess(plain)})


def newest_resource(client: httpx.Client) -> dict:
    """Return the id, the date, the file link and the page of the newest XLSX of the dataset."""
    response = client.get(f"{API}/datasets/{DATASET_ID}/resources", params={"sort": "-data_date", "per_page": 5})
    response.raise_for_status()
    for item in response.json()["data"]:
        attributes = item["attributes"]
        if attributes.get("format") == "xlsx":
            return {
                "id": item["id"],
                "data_date": _date(attributes.get("data_date")),
                "link": attributes.get("link") or attributes.get("download_url"),
                "page": f"https://dane.gov.pl/pl/dataset/{DATASET_ID}/resource/{item['id']}",
            }
    raise ValueError("Zbiór nie ma pliku XLSX")


def download(client: httpx.Client) -> tuple[Path, dict]:
    """Download the newest file once. If the API does not answer, use a file in data/cache/ (downloaded by hand)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        resource = newest_resource(client)
    except (httpx.HTTPError, ValueError, KeyError):
        files = sorted(CACHE.glob("fe_*.xlsx"))
        if not files:
            raise
        rid = files[-1].stem.removeprefix("fe_")
        resource = {"id": rid, "data_date": None, "page": f"https://dane.gov.pl/pl/dataset/{DATASET_ID}/resource/{rid}"}
        return files[-1], resource
    path = CACHE / f"fe_{resource['id']}.xlsx"
    if not path.exists():
        with client.stream("GET", resource["link"], follow_redirects=True) as response:
            response.raise_for_status()
            part = path.with_suffix(".part")
            with part.open("wb") as file:
                for chunk in response.iter_bytes():
                    file.write(chunk)
            part.replace(path)
    return path, resource


def read_rows(path: Path):
    """Yield the rows of the file as dicts with the keys of COLUMNS."""
    workbook = openpyxl.load_workbook(path, read_only=True)
    try:
        rows = workbook.worksheets[0].iter_rows(values_only=True)
        index = None
        for row in rows:
            cells = [str(c or "").replace("\xa0", " ").strip() for c in row]
            if index is None:
                if any(c.startswith(COLUMNS["title"]) for c in cells):
                    index = {
                        key: next(i for i, c in enumerate(cells) if c.startswith(label))
                        for key, label in COLUMNS.items()
                    }
                continue
            if row and row[index["title"]]:
                yield {key: row[i] for key, i in index.items()}
    finally:
        workbook.close()


def load(
    voivodeships: list[str] | None = None, path: Path | None = None, client: httpx.Client | None = None
) -> SourceData:
    """Return the innovation projects in the given voivodeships. None means all of Poland.

    Projects for the whole country ("Cały Kraj") are always included: they serve all regions.
    """
    retrieved = date.today()
    own_client = client is None
    client = client or httpx.Client(timeout=TIMEOUT, headers=HEADERS)
    try:
        if path is None:
            path, resource = download(client)
        else:
            resource = {"id": path.stem, "data_date": None, "page": f"https://dane.gov.pl/pl/dataset/{DATASET_ID}"}
    finally:
        if own_client:
            client.close()

    data = SourceData(
        name=NAME, url=resource["page"], license=LICENSE, retrieved=retrieved, data_date=resource["data_date"]
    )
    wanted = {v.lower() for v in voivodeships} if voivodeships else None
    seen: set[str] = set()
    for row in read_rows(path):
        if not is_innovation(row):
            continue
        regions = _voivodeships(str(row.get("location") or ""))
        if wanted and regions and not wanted & set(regions):
            continue
        try:
            record = row_to_innovation(row, resource["page"], resource["data_date"], retrieved)
        except (ValueError, TypeError) as error:
            data.errors.append(f"{row.get('contract')}: {error}")
            continue
        if record.id not in seen:
            seen.add(record.id)
            data.records.append(record)
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load the FE 2021-2027 projects and print a short report.")
    parser.add_argument("--voivodeship", action="append", help="for example podkarpackie; default: all of Poland")
    args = parser.parse_args()
    result = load(args.voivodeship)
    print(f"{len(result.records)} records, data date {result.data_date}, errors: {len(result.errors)}")
    for error in result.errors[:10]:
        print("  ", error)
