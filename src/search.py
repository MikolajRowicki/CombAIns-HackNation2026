"""Full-text search with Polish lemmas (SQLite FTS5, BM25), filters, ranking and similar innovations."""

import json
import math
import re
import sqlite3
from functools import lru_cache

import simplemma

from src import applications
from src.models import (
    DemandSignal,
    Innovation,
    InnovationDetail,
    SearchResponse,
    SearchResult,
)

# Ranking of the contract (src/models.py): relevance has priority, the potential breaks ties.
RELEVANCE_WEIGHT = 0.7
# The page shows more results with an offset. The group sort needs all candidates in memory.
MAX_CANDIDATES = 2000
POTENTIAL_WEIGHT = 0.3

# A user group gets its area first (FAQ, section 3). The group does not remove other results.
GROUP_AREAS = {
    "investors": "technological",
    "startups": "technological",
    "innovators": "technological",
    "public": "administrative",
    "schools": "educational",
}

_STOPWORDS = {
    "dla", "oraz", "lub", "się", "jest", "przez", "który", "która", "które", "jak", "the", "and", "nie",
    "tak", "też", "być", "mieć", "ten", "ta", "to", "na", "do", "od", "po", "przy", "pod", "nad", "za",
}
_WORD = re.compile(r"\w[\w-]*", re.UNICODE)


@lru_cache(maxsize=100_000)
def _lemma(token: str) -> str:
    return simplemma.lemmatize(token, lang="pl").lower()


def tokens(text: str) -> list[str]:
    return [t for t in (w.lower() for w in _WORD.findall(text or "")) if len(t) > 2 and t not in _STOPWORDS]


def lemmatize(text: str) -> str:
    return " ".join(_lemma(t) for t in tokens(text))


def index(conn: sqlite3.Connection, innovation: Innovation) -> None:
    """Write the lemmas of one record into the full-text index."""
    conn.execute("DELETE FROM innovations_fts WHERE id = ?", (innovation.id,))
    conn.execute(
        "INSERT INTO innovations_fts (id, title, summary, description, keywords) VALUES (?, ?, ?, ?, ?)",
        (
            innovation.id,
            lemmatize(innovation.title),
            lemmatize(str(innovation.summary.value or "")),
            lemmatize(innovation.description),
            lemmatize(" ".join(innovation.keywords)),
        ),
    )


def _match_query(text: str, max_terms: int = 30) -> str | None:
    """Make an FTS5 query: each word as its lemma or as a prefix of the word, joined with OR."""
    terms = []
    for token in tokens(text)[:max_terms]:
        terms.append(f'"{_lemma(token)}"')
        stem = token[: max(4, len(token) - 2)]
        if len(stem) >= 4:
            terms.append(f'"{stem}"*')
    return " OR ".join(dict.fromkeys(terms)) or None


def _result(innovation: Innovation, relevance: float) -> SearchResult:
    potential = innovation.assessment.potential
    return SearchResult(
        id=innovation.id,
        title=innovation.title,
        summary=innovation.summary,
        area=innovation.area,
        institution=innovation.institution,
        implementation_level=innovation.implementation_level,
        potential=potential,
        confidence=innovation.assessment.confidence,
        relevance=round(relevance, 4),
        rank_score=round(RELEVANCE_WEIGHT * relevance + POTENTIAL_WEIGHT * (potential or 0) / 100, 4),
    )


def _filters(area, voivodeship, level_min) -> tuple[str, list]:
    sql, args = [], []
    if area:
        sql.append("i.area = ?")
        args.append(area)
    if voivodeship:
        sql.append("i.voivodeship = ?")
        args.append(voivodeship)
    if level_min:
        sql.append("i.implementation_level >= ?")
        args.append(int(level_min))
    return "".join(f" AND {s}" for s in sql), args


# A small bonus in the order for the needs of each user group (FAQ, section 3). The relevance stays the main key.
GROUP_BONUS = 0.1


