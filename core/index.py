"""Thread-safe in-memory crawl index: visited set and page store."""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class PageRecord:
    """One indexed HTML page."""

    url: str
    origin_url: str
    depth: int
    title: str
    word_freq: dict[str, int]


@dataclass
class SearchResult:
    """One ranked hit returned to the user."""

    url: str
    origin_url: str
    depth: int
    score: float


class CrawlIndex:
    """Shared crawl state; all access goes through this class under one lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, PageRecord] = {}
        self._visited: set[str] = set()
        self._last_indexed_url: str | None = None

    def mark_visited(self, url: str) -> bool:
        """Return True if url was newly recorded; False if it was already visited."""
        with self._lock:
            if url in self._visited:
                return False
            self._visited.add(url)
            return True

    def add_page(self, record: PageRecord) -> None:
        """Store a parsed page in the index."""
        with self._lock:
            self._store[record.url] = record
            self._last_indexed_url = record.url

    def stats(self) -> dict[str, int | str | None]:
        """Snapshot counts and last URL for the dashboard (extend in main if needed)."""
        with self._lock:
            return {
                "pages_indexed": len(self._store),
                "urls_visited": len(self._visited),
                "last_indexed_url": self._last_indexed_url,
            }

    def get_all_records(self) -> list[PageRecord]:
        """Return a copy of all PageRecord values for read-only scoring."""
        with self._lock:
            return list(self._store.values())


if __name__ == "__main__":
    index = CrawlIndex()
    u = "https://example.com/page"
    assert index.mark_visited(u) is True
    assert index.mark_visited(u) is False
    rec = PageRecord(
        url=u,
        origin_url="https://example.com/",
        depth=1,
        title="Test",
        word_freq={"hello": 2, "world": 1},
    )
    index.add_page(rec)
    assert index.stats()["pages_indexed"] == 1
    assert index.stats()["urls_visited"] == 1
    assert index.stats()["last_indexed_url"] == u
    print("index.py self-test OK:", index.stats())
