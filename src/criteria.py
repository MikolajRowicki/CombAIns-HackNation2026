"""Assessment criteria of Radar innowacji: names, scales, weights, references and rules.

The criteria come from the FAQ (section 5). The weights are a proposal of the team (docs/project.md, section 7).
The PCI mentors must calibrate the weights. Each assessment records CRITERIA_VERSION.
"""

import re

CRITERIA_VERSION = "v0.1"

KINDS = ("fact", "estimate")

_OSLO = {
    "label": "OECD/Eurostat, Oslo Manual 2018",
    "url": "https://doi.org/10.1787/9789264304604-en",
}
_TRL = {
    "label": "Komisja Europejska, Horyzont 2020, załącznik G: Technology Readiness Levels",
    "url": "https://ec.europa.eu/research/participants/data/ref/h2020/wp/2014_2015/annexes/h2020-wp1415-annex-g-trl_en.pdf",
}
_INTERREG = {
    "label": "Interreg Europe, kryteria dobrej praktyki",
    "url": "https://www.interregeurope.eu/help-centre/expert-support-services/good-practices",
}
_ROGERS = {
    "label": "Rogers, Diffusion of Innovations; przegląd atrybutów (PMC9338559)",
    "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9338559/",
}
_NESTA = {
    "label": "Nesta, Standards of Evidence",
    "url": "https://www.nesta.org.uk/feature/innovation-methods/standards-evidence/",
}

# The web page shows this dict. Thus all labels are in Polish.
CRITERIA = {
    "K1": {
        "field": "implementation_level",
        "name": "Poziom wdrożenia",
        "description": "Jak daleko rozwiązanie doszło od pomysłu do codziennego użycia.",
        "weight": 30,
        "min": 1,
        "max": 5,
        "scale": {
            1: "Koncepcja",
            2: "Prototyp",
            3: "Testy",
            4: "Wdrożenie pilotażowe",
            5: "Stosowane w praktyce",
        },
        "references": [_OSLO],
    },
    "K2": {
        "field": "trl",
        "name": "Dojrzałość technologiczna (TRL)",
        "description": (
            "Poziom gotowości technologii TRL 1–9, przeliczony na skalę 0–5. "
            "Nie dotyczy innowacji nietechnologicznych: wtedy waga przechodzi proporcjonalnie na inne kryteria."
        ),
        "weight": 15,
        "min": 1,
        "max": 9,
        "scale": {
            1: "TRL 1: zaobserwowano podstawowe zasady",
            2: "TRL 2: sformułowano koncepcję technologii",
            3: "TRL 3: eksperymentalny dowód koncepcji",
            4: "TRL 4: walidacja technologii w laboratorium",
            5: "TRL 5: walidacja technologii w środowisku zbliżonym do rzeczywistego",
            6: "TRL 6: demonstracja technologii w środowisku zbliżonym do rzeczywistego",
            7: "TRL 7: demonstracja prototypu w środowisku operacyjnym",
            8: "TRL 8: system kompletny i zakwalifikowany",
            9: "TRL 9: system sprawdzony w środowisku operacyjnym",
        },
        "score_map": "TRL 1–2 → 1, TRL 3–4 → 2, TRL 5–6 → 3, TRL 7–8 → 4, TRL 9 → 5",
        "references": [_TRL],
    },
    "K3": {
        "field": "novelty",
        "name": "Innowacyjność",
        "description": "Stopień nowości i ulepszenia w porównaniu z istniejącymi rozwiązaniami.",
        "weight": 20,
        "min": 1,
        "max": 5,
        "scale": {
            1: "Nowe w instytucji",
            2: "Nowe w regionie",
            3: "Nowe w Polsce",
            4: "Nowe w Europie",
            5: "Nowe na świecie",
        },
        "references": [_OSLO],
    },
    "K4": {
        "field": "application_potential",
        "name": "Potencjał zastosowania",
        "description": "Możliwość użycia w innych instytucjach, organizacjach lub sektorach: 1 punkt za każdy spełniony warunek.",
        "weight": 20,
        "min": 0,
        "max": 5,
        "items": [
            "Dokumentacja pozwala innym powtórzyć rozwiązanie",
            "Znany koszt wdrożenia",
            "Nie wymaga specjalnej infrastruktury",
            "Zastosowanie w więcej niż jednym sektorze",
            "Sygnały popytu: zakupy podobnych rozwiązań (BZP)",
        ],
        "scale": {
            0: "Żaden warunek nie jest spełniony",
            1: "1 z 5 warunków",
            2: "2 z 5 warunków",
            3: "3 z 5 warunków",
            4: "4 z 5 warunków",
            5: "Wszystkie 5 warunków",
        },
        "references": [_INTERREG, _ROGERS],
    },
    "K5": {
        "field": "credibility",
        "name": "Wiarygodność",
        "description": "Dokumentacja, potwierdzenia wdrożenia i wiarygodne źródła.",
        "weight": 15,
        "min": 0,
        "max": 5,
        "scale": {
            0: "Brak danych",
            1: "Deklaracja własna",
            2: "Opis z liczbami",
            3: "Jedno weryfikowalne źródło",
            4: "Dwa niezależne źródła",
            5: "Publiczne potwierdzenie wdrożenia",
        },
        "references": [_NESTA],
    },
}

