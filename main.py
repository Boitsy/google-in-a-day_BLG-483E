"""Entry point: concurrent crawl, live dashboard, and interactive search."""

from __future__ import annotations

import argparse
import queue

import core.config as config
from core.api import DashboardAPI
from core.crawler import CrawlerWorker
from core.index import CrawlIndex
from core.searcher import search


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Google in a Day — crawler + search",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Seed URL (default: config.SEED_URL)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=None,
        help="Maximum crawl depth (default: config.MAX_DEPTH)",
    )
    return parser.parse_args()


def _apply_config_overrides(args: argparse.Namespace) -> str:
    if args.url:
        config.SEED_URL = args.url
    if args.depth is not None:
        config.MAX_DEPTH = args.depth
    return config.SEED_URL


def main() -> None:
    args = _parse_args()
    _apply_config_overrides(args)

    index = CrawlIndex()
    url_queue: queue.Queue[tuple[str | None, str | None, int | None]] = (
        queue.Queue(maxsize=config.QUEUE_MAX_SIZE)
    )

    workers = [
        CrawlerWorker(url_queue, index, config)
        for _ in range(config.MAX_WORKERS)
    ]
    for worker in workers:
        worker.start()

    api = DashboardAPI(index, url_queue, config)
    api.start(host="127.0.0.1", port=5000)
    print("Dashboard running at http://127.0.0.1:5000")

    try:
        while True:
            query = input("search> ").strip()
            if not query:
                continue
            hits = search(query, index, config.TOP_N_RESULTS)
            api.set_results(hits)
            if not hits:
                print("(no results)")
            else:
                for i, hit in enumerate(hits, start=1):
                    print(f"  {i}. score={hit.score:g} depth={hit.depth} {hit.url}")
    except KeyboardInterrupt:
        print("\nShutting down...")
        for _ in range(config.MAX_WORKERS):
            try:
                url_queue.put_nowait((None, None, None))
            except queue.Full:
                break
        for worker in workers:
            worker.join(timeout=5.0)


if __name__ == "__main__":
    main()
