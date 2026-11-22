"""Data sources. Each module has one function that returns a SourceData object."""

from dataclasses import dataclass, field
from datetime import date

from src.models import FieldValue, Innovation

SUMMARY_CHARS = 300


@dataclass
class SourceData:
    """Records of one source and their metadata (AGENTS.md, section "Code")."""

    name: str
    url: str
    license: str
    retrieved: date
    data_date: date | None = None
    records: list[Innovation] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def summary_quote(text: str, url: str) -> FieldValue:
    """Return the first sentences of the source text as a quote."""
    text = text.strip()
    if len(text) <= SUMMARY_CHARS:
        cut, value = text, text
    else:
        end = text.rfind(". ", 0, SUMMARY_CHARS)
        if end > 100:
            cut = value = text[: end + 1]
        else:
            cut = text[: text.rfind(" ", 0, SUMMARY_CHARS)]
            value = cut + " …"
    return FieldValue(value=value, kind="fact", source_url=url, evidence=cut)
