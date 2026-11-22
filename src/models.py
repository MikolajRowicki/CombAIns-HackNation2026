"""Data contract of the application: the innovation record and the API responses.

The backend, the tests and the web page use these models. Codes are in English.
LABELS has the Polish labels of the codes. The criteria are in src/criteria.py (GET /api/criteria).
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["fact", "estimate"]
Area = Literal["technological", "educational", "administrative"]
InstitutionKind = Literal["jst", "school", "university", "company", "other"]
Confidence = Literal["high", "medium", "low"]
EventType = Literal["grant", "patent", "award", "media", "implementation"]
UserGroup = Literal["investors", "public", "science", "schools", "startups", "innovators"]


class FieldValue(BaseModel):
    """One value on the card. A fact has a source. An estimate has a reason."""

    value: str | int | None
    kind: Kind
    source_url: str | None = None
    evidence: str | None = Field(None, description="Short quote from the source text.")
    reason: str | None = Field(None, description="Only for an estimate: why the value was proposed.")


class Institution(BaseModel):
    name: str
    kind: InstitutionKind
    city: str | None = None
    voivodeship: str | None = Field(None, description="Lowercase Polish name, for example 'podkarpackie'.")


class CriterionScore(BaseModel):
    """One criterion of the assessment, as src/criteria.py calculates it."""

    value: int | float | None = Field(description="Value on the scale of the criterion (TRL 1-9 for K2).")
    score: int | float | None = Field(description="Value on the common scale 0-5.")
    weight: float = Field(description="Weight after the change for a TRL that does not apply.")
    points: float | None
    kind: Kind | None
    applicable: bool


class Assessment(BaseModel):
    """Output of src.criteria.assess()."""

    potential: int | None = Field(ge=0, le=100, description="None if no criterion is known.")
    low: int = Field(ge=0, le=100)
    high: int = Field(ge=0, le=100)
    confidence: Confidence
    fact_share: int = Field(ge=0, le=100, description="Share of the weight with facts, in percent.")
    criteria_version: str
    criteria: dict[str, CriterionScore]
    missing: list[str] = []


class Source(BaseModel):
    name: str
    url: str
    data_date: date | None = None
    retrieved: date
    license: str


class TimelineEvent(BaseModel):
    date: date
    event: EventType
    label: str
    source_url: str


class DemandSignal(BaseModel):
    buyer: str
    date: date
    subject: str
    url: str


class Innovation(BaseModel):
    id: str
    title: str
    summary: FieldValue
    description: str = Field(description="Text from the source: the base for all quotes.")
    area: FieldValue
    type: FieldValue
    institution: Institution
    implementation_level: FieldValue
    trl: FieldValue | None = Field(None, description="None if TRL does not apply.")
    novelty: FieldValue
    application_potential: FieldValue
    credibility: FieldValue
    assessment: Assessment
    sources: list[Source] = Field(min_length=1)
    timeline: list[TimelineEvent] = []
    demand: list[DemandSignal] = []
    keywords: list[str] = []


class SearchResult(BaseModel):
    id: str
    title: str
    summary: FieldValue
    area: FieldValue
    institution: Institution
    implementation_level: FieldValue
    potential: int | None
    confidence: Confidence
    relevance: float = Field(ge=0, le=1)
    rank_score: float = Field(description="0.7 * relevance + 0.3 * potential / 100")


class SearchResponse(BaseModel):
    total: int
    results: list[SearchResult]


class InnovationDetail(Innovation):
    similar: list[SearchResult] = []


class SourceStatus(BaseModel):
    name: str
    records: int
    last_check: date | None = None
    error: str | None = None


LABELS: dict[str, dict[str, str]] = {
    "area": {
        "technological": "technologiczny",
        "educational": "edukacyjny",
        "administrative": "administracyjny",
    },
    "implementation_level": {
        "1": "koncepcja",
        "2": "prototyp",
        "3": "testy",
        "4": "wdrożenie pilotażowe",
        "5": "stosowane w praktyce",
    },
    "institution_kind": {
        "jst": "jednostka samorządu terytorialnego",
        "school": "szkoła lub placówka edukacyjna",
        "university": "uczelnia lub jednostka naukowa",
        "company": "przedsiębiorstwo",
        "other": "inna instytucja",
    },
    "kind": {"fact": "fakt", "estimate": "szacunek"},
    "confidence": {"high": "wysoka", "medium": "średnia", "low": "niska"},
    "event": {
        "grant": "dofinansowanie",
        "patent": "patent",
        "award": "nagroda",
        "media": "publikacja w mediach",
        "implementation": "wdrożenie",
    },
    "user_group": {
        "investors": "inwestorzy i podmioty komercyjne",
        "public": "instytucje publiczne i samorządy",
        "science": "uczelnie i jednostki naukowe",
        "schools": "szkoły i placówki edukacyjne",
        "startups": "startupy i przedsiębiorstwa",
        "innovators": "indywidualni innowatorzy i wynalazcy",
    },
    "voivodeship": {
        v: v
        for v in [
            "dolnośląskie", "kujawsko-pomorskie", "lubelskie", "lubuskie", "łódzkie",
            "małopolskie", "mazowieckie", "opolskie", "podkarpackie", "podlaskie",
            "pomorskie", "śląskie", "świętokrzyskie", "warmińsko-mazurskie",
            "wielkopolskie", "zachodniopomorskie",
        ]
    },
}