# Thresholds for the share of the weight with facts (docs/project.md, section 7, rule 5).
CONFIDENCE_THRESHOLDS = {"high": 70, "medium": 40}

CONFIDENCE_LABELS = {"high": "wysoka", "medium": "średnia", "low": "niska"}


def trl_to_score(trl: int) -> int:
    """Change TRL 1-9 to the scale 0-5 (TRL 1-2 is 1, ..., TRL 9 is 5)."""
    return (trl + 1) // 2


def _round(x: float) -> int:
    # Python round() uses banker's rounding. A fixed half-up rule keeps the scores easy to check by hand.
    return int(x + 0.5)


def _read(cid: str, field) -> tuple:
    """Return (value, kind) of one criterion. The value None means unknown."""
    if field is None:
        return None, None
    value = field.get("value")
    if value is None:
        return None, None
    c = CRITERIA[cid]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{cid}: value {value!r} is not a number")
    if not c["min"] <= value <= c["max"]:
        raise ValueError(f"{cid}: value {value} is not in the range {c['min']}..{c['max']}")
    if cid == "K2" and value != int(value):
        raise ValueError(f"K2: TRL {value} is not an integer")
    kind = field.get("kind")
    if kind not in KINDS:
        raise ValueError(f"{cid}: kind {kind!r} is not one of {KINDS}")
    return value, kind


def assess(record: dict) -> dict:
    """Calculate the assessment of one innovation.

    The record has the keys implementation_level, trl, novelty, application_potential and credibility.
    Each value is {"value": number or None, "kind": "fact" | "estimate"} or None.
    A null value means unknown. For TRL, a null field (or no key) means "nie dotyczy" (contract of PR #24).
    Other keys are ignored. Thus a full Innovation record is also a correct input.
    """
    read = {cid: _read(cid, record.get(c["field"])) for cid, c in CRITERIA.items()}
    trl_applies = record.get("trl") is not None
    base_total = sum(c["weight"] for cid, c in CRITERIA.items() if cid != "K2" or trl_applies)

    criteria = {}
    known_points = known_weight = unknown_weight = fact_weight = 0.0
    for cid, c in CRITERIA.items():
        value, kind = read[cid]
        if cid == "K2" and not trl_applies:
            criteria[cid] = {
                "value": None,
                "score": None,
                "weight": 0,
                "points": None,
                "kind": None,
                "applicable": False,
            }
            continue
        weight = c["weight"] * 100 / base_total
        entry = {
            "value": value,
            "score": None,
            "weight": round(weight, 1),
            "points": None,
            "kind": kind,
            "applicable": True,
        }
        if value is None:
            unknown_weight += weight
        else:
            score = trl_to_score(int(value)) if cid == "K2" else value
            points = weight * score / 5
            entry.update(score=score, points=round(points, 1))
            known_points += points
            known_weight += weight
            if kind == "fact":
                fact_weight += weight
        criteria[cid] = entry

    # An unknown value is not 0: the range uses 0 for the low end and 5 for the high end (rule 4).
    # The point value uses only the known criteria, so it always lies inside the range.
    potential = _round(known_points * 100 / known_weight) if known_weight else None
    fact_share = _round(fact_weight)
    if fact_share >= CONFIDENCE_THRESHOLDS["high"]:
        confidence = "high"
    elif fact_share >= CONFIDENCE_THRESHOLDS["medium"]:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "potential": potential,
        "low": _round(known_points),
        "high": _round(known_points + unknown_weight),
        "confidence": confidence,
        "fact_share": fact_share,
        "criteria_version": CRITERIA_VERSION,
        "criteria": criteria,
        "missing": [cid for cid, e in criteria.items() if e["applicable"] and e["value"] is None],
    }


