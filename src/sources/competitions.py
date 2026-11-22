"""Result pages of competitions: one card for each awarded project.

The list of pages is in data/web_sources.csv (category "competition_results"). Thus the code has no list of competitions.
The first parser reads "Innowacyjny Samorząd" (Serwis Samorządowy PAP, pages on wartowiedziec.pl).
A laureate is an institution (a JST). The loader does not store names of persons.
The loader obeys robots.txt and its Crawl-delay, and keeps the pages in data/cache/pages/.
"""

import csv
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura
from protego import Protego

from src.criteria import assess, estimate_novelty
from src.models import FieldValue, Innovation, Institution, Source, TimelineEvent
from src.sources import SourceData

ROOT = Path(__file__).resolve().parents[2]
SOURCES_CSV = ROOT / "data" / "web_sources.csv"
CACHE = ROOT / "data" / "cache" / "pages"
CACHE_DAYS = 7
USER_AGENT = "RadarInnowacji/0.1"
MIN_PAUSE = 1.5
NAME = "Wyniki konkursów (strony WWW)"
LICENSE = "Prawa wydawcy strony; radar zapisuje krótki cytat i link (art. 26³ i 29 pr. aut.)"

VOIVODESHIPS = {
    "dolnośląsk": "dolnośląskie", "kujawsko-pomorsk": "kujawsko-pomorskie", "lubelsk": "lubelskie",
    "lubusk": "lubuskie", "łódzk": "łódzkie", "małopolsk": "małopolskie", "mazowieck": "mazowieckie",
    "opolsk": "opolskie", "podkarpack": "podkarpackie", "podlask": "podlaskie", "pomorsk": "pomorskie",
    "śląsk": "śląskie", "świętokrzysk": "świętokrzyskie", "warmińsko-mazursk": "warmińsko-mazurskie",
    "wielkopolsk": "wielkopolskie", "zachodniopomorsk": "zachodniopomorskie",
}

_QUOTE = re.compile(r"[„\"]([^”\"]{5,300})[”\"]")
# "<laureate> za projekt „<title>”". The laureate is the text after the last separator.
_FOR_PROJECT = re.compile(r"([^;:„”]{2,120}?)\s+za\s+(?:projekt\s+)?[„\"]((?:[^”\"]|”(?=\S))+?)[”\"](?=[\s,.;:)]|$)")
_SEPARATORS = re.compile(
    r".*(?:[:;]|\boraz\b|\botrzymał\w*|\bzajął\w*|\bzajęł\w*|\bprzyznano|\bprzypadło|\bex\s+aequo|\bzwyciężył\w*|\bwyróżnion\w*)\s*",
    re.IGNORECASE | re.DOTALL,
)
_IN_TITLE = [
    (re.compile(r"\b[Ww]ojewództw\w*\s+([A-ZŁŚŻŹĆÓa-ząćęłńóśźż-]+)"), "woj."),
    (re.compile(r"\b[Pp]owi(?:at|ecie|atu)\w*\s+([A-ZŁŚŻŹĆÓa-ząćęłńóśźż-]+)"), "pow."),
    (re.compile(r"\b[Gg]min(?:y|ie|a)\s+([A-ZŁŚŻŹĆÓ][\w-]+(?:\s+[A-ZŁŚŻŹĆÓ][\w-]+)?)"), "gm."),
]
# "„<title>” w gminie <name>"
_AFTER_TITLE = re.compile(r"^[”\"]\s+w\s+gminie\s+([A-ZŁŚŻŹĆÓ][\w-]+(?:\s+[A-ZŁŚŻŹĆÓ][\w-]+)?)")
_SPEECH = re.compile(r"\b(?:powiedział|podkreślił|dodał|zaznaczył|zadeklarował|poinformował)\w*", re.IGNORECASE)
_IMPLEMENTED = re.compile(r"[^.\n]*\b(?:wdrożył\w*|zrealizowan\w* projekt\w*)[^.\n]*\.")
# List item: "- I miejsce: Powiat Poznański (Aromatorium – biblioteka zapachów ...),"
_LIST_ITEM = re.compile(r"^-\s*([IV]+)\s+miejsce:\s*([^(\n]{3,80}?)\s*\(([^\n]{5,300})\)[,.;]?\s*$", re.MULTILINE)


def _sources() -> list[dict]:
    with SOURCES_CSV.open(encoding="utf-8") as f:
        return [row for row in csv.DictReader(f) if row["category"] == "competition_results"]


