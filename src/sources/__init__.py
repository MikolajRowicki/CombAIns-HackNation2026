"""Data sources. Each module has one function that returns a SourceData object."""

from dataclasses import dataclass, field
from datetime import date

from src.models import Innovation


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