def _value(field) -> int:
    return (field.value or 0) if field is not None and isinstance(field.value, int) else 0


def group_bonus(group: str | None, innovation: Innovation) -> float:
    """Return the bonus of one card for one user group. The rules are in README.md (table of the user groups)."""
    rules = {
        "investors": _value(innovation.trl) >= 6 or _value(innovation.implementation_level) >= 4,
        "startups": _value(innovation.novelty) >= 3,
        "innovators": "patent" in str(innovation.type.value or "").lower(),
        "public": _value(innovation.implementation_level) >= 4,
        "schools": _value(innovation.credibility) >= 4,
        "science": innovation.institution.kind == "university",
    }
    return GROUP_BONUS if rules.get(group or "") else 0.0


def search(
    conn: sqlite3.Connection,
    q: str = "",
    area: str | None = None,
    voivodeship: str | None = None,
    level_min: int | None = None,
    group: str | None = None,
    limit: int = 20,
    exclude: str | None = None,
    offset: int = 0,
) -> SearchResponse:
    where, args = _filters(area, voivodeship, level_min)
    if exclude:
        where += " AND i.id != ?"
        args.append(exclude)
    match = _match_query(q)
    if match:
        rows = conn.execute(
            f"""SELECT i.data, bm25(innovations_fts, 10.0, 4.0, 1.0, 4.0) AS score
                FROM innovations_fts f JOIN innovations i ON i.id = f.id
                WHERE innovations_fts MATCH ?{where} ORDER BY score LIMIT {MAX_CANDIDATES}""",
            [match, *args],
        ).fetchall()
        # BM25 in SQLite is negative: the best match has the lowest value.
        best = rows[0]["score"] if rows else -1.0
        scored = [(Innovation.model_validate(json.loads(r["data"])), r["score"] / best if best else 0.0) for r in rows]
        total = len(rows)
    else:
        rows = conn.execute(
            f"SELECT i.data FROM innovations i WHERE 1 = 1{where} ORDER BY i.potential DESC NULLS LAST LIMIT {MAX_CANDIDATES}",
            args,
        ).fetchall()
        scored = [(Innovation.model_validate(json.loads(r["data"])), 1.0) for r in rows]
        total = conn.execute(f"SELECT COUNT(*) FROM innovations i WHERE 1 = 1{where}", args).fetchone()[0]

    preferred = GROUP_AREAS.get(group or "")
    ranked = [(_result(innovation, relevance), group_bonus(group, innovation)) for innovation, relevance in scored]
    ranked.sort(key=lambda x: (preferred is not None and x[0].area.value != preferred, -(x[0].rank_score + x[1])))
    results = [r for r, _ in ranked]
    return SearchResponse(total=max(total, len(results)), results=results[offset : offset + limit])


def detail(conn: sqlite3.Connection, innovation: Innovation, k: int = 5) -> InnovationDetail:
    """Return the card with the k most similar innovations and the applications (src/applications.py)."""
    text = " ".join([innovation.title, *innovation.keywords])
    # More candidates than k, so that the list of other institutions is not empty.
    candidates = search(conn, text, exclude=innovation.id, limit=4 * k).results if text.strip() else []
    return InnovationDetail(
        **innovation.model_dump(exclude={"demand"}),
        similar=candidates[:k],
        demand=innovation.demand or demand(conn, innovation),
        applications=applications.recommend(innovation, candidates),
    )


