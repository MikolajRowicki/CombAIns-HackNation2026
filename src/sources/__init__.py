"""Data sources. Each module has one function that returns a SourceData object."""

import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx
from protego import Protego

from src.models import FieldValue, Innovation

SUMMARY_CHARS = 300
PAGE_CACHE = Path(__file__).resolve().parents[2] / "data" / "cache" / "pages"
PAGE_CACHE_DAYS = 7
USER_AGENT = "RadarInnowacji/0.1"
MIN_PAUSE = 1.5


class PageFetcher:
    """Read web pages with a cache. Obey robots.txt and the Crawl-delay of each host (AGENTS.md, rule 12)."""

    def __init__(self, client: httpx.Client, cache: Path | None = None):
        self.client = client
        self.cache = cache or PAGE_CACHE
        self.robots: dict[str, Protego] = {}
        self.last: dict[str, float] = {}
        # Copies of pages stay only as long as necessary (TDM, art. 26³ of the Polish copyright act): delete old ones.
        old = datetime.now() - timedelta(days=PAGE_CACHE_DAYS)
        for path in self.cache.glob("*.html") if self.cache.exists() else []:
            if datetime.fromtimestamp(path.stat().st_mtime) < old:
                path.unlink()

    def get(self, url: str) -> str:
        self.cache.mkdir(parents=True, exist_ok=True)
        path = self.cache / (re.sub(r"[^\w]+", "_", url)[-150:] + ".html")
        fresh = datetime.now() - timedelta(days=PAGE_CACHE_DAYS)
        if path.exists() and datetime.fromtimestamp(path.stat().st_mtime) > fresh:
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
