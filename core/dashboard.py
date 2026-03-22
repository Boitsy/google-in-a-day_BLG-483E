"""Terminal dashboard: live crawl metrics and optional search hits."""

from __future__ import annotations

import os
import queue
import threading
import time
from types import ModuleType

from .index import CrawlIndex, SearchResult


class Dashboard(threading.Thread):
    """Periodic full-screen status view; safe to update results from other threads."""

    def __init__(
        self,
        index: CrawlIndex,
        url_queue: queue.Queue,
        config: ModuleType,
    ) -> None:
        super().__init__(daemon=True)
        self._index = index
        self._url_queue = url_queue
        self._config = config
        self._results_lock = threading.Lock()
        self._pending_results: list[SearchResult] = []

    def set_results(self, results: list[SearchResult]) -> None:
        """Replace queued search hits (copy) for the next refresh."""
        with self._results_lock:
            self._pending_results = list(results)

    def _pop_results(self) -> list[SearchResult]:
        with self._results_lock:
            out = self._pending_results
            self._pending_results = []
            return out

    def run(self) -> None:
        while True:
            time.sleep(1.5)
            os.system("cls" if os.name == "nt" else "clear")
            stats = self._index.stats()
            depth = self._url_queue.qsize()
            cap = self._config.QUEUE_MAX_SIZE
            throttle = "THROTTLED" if depth >= cap * 0.8 else "OK"
            last = stats.get("last_indexed_url") or "(none)"

            print(" Google in a Day - Dashboard")
            print("-" * 40)
            print(f"  Pages indexed:   {stats['pages_indexed']}")
            print(f"  URLs visited:    {stats['urls_visited']}")
            print(f"  Queue depth:     {depth} / {cap}")
            print(f"  Throttle:        {throttle}")
            print(f"  Last indexed:    {last}")
            print("-" * 40)

            results = self._pop_results()
            if results:
                print(" Search results")
                print("-" * 40)
                for i, hit in enumerate(results, start=1):
                    print(
                        f"  {i}. score={hit.score:g} depth={hit.depth}\n"
                        f"     {hit.url}"
                    )
                print("-" * 40)


if __name__ == "__main__":
    from . import config

    class _MockIndex:
        """Minimal stand-in: only `stats()` is used by the dashboard."""

        def stats(self) -> dict[str, int | str | None]:
            return {
                "pages_indexed": 12,
                "urls_visited": 40,
                "last_indexed_url": "https://example.com/mock-page",
            }

    q: queue.Queue[tuple[int, int, int]] = queue.Queue(
        maxsize=config.QUEUE_MAX_SIZE,
    )
    for _ in range(3):
        q.put((0, 0, 0))

    board = Dashboard(_MockIndex(), q, config)
    board.set_results(
        [
            SearchResult(
                url="https://ex.com/hit",
                origin_url="https://ex.com/",
                depth=1,
                score=5.0,
            )
        ]
    )
    board.start()
    time.sleep(4.0)
    print("(manual test finished — daemon dashboard stops with process)")