class _Fetcher:
    """Read pages with a cache. Obey robots.txt and the Crawl-delay of each host."""

    def __init__(self, client: httpx.Client):
        self.client = client
        self.robots: dict[str, Protego] = {}
        self.last: dict[str, float] = {}

    def get(self, url: str) -> str:
        CACHE.mkdir(parents=True, exist_ok=True)
        path = CACHE / (re.sub(r"[^\w]+", "_", url)[-150:] + ".html")
        if path.exists() and datetime.fromtimestamp(path.stat().st_mtime) > datetime.now() - timedelta(days=CACHE_DAYS):
            return path.read_text(encoding="utf-8")
        host = urlparse(url).netloc
        if host not in self.robots:
            response = self.client.get(f"https://{host}/robots.txt")
            self.robots[host] = Protego.parse(response.text if response.status_code == 200 else "")
        robots = self.robots[host]
        if not robots.can_fetch(url, USER_AGENT):
            raise PermissionError(f"robots.txt forbids {url}")
        pause = max(MIN_PAUSE, robots.crawl_delay(USER_AGENT) or 0)
        wait = self.last.get(host, 0) + pause - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        response = self.client.get(url)
        self.last[host] = time.monotonic()
        response.raise_for_status()
        path.write_text(response.text, encoding="utf-8")
        return response.text


# Do not split a sentence after abbreviations such as "gm." or "pow.".
_SPLIT = re.compile(
    r"(?<=[.!?])(?<!\bgm\.)(?<!\bpow\.)(?<!\bwoj\.)(?<!\bim\.)(?<!\bul\.)(?<!\bnr\.)(?<!\bprof\.)(?<!\bdr\.)"
    r"\s+(?=[A-ZŁŚŻŹĆÓ„\"])"
)
_MONTHS = {"sty": 1, "lut": 2, "mar": 3, "mrz": 3, "kw": 4, "mj": 5, "maj": 5, "cz": 6, "lip": 7, "sie": 8,
           "wrz": 9, "pa": 10, "lis": 11, "gru": 12}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(text) if s.strip()]


def _page_date(html: str) -> date | None:
    """Read the date of the article from the page, for example 'class="date">Pt., 29 Mj. 2026'.

    The automatic date of trafilatura is not correct for this site.
    """
    m = re.search(r'class="date">[^,<]*,\s*(\d{1,2})\s+([^\s.<]+)\.?\s+(\d{4})', html)
    if not m:
        return None
    word = m.group(2).lower()
    month = next((n for prefix, n in sorted(_MONTHS.items(), key=lambda x: -len(x[0])) if word.startswith(prefix)), None)
    return date(int(m.group(3)), month, int(m.group(1))) if month else None


def _adjective(word: str, ending: str) -> str:
    """Change the case of a Polish adjective: "łódzkiego" -> "łódzkie", "krotoszyńskiemu" -> "krotoszyński"."""
    word = word.lower()
    return re.sub(r"(?:iego|iemu|im|ie|i|ego|emu|y)$", "", word) + ending


def institution_name(who: str) -> tuple[str, str | None]:
    """Return the name of the JST in the nominative case and its voivodeship, if the name shows it."""
    who = re.sub(r"\s+", " ", who).strip(" ,.–-")
    m = re.match(r"(?i)^(?:woj\.|województw\w*)\s+(.+)$", who)
    if m:
        adjective = _adjective(m.group(1).split()[0], "ie")
        return f"Województwo {adjective}", _voivodeship(adjective)
    m = re.match(r"(?i)^(?:pow\.|powiat\w*)\s+(.+)$", who)
    if m:
        return f"Powiat {_adjective(m.group(1).split()[0], 'i')}", None
    m = re.match(r"(?i)^(?:gm\.|gmin\w*)\s+(.+)$", who)
    if m:
        return f"Gmina {m.group(1)}", None
    # A city in the dative case: "Grodziskowi Mazowieckiemu" -> "Grodzisk Mazowiecki".
    words = [re.sub(r"owi$", "", re.sub(r"iemu$", "i", w)) for w in who.split()]
    return " ".join(words), None


def _voivodeship(text: str) -> str | None:
    word = text.lower()
    for stem, name in VOIVODESHIPS.items():
        if re.search(rf"\b{stem}", word):
            return name
    return None


def _voivodeship_in(title: str) -> str | None:
    m = re.search(r"[Ww]ojewództw\w*\s+([a-ząćęłńóśźżA-ZŁŚŻŹĆÓ-]+)", title)
    return _voivodeship(m.group(1)) if m else None


def _laureates(body: str) -> list[tuple[str, str, str, str]]:
    """Return (laureate, title, text of the item, sentence) for each awarded project in the text."""
    found = []
    for m in _LIST_ITEM.finditer(body):
        line = m.group(0).strip()
        found.append((m.group(2).strip(), m.group(3).strip(), line, line))
    for sentence in _sentences(body):
        if _SPEECH.search(sentence):
            continue
        items = list(_FOR_PROJECT.finditer(sentence))
        for m in items:
            who = _SEPARATORS.sub("", m.group(1)).strip()
            if who and len(who.split()) <= 4:
                found.append((who, m.group(2).strip(), sentence if len(items) == 1 else m.group(0).strip(), sentence))
        if items:
            continue
        q = _QUOTE.search(sentence)
        if not q:
            continue
        after = _AFTER_TITLE.search(sentence[q.end() - 1 :])
        if after:
            found.append((f"gm. {after.group(1)}", q.group(1).strip(), sentence, sentence))
            continue
        for pattern, prefix in _IN_TITLE:
            t = pattern.search(q.group(1))
            if t:
                found.append((f"{prefix} {t.group(1)}", q.group(1).strip(), sentence, sentence))
                break
    return found


