"""European patents granted to Polish applicants (EPO Linked Open Data, SPARQL, CC BY 4.0, no key).

The SPARQL endpoint is https://data.epo.org/linked-data/query (robots.txt allows it).
The loader takes granted patents (kind B1) with an applicant address in Poland. The data has no city, so the card
has no voivodeship. Applicants that are natural persons ("KOWALSKI, Jan") are not used. The titles are in
English, German and French; the card uses the English title and Polish keywords of the IPC section.
"""

import re
from collections import defaultdict
from datetime import date, timedelta

import httpx

from src.criteria import assess
from src.models import FieldValue, Innovation, Institution, Source, TimelineEvent
from src.sources import USER_AGENT, SourceData, fe_projects

ENDPOINT = "https://data.epo.org/linked-data/query"
NAME = "EPO: patenty europejskie polskich zgłaszających (Linked Open Data)"
LICENSE = "CC BY 4.0 (European Patent Office, Linked Open EP data)"
YEARS = 5

QUERY = """
PREFIX patent: <http://data.epo.org/linked-data/def/patent/>
PREFIX vcard: <http://www.w3.org/2006/vcard/ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?pub ?number ?date ?name ?title ?filing ?ipc WHERE {
  ?adr patent:countryCode "PL" .
  ?vc vcard:hasAddress ?adr ; vcard:fn ?name ; patent:vcApplicantOf ?pub .
  ?pub patent:publicationKind <http://data.epo.org/linked-data/def/patent/publicationKind_B1> ;
       patent:publicationDate ?date ; patent:publicationNumber ?number ; patent:titleOfInvention ?title .
  OPTIONAL { ?pub patent:application ?app . ?app patent:filingDate ?filing }
  OPTIONAL { ?pub patent:classificationIPCInventive ?ipc }
  FILTER(?date >= "%s"^^xsd:date)
}
"""

# Sections of the International Patent Classification, in Polish, as keywords for the Polish search.
IPC_SECTIONS = {
    "A": "medycyna, rolnictwo, żywność, artykuły codziennego użytku",
    "B": "procesy przemysłowe, obróbka, transport",
    "C": "chemia, metalurgia, materiały",
    "D": "włókiennictwo, papier",
    "E": "budownictwo, górnictwo",
    "F": "mechanika, silniki, oświetlenie, ogrzewanie",
    "G": "fizyka, pomiary, informatyka",
    "H": "elektrotechnika, energetyka, elektronika",
}
_ENGLISH = re.compile(r"\b(?:AND|FOR|OF|THE|WITH|METHOD|DEVICE|USE|APPARATUS|AN?|IN|ON|FROM)\b")
_OTHER = re.compile(r"\b(?:UND|MIT|FÜR|DER|DIE|DAS|VON|ZUR|ZUM|EINE?R?|ET|DE|LA|LE|DES|DU|POUR|UNE?|AVEC)\b|[ÄÖÜÉÈÀ]")
_COMPANY = re.compile(
    r"sp\.?\s*z\.?\s*o\.?\s*o|z\.\s*o\.\s*o|sp[oó][lł]ka|akcyjna|\bs\.?\s*a\.?$|\bsa\b|sp\.\s*k\.|s\.c\.|gmbh|\bltd\b|\binc\b",
    re.IGNORECASE,
)
_UNIVERSITY = re.compile(r"politechnik|uniwersytet|akademi|instytut|universit|institut|łukasiewicz|lukasiewicz", re.IGNORECASE)


_INSTITUTION = re.compile(
    r"centrum|center|muzeum|museum|stowarzysz|fundacj|narodow|polsk|sieć|siec|zakład|zaklad|przedsiębiorstw"
    r"|przedsiebiorstw|szpital|hospital|izba|park|klaster",
    re.IGNORECASE,
)


def is_person(name: str) -> bool:
    """Return False only for a clear institution: a legal form of a company, a university or an institution word.

    EPO writes a natural person as "SURNAME, First name", and many sole traders have a first name and a surname
    in the name ("Stalpa Stanislaw Pargiela"), often without Polish letters. Thus the rule keeps only clear
    institutions: a few companies go out, but no person comes in (AGENTS.md, personal data).
    """
    if _UNIVERSITY.search(name) or _COMPANY.search(name):
        return fe_projects.person_name(name) is not None and not _COMPANY.search(name)
    if _INSTITUTION.search(name) and "," not in name:
        return fe_projects.person_name(name) is not None
    return True


