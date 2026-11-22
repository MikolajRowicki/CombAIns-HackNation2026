import json

import pytest

from src.criteria import (
    CRITERIA,
    CRITERIA_VERSION,
    assess,
    estimate_implementation_level,
    estimate_novelty,
    trl_to_score,
)


def fv(value, kind="fact"):
    return {"value": value, "kind": kind}


def test_criteria_definition_is_complete():
    assert sum(c["weight"] for c in CRITERIA.values()) == 100
    for c in CRITERIA.values():
        assert c["name"] and c["description"] and c["scale"]
        assert c["references"] and all(r["label"] for r in c["references"])
        assert set(range(c["min"], c["max"] + 1)) == set(c["scale"])
    json.dumps(CRITERIA)


@pytest.mark.parametrize("trl,score", [(1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (6, 3), (7, 4), (8, 4), (9, 5)])
def test_trl_to_score(trl, score):
    assert trl_to_score(trl) == score


def test_all_facts():
    a = assess(
        {
            "implementation_level": fv(5),
            "trl": fv(9),
            "novelty": fv(3),
            "application_potential": fv(4),
            "credibility": fv(5),
        }
    )
    # 30 + 15 + 20*3/5 + 20*4/5 + 15 = 88
    assert (a["potential"], a["low"], a["high"]) == (88, 88, 88)
    assert a["confidence"] == "high"
    assert a["criteria_version"] == CRITERIA_VERSION
    assert a["criteria"]["K2"] == {
        "value": 9,
        "score": 5,
        "weight": 15.0,
        "points": 15.0,
        "kind": "fact",
        "applicable": True,
    }
    assert a["missing"] == []


def test_trl_not_applicable_moves_weight():
    a = assess(
        {
            "implementation_level": fv(5),
            "trl": None,
            "novelty": fv(3),
            "application_potential": fv(4),
            "credibility": fv(5),
        }
    )
    assert a["criteria"]["K2"]["applicable"] is False
    assert a["criteria"]["K2"]["weight"] == 0
    assert a["criteria"]["K1"]["weight"] == 35.3
    assert sum(e["weight"] for e in a["criteria"].values()) == pytest.approx(100, abs=0.2)
    # (30*5 + 20*3 + 20*4 + 15*5) / 5 / 85 * 100 = 85.88
    assert a["potential"] == 86


def test_unknown_values_give_a_range():
    a = assess(
        {
            "implementation_level": fv(5),
            "trl": fv(None, "estimate"),
            "novelty": None,
            "application_potential": fv(None),
            "credibility": fv(3, "estimate"),
        }
    )
    assert a["missing"] == ["K3", "K4"]
    # Known: 35.29 + 10.59 = 45.88 points. Unknown weight: 47.06.
    assert (a["low"], a["high"]) == (46, 93)
    assert a["low"] <= a["potential"] <= a["high"]
    assert a["potential"] == 87
    assert a["fact_share"] == 35
    assert a["confidence"] == "low"


def test_no_data():
    a = assess({})
    assert a["potential"] is None
    assert (a["low"], a["high"]) == (0, 100)
    assert a["confidence"] == "low"
    assert a["missing"] == ["K1", "K3", "K4", "K5"]


def test_confidence_medium():
    a = assess(
        {
            "implementation_level": fv(4),
            "trl": fv(6, "estimate"),
            "novelty": fv(2),
            "application_potential": fv(3, "estimate"),
            "credibility": fv(4, "estimate"),
        }
    )
    assert a["fact_share"] == 50
    assert a["confidence"] == "medium"


def test_full_innovation_record_is_accepted_and_repeatable():
    record = {
        "id": "fe-2021-000123",
        "title": "E-usługi publiczne",
        "implementation_level": {"value": 5, "kind": "fact", "source_url": "https://example.org", "evidence": "x"},
        "trl": None,
        "novelty": {"value": 2, "kind": "estimate", "reason": "y"},
        "application_potential": {"value": 3, "kind": "estimate", "reason": "z"},
        "credibility": {"value": 3, "kind": "fact"},
    }
    assert assess(record) == assess(record)


@pytest.mark.parametrize(
    "record",
    [
        {"implementation_level": fv(7)},
        {"implementation_level": fv(0)},
        {"trl": fv(10)},
        {"trl": fv(6.5)},
        {"novelty": fv("3")},
        {"credibility": fv(True)},
        {"credibility": fv(3, "guess")},
    ],
)
def test_invalid_values_raise(record):
    with pytest.raises((ValueError, TypeError)):
        assess(record)


@pytest.mark.parametrize(
    "text,level",
    [
        ("System wdrożono w 2023 r. Jest stosowany w 12 gminach.", 5),
        ("Aplikacja funkcjonuje od 2021 roku w urzędzie miasta.", 5),
        ("W trzech szkołach trwa wdrożenie pilotażowe metody.", 4),
        ("Wdrożono pilotażowo w dwóch gminach.", 4),
        ("Prototyp przeszedł testy w laboratorium.", 3),
        ("Zespół zbudował prototyp, który zostanie wdrożony w przyszłym roku.", 2),
        ("Planujemy wdrożenie systemu w 2027 roku.", 1),
        ("Przedstawiamy koncepcję nowej platformy.", 1),
        ("Uczniowie odwiedzili muzeum.", None),
        ("", None),
    ],
)
def test_estimate_implementation_level(text, level):
    result = estimate_implementation_level(text, source_url="https://example.org/a")
    assert result["value"] == level
    assert result["kind"] == "estimate"
    assert result["reason"]
    assert result["source_url"] == "https://example.org/a"
    if level is not None:
        assert result["evidence"] in text


@pytest.mark.parametrize(
    "text,level",
    [
        ("To pierwsze takie rozwiązanie na świecie.", 5),
        ("Jeden z pierwszych systemów w Europie, pierwszy w Polsce.", 4),
        ("Gmina jako pierwsza w Polsce uruchomiła e-usługę.", 3),
        ("To jedyny taki program w województwie.", 2),
        ("Szkoła prowadzi innowację pedagogiczną z robotyki.", 1),
        ("Nowe boisko przy szkole.", None),
    ],
)
def test_estimate_novelty(text, level):
    result = estimate_novelty(text)
    assert result["value"] == level
    if level is not None:
        assert result["evidence"] in text
        assert str(level) in result["reason"]


def test_long_text_evidence_is_short_and_exact():
    text = "Opis projektu " * 40 + "system jest stosowany w praktyce " + "i dalej " * 40
    result = estimate_implementation_level(text)
    assert result["value"] == 5
    assert len(result["evidence"]) <= 200
    assert result["evidence"] in text


def test_estimate_feeds_assessment():
    text = "Aplikację wdrożono w 2022 r. To pierwsze takie rozwiązanie w Polsce."
    a = assess({"implementation_level": estimate_implementation_level(text), "novelty": estimate_novelty(text)})
    assert a["criteria"]["K1"] == {**a["criteria"]["K1"], "value": 5, "kind": "estimate"}
    assert a["criteria"]["K3"]["value"] == 3
    assert a["confidence"] == "low"
