"""Concurrent crawler workers: fetch HTML, parse, enqueue, index."""

from __future__ import annotations

import logging
import queue
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from types import ModuleType

from .index import CrawlIndex, PageRecord

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[a-z0-9]+")


class LinkTextParser(HTMLParser):
    """Collect hrefs, document title, and visible-ish body text."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url
        self.links: list[str] = []
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []
        self._in_title = False
        self._in_head = False
        self._in_script = False
        self._in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k: v for k, v in attrs if v is not None}
        if tag == "a":
            href = attrs_dict.get("href")
            if href:
                self.links.append(href)
        if tag == "head":
            self._in_head = True
        if tag == "body":
            self._in_head = False
        if tag == "title":
            self._in_title = True
        if tag == "script":
            self._in_script = True
        if tag == "style":
            self._in_style = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            self._in_head = False
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._in_script = False
        if tag == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if self._in_script or self._in_style:
            return
        if self._in_title:
            self._title_parts.append(data)
            return
        if self._in_head:
            return
        self._text_parts.append(data)

    def title_str(self) -> str:
        return " ".join(self._title_parts).strip()

    def word_freq(self) -> dict[str, int]:
        blob = "".join(self._text_parts).lower()
        words = _WORD_RE.findall(blob)
        return dict(Counter(words))


def normalize_url(
    href: str,
    base_url: str,
    seed_netloc: str,
    same_domain_only: bool,
) -> str | None:
    """urljoin → strip fragment → lowercase scheme/host → optional domain filter."""
    joined = urllib.parse.urljoin(base_url, href.strip())
    no_frag, _frag = urllib.parse.urldefrag(joined)
    parts = urllib.parse.urlparse(no_frag)
    scheme = (parts.scheme or "").lower()
    if scheme not in ("http", "https"):
        return None
    netloc = parts.netloc.lower()
    if not netloc:
        return None
    path = parts.path if parts.path else "/"
    cleaned = urllib.parse.urlunparse(
        (scheme, netloc, path, parts.params, parts.query, "")
    )
    if same_domain_only and netloc != seed_netloc:
        return None
    return cleaned


class CrawlerWorker(threading.Thread):
    """Worker thread: dequeue URLs, fetch, parse, enqueue children, index page."""

    def __init__(
        self,
        url_queue: queue.Queue[tuple[str | None, str | None, int | None]],
        index: CrawlIndex,
        config: ModuleType,
    ) -> None:
        super().__init__(daemon=False)
        self._url_queue = url_queue
        self._index = index
        self._config = config

    def run(self) -> None:
        while True:
            item = self._url_queue.get()
            try:
                url, origin_url, depth = item
                if url is None:
                    break
                if depth > self._config.MAX_DEPTH:
                    continue
                try:
                    body, charset = self._fetch(url)
                    text = body.decode(charset, errors="strict")
                except urllib.error.HTTPError as e:
                    logger.warning(
                        "fetch HTTPError url=%s type=%s error=%s",
                        url,
                        type(e).__name__,
                        e,
                    )
                    continue
                except urllib.error.URLError as e:
                    logger.warning(
                        "fetch URLError url=%s type=%s error=%s",
                        url,
                        type(e).__name__,
                        e,
                    )
                    continue
                except UnicodeDecodeError as e:
                    logger.warning(
                        "decode UnicodeDecodeError url=%s type=%s error=%s",
                        url,
                        type(e).__name__,
                        e,
                    )
                    continue
                except Exception as e:
                    logger.error(
                        "unexpected error url=%s type=%s error=%s",
                        url,
                        type(e).__name__,
                        e,
                    )
                    continue

                parser = LinkTextParser(url)
                try:
                    parser.feed(text)
                    parser.close()
                except Exception as e:
                    logger.error(
                        "unexpected error url=%s type=%s error=%s",
                        url,
                        type(e).__name__,
                        e,
                    )
                    continue

                if depth < self._config.MAX_DEPTH:
                    for raw_href in parser.links:
                        seed_netloc = urllib.parse.urlparse(
                            self._config.SEED_URL
                        ).netloc.lower()
                        norm = normalize_url(
                            raw_href,
                            url,
                            seed_netloc,
                            self._config.SAME_DOMAIN_ONLY,
                        )
                        if norm is None:
                            continue
                        if self._index.mark_visited(norm):
                            self._url_queue.put(
                                (norm, url, depth + 1),
                            )

                record = PageRecord(
                    url=url,
                    origin_url=origin_url,
                    depth=depth,
                    title=parser.title_str(),
                    word_freq=parser.word_freq(),
                )
                self._index.add_page(record)
                time.sleep(self._config.REQUEST_DELAY_SEC)
            finally:
                self._url_queue.task_done()

    def _fetch(self, url: str) -> tuple[bytes, str]:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; GoogleInADay/1.0; edu)",
            },
            method="GET",
        )
        with urllib.request.urlopen(
            req,
            timeout=self._config.REQUEST_TIMEOUT_SEC,
        ) as resp:
            body = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return body, charset


if __name__ == "__main__":
    from . import config

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    q: queue.Queue[tuple[str, str, int]] = queue.Queue()
    idx = CrawlIndex()
    seed = config.SEED_URL
    assert idx.mark_visited(seed)
    q.put((seed, seed, 0))
    worker = CrawlerWorker(q, idx, config)
    worker.daemon = True
    worker.start()
    q.join()
    print("Manual crawl test:", idx.stats())
