"""Flask HTTP API and SSE stream for crawl metrics and search."""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from dataclasses import asdict
from types import ModuleType

from flask import Flask, Response, jsonify, render_template, request

from .index import CrawlIndex, SearchResult
from .searcher import search

_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


class DashboardAPI:
    """Thread-safe search buffer + Flask app served on a daemon thread."""

    def __init__(
        self,
        index: CrawlIndex,
        url_queue: queue.Queue,
        config: ModuleType,
    ) -> None:
        self._index = index
        self._url_queue = url_queue
        self._config = config
        self._crawl_started = False
        self._crawl_lock = threading.Lock()
        self._results_lock = threading.Lock()
        self._results: list[SearchResult] = []

        self.app = Flask(
            __name__,
            template_folder=os.path.join(_ROOT_DIR, "templates"),
        )

        @self.app.route("/")
        def dashboard_page() -> str:
            return render_template("dashboard.html")

        @self.app.route("/status")
        def status_route():
            with self._crawl_lock:
                started = self._crawl_started
            return jsonify({"crawl_started": started})

        @self.app.route("/start", methods=["POST"])
        def start_route():
            body = request.get_json(silent=True) or {}
            seed_url = str(body.get("url", "")).strip()
            if not seed_url:
                return jsonify({"error": "invalid url"}), 400
            raw_depth = body.get("depth")
            try:
                depth = int(raw_depth)
            except (TypeError, ValueError):
                return jsonify({"error": "invalid depth"}), 400
            if depth < 1 or depth > 5:
                return jsonify({"error": "invalid depth"}), 400

            with self._crawl_lock:
                if self._crawl_started:
                    return jsonify({"error": "already running"}), 400
                self._config.SEED_URL = seed_url
                self._config.MAX_DEPTH = depth
                self._index.mark_visited(seed_url)
                self._url_queue.put((seed_url, seed_url, 0))
                self._crawl_started = True
            self._spawn_sentinel_when_queue_drained()
            return jsonify({"ok": True})

        @self.app.route("/stream")
        def stream() -> Response:
            def event_stream():
                while True:
                    payload = self._sse_payload()
                    line = f"data: {json.dumps(payload)}\n\n"
                    yield line
                    time.sleep(1.5)

            headers = {
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
            return Response(event_stream(), headers=headers)

        @self.app.route("/search", methods=["POST"])
        def search_route():
            body = request.get_json(silent=True) or {}
            q = str(body.get("query", "")).strip()
            hits = search(q, self._index, self._config.TOP_N_RESULTS)
            self.set_results(hits)
            return jsonify([asdict(h) for h in hits])

    def _spawn_sentinel_when_queue_drained(self) -> None:
        """After crawl work finishes, unblock workers with sentinels (same as main used)."""

        def _inject_after_join() -> None:
            self._url_queue.join()
            for _ in range(self._config.MAX_WORKERS):
                self._url_queue.put((None, None, None))

        threading.Thread(target=_inject_after_join, daemon=True).start()

    def set_results(self, results: list[SearchResult]) -> None:
        """Store the latest search hits for SSE clients."""
        with self._results_lock:
            self._results = list(results)

    def get_results(self) -> list[SearchResult]:
        """Return a copy of stored search hits."""
        with self._results_lock:
            return list(self._results)

    def _sse_payload(self) -> dict:
        stats = self._index.stats()
        depth = self._url_queue.qsize()
        cap = self._config.QUEUE_MAX_SIZE
        throttled = depth >= cap * 0.8
        with self._results_lock:
            hits = [asdict(r) for r in self._results]
        with self._crawl_lock:
            crawl_started = self._crawl_started
        return {
            "pages_indexed": stats["pages_indexed"],
            "urls_visited": stats["urls_visited"],
            "queue_depth": depth,
            "queue_max": cap,
            "throttled": throttled,
            "last_indexed_url": stats.get("last_indexed_url"),
            "search_results": hits,
            "crawl_started": crawl_started,
        }

    def start(self, host: str, port: int) -> None:
        """Run Flask on a daemon thread (no reloader)."""

        def _run() -> None:
            self.app.run(
                host=host,
                port=port,
                threaded=True,
                use_reloader=False,
            )

        threading.Thread(target=_run, daemon=True).start()
