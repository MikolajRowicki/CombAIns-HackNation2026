"""Where an innovation can be used and by whom: sectors, user groups, similar institutions and the next path.

Task section 6, points d and e: potential recipients, paths and the measures of effectiveness.
All results are estimates of rules. Each result has its reason. The rules do not use AI.
"""

import re

from src.criteria import CRITERIA, _evidence
from src.models import (
    LABELS,
    Adopter,
    Applications,
    Audience,
    Innovation,
    Path,
    SearchResult,
    Sector,
)

APPLICATIONS_VERSION = "v0.1"

_INTERREG = "Interreg Europe, kryteria dobrej praktyki (potencjał przeniesienia do innych regionów)"
_NESTA = "Nesta, Standards of Evidence; Nesta, Making it big (skalowanie innowacji społecznych)"
_OPSI = "OECD OPSI, dyfuzja innowacji w sektorze publicznym (przejęcie przez drugą organizację)"
_TTO = "PCI, karta oceny projektów B+R (walidacja z odbiorcą technologii); praktyka centrów transferu technologii"

# Sector: (label, Polish stems, typical recipients). The stems find the sector in the text of the source.
SECTORS = [
    ("ochrona zdrowia", r"medycz|rehabilit|leczeni|pacjent|szpital|terapi|diagnost|farmac|chorob|chirurg|klinicz|niepełnospraw", "szpitale, przychodnie, ośrodki rehabilitacji, firmy medyczne"),
    ("lotnictwo i kosmonautyka", r"lotnic|lotnisk|samolot|śmigłow|dron|bezzałog|kosmi|satelit|statk\w* powietrz|ruch\w* powietrz|antykoliz|pilot(?:a|ów|em)?\b", "przemysł lotniczy, operatorzy dronów, ośrodki szkolenia lotniczego"),
    ("transport i motoryzacja", r"pojazd|samochod|motoryzac|transport|kolejow|kolei\b|tramwaj|autobus|przystan", "producenci pojazdów i części, przewoźnicy, zarządcy transportu publicznego"),
    ("budownictwo i infrastruktura", r"budowl|budynk|beton|most|przęsł|konstrukcj\w* nośn|izolac|drogow", "firmy budowlane, zarządcy dróg i budynków publicznych"),
    ("energetyka i efektywność energetyczna", r"energ|fotowolta|kolektor\w* słoneczn|ciepł|wodór|wodor|bateri|akumulat|turbin", "firmy energetyczne, JST, spółdzielnie i wspólnoty mieszkaniowe"),
    ("rolnictwo i przetwórstwo spożywcze", r"rolni|upraw|roślin|żywnoś|spożyw|mlecz|mięs|pasz|wypiek|piekar|biszkopt", "gospodarstwa rolne, zakłady przetwórstwa spożywczego"),
    ("ochrona środowiska i gospodarka komunalna", r"ściek|odpad|recykl|uzdatn|jakoś\w* powietrza|smog|emisj|zanieczyszcz|powodz|przeciwpowodz", "JST, przedsiębiorstwa komunalne, zakłady przemysłowe"),
    ("materiały i chemia", r"kompozyt|polimer|stop\w* metal|powłok|lakier|chemiczn|katalizat|nanocz", "zakłady produkcyjne, przemysł chemiczny i materiałowy"),
    ("przemysł maszynowy i produkcja", r"maszyn|narzędzi|obróbk|spawan|frezow|produkcj\w* seryjn|automatyzac", "zakłady produkcyjne, producenci maszyn"),
    ("ICT i cyfryzacja", r"oprogramow|aplikacj|algorytm|sztuczn\w* inteligenc|cyfrow|internet|e-usług|platform\w* (?:cyfrow|internet|onlin)", "firmy IT, instytucje, które cyfryzują usługi"),
    ("administracja publiczna", r"urząd\b|urzęd(?:u|zie|em|y|ów|ach|ami|nik)|mieszkańc|samorząd|gmin|e-usług|administracj", "gminy, powiaty, urzędy marszałkowskie, instytucje publiczne"),
    ("edukacja", r"szkoł|uczni|nauczyc|dydakty|kształceni|edukac|przedszkol|student", "szkoły, przedszkola, uczelnie, placówki doskonalenia nauczycieli"),
]

_MAX_SECTORS = 3
_MAX_ADOPTERS = 5


def find_sectors(innovation: Innovation) -> list[Sector]:
    text = f"{innovation.title}\n{innovation.description}"
    found = []
    for label, stems, recipients in SECTORS:
        matches = list(re.finditer(rf"\b(?:{stems})\w*", text, re.IGNORECASE))
        if not matches:
            continue
        first = matches[0]
        found.append(
            (
                len(matches),
                Sector(
                    label=label,
                    recipients=recipients,
                    evidence=_evidence(text, first.start(), first.end()),
                    reason=f"Tekst źródła zawiera „{first.group()}” ({len(matches)} wystąpień słów z tej dziedziny).",
                ),
            )
        )
    found.sort(key=lambda f: -f[0])
    return [sector for _, sector in found[:_MAX_SECTORS]]