# Rules for estimates from text, without AI. Each rule is (level, Polish regular expression).
# The text of a source is Polish, so the patterns use Polish word stems.

# A plan or a future event is a concept, not an implementation. This rule runs first and
# removes the matched words, so "zostanie wdrożony" and "wdrożona zostanie" do not count as "wdrożony".
# The rule removes the rest of the clause, so "zostanie opracowana i wdrożona" counts as one plan.
_PLAN = (
    r"\b\w+\s+(?:zostanie|zostaną)\b[^.;!?\n]{0,120}|"
    r"\b(?:planuj\w*|planowan\w*|zaplanowan\w*|przewidzian\w*|zamierza\w*|zostanie|zostaną|będzie|będą|ma\s+zostać|mają\s+zostać"
    r"|ma\s+na\s+celu|mają\s+na\s+celu|celem\s+(?:\w+\s+){0,2}jest)"
    r"[^.;!?\n]{1,120}"
)

# A negation ("nie były stosowane") is no evidence of a level. This rule removes the words and gives no level.
_NEGATION = r"\bnie\s+(?:\w+\s+){0,2}?(?:stosowan|wdroż|uruchomi|funkcjonuj|testowan)\w*"

# Level 5 needs a statement about use, not only a word. Thus "laboratorium funkcjonującym w ramach"
# or "lek stosowany w leczeniu" (a description of a known method) do not count (test on RAD-on data).
_USED = r"stosowan(?:y|a|e|ą|ych|ymi)\b(?!\s+jako)"
_IN_USE = (
    r"\bwdrożon[oaey]\b(?!\s+(?:zostanie|zostaną|będzie|będą))|\bwdrożył\w*|\b" + _USED + r"\s+w\s+praktyce"
    r"|\b(?:jest|są|został\w*|zostały|już)\s+(?:już\s+|z\s+powodzeniem\s+)?"
    + _USED
    + r"|\bw\s+użyciu\b|\b(?:funkcjonuje|działa)\s+od\b|\buruchomion[oaey]\b"
    r"|\bwprowadzon\w*\s+do\s+(?:użytku|sprzedaży|oferty)"
    r"|\bdostępn\w*\s+dla\s+(?:mieszkańców|użytkowników|klientów|uczniów|pacjentów)"
)

_LEVEL_RULES = [
    (None, _NEGATION),
    (1, _PLAN),
    (4, r"\bwdroż\w*\s+pilotaż\w*|\bpilotaż\w*|\bpilotow(?:o|y|e|a|ego|ej|ym|ych|anie|ania|ano)\b"),
    (5, _IN_USE),
    (3, r"\bprzetestowan\w*|\btestowan\w*|\btest(?:y|ów|ach|ami|u|em)?\b|\bwalidacj\w*|\bwersj\w*\s+beta\b"),
    (2, r"\bprototyp\w*|\bdemonstrator\w*|\bmodel\w*\s+funkcjonaln\w*|\bmakiet\w*"),
    (1, r"\bkoncepcj\w*|\bpomysł\w*|\bstudi\w*\s+wykonalności\b"),
]