def parse_innowacyjny_samorzad(html: str, url: str, retrieved: date) -> list[Innovation]:
    """Return one card for each laureate project of one edition of "Innowacyjny Samorząd"."""
    text = trafilatura.extract(html, favor_recall=True) or ""
    published = _page_date(html)
    text = text.replace("\xa0", " ")
    _, _, body = text.partition("Laureaci")
    # A page with a list of places can have the word "Laureaci" in a later heading: read the full text.
    if not body or _LIST_ITEM.search(text):
        body = text
    implemented = _IMPLEMENTED.search(text)
    edition = re.search(r"\b([IVX]+)\s+edycj", text)

    records = []
    sentences = _sentences(body)
    for who, title, item, sentence in _laureates(body):
        name, voivodeship = institution_name(who)
        voivodeship = voivodeship or _voivodeship_in(title)
        # For a main laureate, the next sentences without a new title describe the same project.
        extra = []
        if item in sentences:
            i = sentences.index(item)
            for nxt in sentences[i + 1 : i + 3]:
                if _QUOTE.search(nxt) or _SPEECH.search(nxt):
                    break
                extra.append(nxt)
        description = " ".join([item, *extra])
        if implemented:
            description += " Opis konkursu: " + implemented.group().strip()
        award = "Wyróżnienie" if re.search(r"wyróżn", sentence, re.IGNORECASE) else "Nagroda"

        def estimate(value, reason, evidence=None):
            return FieldValue(value=value, kind="estimate", source_url=url, evidence=evidence, reason=reason)

        level = (
            FieldValue(value=5, kind="fact", source_url=url, evidence=implemented.group().strip())
            if implemented
            else estimate(4, "Laureat konkursu dla JST; źródło nie mówi wprost o wdrożeniu.")
        )
        novelty = estimate_novelty(description, url)
        if novelty["value"] is None:
            novelty = estimate(2, "Projekt nagrodzony w konkursie ogólnopolskim; źródło nie podaje zasięgu nowości.")
        fields = dict(  # noqa: C408
            id="insam-" + re.sub(r"[^a-z0-9]+", "-", f"{published.year if published else ''} {title}".lower())[:70].strip("-"),
            title=title,
            summary=FieldValue(value=item, kind="fact", source_url=url, evidence=item),
            description=description,
            area=estimate("administrative", "Konkurs „Innowacyjny Samorząd” nagradza rozwiązania jednostek samorządu."),
            type=FieldValue(value="projekt JST nagrodzony w konkursie", kind="fact", source_url=url),
            institution=Institution(name=name, kind="jst", voivodeship=voivodeship),
            implementation_level=level,
            trl=None,
            novelty=FieldValue.model_validate(novelty),
            application_potential=estimate(None, "Źródło nie podaje kosztu ani dokumentacji dla innych JST."),
            credibility=FieldValue(
                value=5 if implemented else 4,
                kind="fact",
                source_url=url,
                evidence=implemented.group().strip() if implemented else None,
            ),
        )
        assessment = assess({k: v.model_dump() if isinstance(v, FieldValue) else v for k, v in fields.items()})
        records.append(
            Innovation(
                **fields,
                assessment=assessment,
                sources=[
                    Source(
                        name="Konkurs „Innowacyjny Samorząd” (Serwis Samorządowy PAP), wartowiedziec.pl",
                        url=url,
                        data_date=published,
                        retrieved=retrieved,
                        license=LICENSE,
                    )
                ],
                timeline=[
                    TimelineEvent(
                        date=published,
                        event="award",
                        label=f"{award} w konkursie „Innowacyjny Samorząd”"
                        + (f" ({edition.group(1)} edycja)" if edition else ""),
                        source_url=url,
                    )
                ]
                if published
                else [],
            )
        )
    return records


PARSERS = {"innowacyjny_samorzad": parse_innowacyjny_samorzad}


def load(voivodeships: list[str] | None = None, client: httpx.Client | None = None) -> SourceData:
    """Return the cards of all result pages. A voivodeship filter keeps also cards without a known voivodeship."""
    retrieved = date.today()
    data = SourceData(name=NAME, url=str(SOURCES_CSV.relative_to(ROOT)), license=LICENSE, retrieved=retrieved)
    own_client = client is None
    client = client or httpx.Client(timeout=60, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    fetcher = _Fetcher(client)
    seen = set()
    for row in _sources():
        parser = PARSERS.get(row["strategy"])
        if parser is None:
            data.errors.append(f"{row['id']}: no parser {row['strategy']!r}")
            continue
        try:
            records = parser(fetcher.get(row["url"]), row["url"], retrieved)
        except (httpx.HTTPError, PermissionError, ValueError) as error:
            data.errors.append(f"{row['id']}: {error}")
            continue
        for record in records:
            if voivodeships and record.institution.voivodeship not in (None, *voivodeships):
                continue
            if record.id not in seen:
                seen.add(record.id)
                data.records.append(record)
                d = record.sources[0].data_date
                if d and (data.data_date is None or d > data.data_date):
                    data.data_date = d
    if own_client:
        client.close()
    return data