def find_audiences(innovation: Innovation, sectors: list[Sector]) -> list[Audience]:
    """Return the user groups of the FAQ (section 3) that can use the innovation."""
    area = innovation.area.value
    level = innovation.implementation_level.value or 0
    labels = {s.label for s in sectors}
    groups: dict[str, str] = {}
    if area == "technological":
        groups["investors"] = "Rozwiązanie techniczne, które firma może wdrożyć lub licencjonować."
        if level <= 3:
            groups["startups"] = "Wczesny etap rozwoju: miejsce na spółkę lub start-up, który rozwinie rozwiązanie."
    if area == "administrative" or "administracja publiczna" in labels:
        groups["public"] = "Rozwiązanie dla urzędów i samorządów; inne JST mogą je powtórzyć."
    if area == "educational" or "edukacja" in labels:
        groups["schools"] = "Rozwiązanie dla szkół i placówek edukacyjnych."
    if innovation.institution.kind == "university" or level <= 2:
        groups["science"] = "Uczelnie i instytuty mogą rozwijać rozwiązanie we wspólnych projektach B+R."
    return [Audience(group=g, label=LABELS["user_group"][g], reason=r) for g, r in groups.items()]


def find_adopters(innovation: Innovation, similar: list[SearchResult]) -> list[Adopter]:
    """Return other institutions with similar innovations: candidates for partners or for the next adoption."""
    seen = {innovation.institution.name}
    adopters = []
    for result in similar:
        name = result.institution.name
        if name in seen:
            continue
        seen.add(name)
        adopters.append(
            Adopter(
                name=name,
                kind=result.institution.kind,
                voivodeship=result.institution.voivodeship,
                innovation_id=result.id,
                innovation_title=result.title,
                relevance=result.relevance,
            )
        )
        if len(adopters) >= _MAX_ADOPTERS:
            break
    return adopters


def _paths(innovation: Innovation) -> list[Path]:
    area = innovation.area.value
    level = innovation.implementation_level.value
    trl = innovation.trl.value if innovation.trl else None
    kind = innovation.institution.kind
    a = innovation.assessment
    level_text = f"poziom wdrożenia {level}/5" if level else "poziom wdrożenia nieznany"
    paths = []

    if area == "technological" and level is not None and level <= 3:
        paths.append(
            Path(
                id="P1",
                name="Transfer technologii: licencja lub wspólny projekt B+R z firmą",
                reason=f"Obszar technologiczny, {level_text} (≤ 3)"
                + (", twórcą jest uczelnia lub instytut." if kind == "university" else "."),
                measures=[
                    "liczba zapytań od firm po publikacji karty",
                    "umowa licencyjna lub umowa B+R w ciągu 12 miesięcy",
                    "wzrost TRL o co najmniej 1 poziom",
                ],
                reference=_TTO,
            )
        )
    if area == "technological" and ((level or 0) >= 4 or (trl or 0) >= 6):
        paths.append(
            Path(
                id="P2",
                name="Wdrożenie rynkowe u kolejnych odbiorców",
                reason=f"Obszar technologiczny, {level_text}" + (f", TRL {trl}" if trl else "") + ": rozwiązanie jest gotowe do użycia.",
                measures=[
                    "liczba nowych odbiorców w ciągu 12 miesięcy",
                    "przychód lub oszczędność u odbiorcy",
                    "zmiana poziomu wdrożenia na 5 (stosowane w praktyce)",
                ],
                reference=_TTO,
            )
        )
    if area in ("administrative", "educational") and (level or 0) >= 4:
        paths.append(
            Path(
                id="P3",
                name="Replikacja w innej instytucji",
                reason=f"Obszar {LABELS['area'][area]}, {level_text} (≥ 4): rozwiązanie działa i może je powtórzyć inna instytucja.",
                measures=[
                    "liczba instytucji, które przejęły rozwiązanie w ciągu 12 miesięcy",
                    "liczba użytkowników (mieszkańców, uczniów) w nowych miejscach",
                    "efekt w nowym miejscu, np. czas obsługi sprawy lub wyniki uczniów",
                ],
                reference=f"{_OPSI}; {_INTERREG}",
            )
        )
    if area in ("administrative", "educational") and (level or 0) <= 3:
        paths.append(
            Path(
                id="P4",
                name="Pilotaż z ewaluacją",
                reason=f"Obszar {LABELS['area'][area]}, {level_text} (≤ 3): przed przeniesieniem trzeba sprawdzić efekt.",
                measures=[
                    "pilotaż rozpoczęty w 1–2 instytucjach",
                    "zmierzony stan przed pilotażem i po pilotażu",
                    "raport z ewaluacji (poziom 2–3 skali Nesta)",
                ],
                reference=_NESTA,
            )
        )
    if a.missing or a.confidence == "low":
        missing = ", ".join(CRITERIA[c]["name"].lower() for c in a.missing) if a.missing else "dane potwierdzone"
        paths.append(
            Path(
                id="P5",
                name="Uzupełnienie danych i ponowna ocena",
                reason=f"Pewność oceny: {LABELS['confidence'][a.confidence]}; brakuje: {missing}.",
                measures=[
                    "liczba kryteriów z danymi ze źródła zamiast wartości przybliżonych",
                    "ponowna ocena po aktualizacji źródeł (do 6 miesięcy)",
                ],
                reference=_NESTA,
            )
        )
    return paths


def recommend(innovation: Innovation, similar: list[SearchResult]) -> Applications:
    sectors = find_sectors(innovation)
    return Applications(
        version=APPLICATIONS_VERSION,
        sectors=sectors,
        audiences=find_audiences(innovation, sectors),
        adopters=find_adopters(innovation, similar),
        paths=_paths(innovation),
    )