_SCOPE = r"(?:\w+\s+){0,2}"
_NOVELTY_RULES = [
    (
        5,
        (
            rf"\bpierwsz\w*\s+{_SCOPE}na\s+świecie|\bna\s+skalę\s+światową|\bw\s+skali\s+(?:świata|światowej)"
            r"|\bunikat\w*\s+na\s+świecie|\bświatow\w*\s+nowoś\w*|\bbez\s+odpowiednika\s+na\s+świecie"
        ),
    ),
    (
        4,
        (
            rf"\bpierwsz\w*\s+{_SCOPE}w\s+Europie|\bna\s+skalę\s+europejską|\bw\s+skali\s+(?:Europy|europejskiej)"
            r"|\bunikat\w*\s+w\s+Europie"
        ),
    ),
    (
        3,
        (
            rf"\b(?:pierwsz|jedyn)\w*\s+{_SCOPE}w\s+(?:Polsce|kraju)|\bna\s+skalę\s+(?:krajową|ogólnopolską)"
            r"|\bw\s+skali\s+kraju|\bnowoś\w*\s+na\s+(?:polskim\s+rynku|rynku\s+polskim)|\bunikat\w*\s+w\s+(?:Polsce|kraju)"
        ),
    ),
    (
        2,
        (
            rf"\b(?:pierwsz|jedyn)\w*\s+{_SCOPE}w\s+(?:regionie|województwie|powiecie|mieście|gminie)"
            r"|\bna\s+skalę\s+regionaln\w*|\bw\s+skali\s+(?:regionu|województwa)"
        ),
    ),
    (
        1,
        (
            r"\binnowacj\w*\s+pedagogiczn\w*"
            r"|\b(?:nowoś\w*|po\s+raz\s+pierwszy)\s+w\s+(?:naszej\s+|naszym\s+)?(?:szkole|urzędzie|uczelni|firmie|placówce)"
        ),
    ),
]

_MAX_EVIDENCE = 200


def _evidence(text: str, start: int, end: int) -> str:
    """Return the sentence around a match. The result is always an exact part of the text."""
    left = max(text.rfind(ch, 0, start) for ch in ".!?\n") + 1
    right = min((i for i in (text.find(ch, end) for ch in ".!?\n") if i != -1), default=len(text))
    if right - left > _MAX_EVIDENCE:
        left = max(left, start - 80)
        right = min(right, end + 80)
    return text[left:right].strip()


def _match_rules(text: str, rules: list) -> list:
    """Return the matches as (level, start, end). Each matched part of the text counts only once.

    A rule with the level None removes its words and gives no match.
    """
    work = text
    found = []
    for level, pattern in rules:
        if level is not None:
            found.extend((level, m.start(), m.end()) for m in re.finditer(pattern, work, re.IGNORECASE))
        work = re.sub(pattern, lambda m: " " * len(m.group()), work, flags=re.IGNORECASE)
    return found


def _estimate(cid: str, text: str, rules: list, source_url, empty_reason: str) -> dict:
    found = _match_rules(text or "", rules)
    if not found:
        return {"value": None, "kind": "estimate", "source_url": source_url, "evidence": None, "reason": empty_reason}
    level, start, end = max(found, key=lambda f: (f[0], -f[1]))
    label = CRITERIA[cid]["scale"][level]
    return {
        "value": level,
        "kind": "estimate",
        "source_url": source_url,
        "evidence": _evidence(text, start, end),
        "reason": f"Reguła słów kluczowych: tekst zawiera „{text[start:end]}”, co wskazuje poziom {level} ({label}).",
    }


def estimate_implementation_level(text: str, source_url: str | None = None) -> dict:
    """Propose K1 from Polish keywords in the text. The result is a FieldValue with kind "estimate"."""
    return _estimate("K1", text, _LEVEL_RULES, source_url, "Tekst nie zawiera słów kluczowych o poziomie wdrożenia.")


def estimate_novelty(text: str, source_url: str | None = None) -> dict:
    """Propose K3 from Polish keywords in the text. The result is a FieldValue with kind "estimate"."""
    return _estimate("K3", text, _NOVELTY_RULES, source_url, "Tekst nie zawiera informacji o zasięgu nowości.")


def estimate_application_potential(checks: dict[int, str | None], source_url: str | None = None) -> dict:
    """Propose K4 from the checks of its items (CRITERIA["K4"]["items"], index 0-4).

    checks maps the index of an item to a reason if the data shows the item, or to None if the data shows no
    sign of it. An item that is not in checks cannot be checked with the data: it does not count, and the
    reason says so. K4 is the number of items that the data shows. The result is a FieldValue with kind "estimate".
    """
    items = CRITERIA["K4"]["items"]
    met = [f"{items[i]} ({why})" for i, why in sorted(checks.items()) if why]
    unchecked = [items[i] for i in range(len(items)) if i not in checks]
    reason = "Spełnione: " + ("; ".join(met) if met else "żaden warunek") + "."
    if unchecked:
        reason += " Niesprawdzone (brak danych w źródłach): " + "; ".join(unchecked).lower() + "."
    return {"value": len(met), "kind": "estimate", "source_url": source_url, "evidence": None, "reason": reason}
