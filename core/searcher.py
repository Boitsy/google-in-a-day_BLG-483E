"""Pure query scoring over a thread-safe crawl index snapshot."""

from __future__ import annotations

import re

from .index import CrawlIndex, SearchResult


def search(query: str, index: CrawlIndex, top_n: int) -> list[SearchResult]:
    """Rank indexed pages by keyword frequency in body and title bonus."""
    keywords = re.findall(r"[a-z0-9]+", query.lower())
    if not keywords:
        return []

    pages = index.get_all_records()
    results: list[SearchResult] = []
    for page in pages:
        score = sum(page.word_freq.get(kw, 0) for kw in keywords)
        title_lower = page.title.lower()
        score += 2 * sum(1 for kw in keywords if kw in title_lower)
        if score == 0:
            continue
        results.append(
            SearchResult(
                url=page.url,
                origin_url=page.origin_url,
                depth=page.depth,
                score=float(score),
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]


if __name__ == "__main__":
    from .index import PageRecord

    idx = CrawlIndex()
    idx.add_page(
        PageRecord(
            url="https://ex.com/a",
            origin_url="https://ex.com/",
            depth=0,
            title="No match here",
            word_freq={"other": 5},
        )
    )
    idx.add_page(
        PageRecord(
            url="https://ex.com/b",
            origin_url="https://ex.com/",
            depth=1,
            title="Python notes",
            word_freq={"python": 2, "code": 1},
        )
    )
    idx.add_page(
        PageRecord(
            url="https://ex.com/c",
            origin_url="https://ex.com/b",
            depth=2,
            title="Learn python today",
            word_freq={"learn": 1},
        )
    )
    hits = search("python tutorial", idx, top_n=5)
    assert len(hits) == 2, f"expected 2 matches, got {hits!r}"
    assert hits[0].url == "https://ex.com/b"
    assert hits[0].score > hits[1].score
    assert hits[1].url == "https://ex.com/c"
    top1 = search("python", idx, top_n=1)
    assert len(top1) == 1 and top1[0].url == "https://ex.com/b"
    print("searcher.py self-test OK:", [(h.url, h.score) for h in hits])