def english(titles: set[str]) -> str:
    """Return the title with the most English function words and the fewest German or French ones."""
    return max(sorted(titles), key=lambda t: len(_ENGLISH.findall(t.upper())) - 2 * len(_OTHER.findall(t.upper())))


def institution_kind(name: str) -> str:
    if _UNIVERSITY.search(name):
        return "university"
    return "company" if _COMPANY.search(name) else "other"


def to_innovation(number: str, rows: list[dict], retrieved: date) -> Innovation | None:
    names = {re.sub(r"\s+", " ", r["name"]).strip() for r in rows}
    applicants = sorted(n for n in names if not is_person(n))
    if not applicants:
        return None
    url = f"https://data.epo.org/publication-server/document?pn={number}&ki=B1"
    title = english({r["title"] for r in rows})
    granted = date.fromisoformat(rows[0]["date"][:10])
    filings = sorted({r["filing"][:10] for r in rows if r.get("filing")})
    ipcs = sorted({r["ipc"].rsplit("/", 1)[-1] for r in rows if r.get("ipc")})
    sections = sorted({i[0] for i in ipcs if i[:1] in IPC_SECTIONS})
    keywords = [IPC_SECTIONS[s] for s in sections] + [f"IPC {i.replace('-', '/')}" for i in ipcs[:3]]
    description = f"{title}. Patent europejski EP {number} B1 udzielony {granted:%d.%m.%Y}."

    def estimate(value, reason):
        return FieldValue(value=value, kind="estimate", source_url=url, reason=reason)

    fields = {
        "id": f"epo-{number}",
        "title": title,
        "summary": FieldValue(value=title, kind="fact", source_url=url, evidence=title),
        "description": description,
        "area": estimate("technological", "Patent europejski: rozwiązanie techniczne."),
        "type": FieldValue(value="patent europejski", kind="fact", source_url=url),
        "institution": Institution(name=applicants[0], kind=institution_kind(applicants[0])),
        "implementation_level": estimate(
            2, "Patent potwierdza opis działającego rozwiązania. Źródło nie podaje informacji o wdrożeniu."
        ),
        "trl": estimate(4, "Wynalazek opisany do poziomu, który pozwala go wykonać; brak danych o testach poza laboratorium."),
        "novelty": estimate(4, "Europejski Urząd Patentowy udzielił patentu: nowość w skali co najmniej europejskiej."),
        "application_potential": estimate(None, "Źródło nie podaje danych o zastosowaniu w innych instytucjach."),
        "credibility": FieldValue(value=3, kind="fact", source_url=url),
        "keywords": keywords,
    }
    timeline = []
    if filings:
        timeline.append(
            TimelineEvent(date=date.fromisoformat(filings[0]), event="patent", label="Zgłoszenie w EPO", source_url=url)
        )
    timeline.append(TimelineEvent(date=granted, event="patent", label=f"Patent europejski EP {number} B1", source_url=url))
    plain = {k: v.model_dump() if isinstance(v, FieldValue) else v for k, v in fields.items()}
    return Innovation(
        **fields,
        assessment=assess(plain),
        sources=[Source(name=NAME, url=url, data_date=None, retrieved=retrieved, license=LICENSE)],
        timeline=timeline,
    )


def load(voivodeships: list[str] | None = None, client: httpx.Client | None = None) -> SourceData:
    """Return the patents of the last YEARS years. The data has no city, so the voivodeship filter does not apply."""
    retrieved = date.today()
    data = SourceData(name=NAME, url=ENDPOINT, license=LICENSE, retrieved=retrieved)
    own_client = client is None
    client = client or httpx.Client(timeout=180, headers={"User-Agent": USER_AGENT})
    since = retrieved - timedelta(days=365 * YEARS)
    try:
        response = client.post(
            ENDPOINT,
            data={"query": QUERY % since.isoformat()},
            headers={"Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()
        bindings = response.json()["results"]["bindings"]
    except (httpx.HTTPError, ValueError, KeyError) as error:
        data.errors.append(f"SPARQL: {error}")
        bindings = []
    finally:
        if own_client:
            client.close()
    groups: dict[str, list[dict]] = defaultdict(list)
    for b in bindings:
        groups[b["number"]["value"]].append({k: v["value"] for k, v in b.items()})
    for number, rows in sorted(groups.items()):
        card = to_innovation(number, rows, retrieved)
        if card:
            data.records.append(card)
            if data.data_date is None or card.timeline[-1].date > data.data_date:
                data.data_date = card.timeline[-1].date
    return data