# Words that occur in most notices or titles. A match on these words alone is not a demand signal.
_GENERIC = {
    "dostawa", "usługa", "wykonanie", "zakup", "świadczenie", "realizacja", "system", "sposób", "urządzenie",
    "układ", "gmina", "miasto", "powiat", "projekt", "część", "zadanie", "rok", "nowy", "nowoczesny", "rozwój",
    "budowa", "przebudowa", "zamówienie", "dostarczenie", "obsługa", "wraz", "element", "materiał", "zestaw",
    "sprzęt", "program", "rama", "umowa", "okres", "potrzeba", "polska", "województwo", "jednostka", "teren",
    "wyposażenie", "dostosowanie", "przedmiot", "wynalazek", "zastosowanie", "zwłaszcza", "który", "jego",
    "podstawa", "wykorzystanie", "oparty", "metoda", "wytwarzanie", "uzyskanie", "dotyczyć", "zakres",
    "organizacja", "ramy", "wysoki", "dwa", "ten", "poprzez", "cel", "proces", "wdrożyć", "wdrożenie",
    "rozwiązanie", "spółka", "ograniczony", "odpowiedzialność", "przedsiębiorstwo", "opracować", "planować",
    "przeprowadzić", "praca", "zmiana", "osoba", "obszar",
    # Words of the patent law ("prawo ochronne na wzór użytkowy") are not a subject of a purchase.
    "użytkowy", "własność", "wzór", "ochronny", "prawo", "patent",
}
MIN_COMMON_WORDS = 2
MIN_DEMAND_SCORE = 12.0  # sum of IDF weights; about two rare words


def index_notice(conn: sqlite3.Connection, notice: dict) -> None:
    conn.execute(
        "INSERT INTO notices (id, data, date) VALUES (?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET data = excluded.data, date = excluded.date",
        (notice["id"], json.dumps(notice, ensure_ascii=False), notice["date"]),
    )
    conn.execute("DELETE FROM notices_fts WHERE id = ?", (notice["id"],))
    conn.execute("INSERT INTO notices_fts (id, subject) VALUES (?, ?)", (notice["id"], lemmatize(notice["subject"])))


def demand(conn: sqlite3.Connection, innovation: Innovation, k: int = 5) -> list[DemandSignal]:
    """Return the notices of public purchases with a similar subject.

    The match score is the sum of IDF weights of the common words (not generic). A rare word has a high weight.
    Thus two common words such as "plan" and "lokalny" give a low score, and "rehabilitacja" gives a high score.
    """
    text = " ".join([innovation.title, str(innovation.summary.value or ""), *innovation.keywords])
    lemmas = {_lemma(t) for t in tokens(text)} - _GENERIC
    if len(lemmas) < MIN_COMMON_WORDS:
        return []
    total = conn.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
    if not total:
        return []
    weight = {}
    for lemma in lemmas:
        count = conn.execute("SELECT COUNT(*) FROM notices_fts WHERE notices_fts MATCH ?", (f'"{lemma}"',)).fetchone()[0]
        if count:
            weight[lemma] = math.log(total / count)
    if not weight:
        return []
    rows = conn.execute(
        """SELECT n.data, f.subject FROM notices_fts f JOIN notices n ON n.id = f.id
           WHERE notices_fts MATCH ? ORDER BY bm25(notices_fts) LIMIT 200""",
        (" OR ".join(f'"{lemma}"' for lemma in sorted(weight)),),
    ).fetchall()
    found, seen = [], set()
    for row in rows:
        common = set(weight) & set(row["subject"].split())
        score = sum(weight[w] for w in common)
        notice = json.loads(row["data"])
        key = (notice["buyer"].lower(), notice["subject"].lower())
        if len(common) >= MIN_COMMON_WORDS and score >= MIN_DEMAND_SCORE and key not in seen:
            seen.add(key)
            found.append((score, notice, sorted(common, key=lambda w: -weight[w])))
    found.sort(key=lambda f: (-f[0], f[1]["date"]))
    signals = []
    for _, notice, common in found[:k]:
        place = ", ".join(x for x in (notice.get("city"), notice.get("voivodeship")) if x)
        signals.append(
            DemandSignal(
                buyer=f"{notice['buyer']} ({place})" if place else notice["buyer"],
                date=notice["date"],
                subject=notice["subject"],
                url=notice["url"],
                voivodeship=notice.get("voivodeship"),
                reason="Wspólne słowa: " + ", ".join(common),
            )
        )
    return signals
