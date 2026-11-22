"""Full-text search with Polish lemmas (SQLite FTS5, BM25), filters, ranking and similar innovations."""

import json
import re
import sqlite3
from functools import lru_cache

import simplemma

from src import applications
from src.models import Innovation, InnovationDetail, SearchResponse, SearchResult

# Ranking of the contract (src/models.py): relevance has priority, the potential breaks ties.
RELEVANCE_WEIGHT = 0.7
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


def search(
    conn: sqlite3.Connection,
    q: str = "",
    area: str | None = None,
    voivodeship: str | None = None,
    level_min: int | None = None,
    group: str | None = None,
    limit: int = 20,
    exclude: str | None = None,
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
                WHERE innovations_fts MATCH ?{where} ORDER BY score LIMIT 500""",
            [match, *args],
        ).fetchall()
        # BM25 in SQLite is negative: the best match has the lowest value.
        best = rows[0]["score"] if rows else -1.0
        scored = [(Innovation.model_validate(json.loads(r["data"])), r["score"] / best if best else 0.0) for r in rows]
        total = len(rows)
    else:
        rows = conn.execute(
            f"SELECT i.data FROM innovations i WHERE 1 = 1{where} ORDER BY i.potential DESC NULLS LAST LIMIT 500",
            args,
        ).fetchall()
        scored = [(Innovation.model_validate(json.loads(r["data"])), 1.0) for r in rows]
        total = conn.execute(f"SELECT COUNT(*) FROM innovations i WHERE 1 = 1{where}", args).fetchone()[0]

    results = [_result(innovation, relevance) for innovation, relevance in scored]
    preferred = GROUP_AREAS.get(group or "")
    results.sort(key=lambda r: (preferred is not None and r.area.value != preferred, -r.rank_score))
    return SearchResponse(total=max(total, len(results)), results=results[:limit])


def detail(conn: sqlite3.Connection, innovation: Innovation, k: int = 5) -> InnovationDetail:
    """Return the card with the k most similar innovations and the applications (src/applications.py)."""
    text = " ".join([innovation.title, *innovation.keywords])
    # More candidates than k, so that the list of other institutions is not empty.
    candidates = search(conn, text, exclude=innovation.id, limit=4 * k).results if text.strip() else []
    return InnovationDetail(
        **innovation.model_dump(),
        similar=candidates[:k],
        applications=applications.recommend(innovation, candidates),
    )
