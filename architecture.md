# System Architecture
## Project: "Google in a Day" — Web Crawler & Real-Time Search Engine

---

## 1. Module Structure

```
google-in-a-day/
├── main.py           # Entry point: wires everything together, starts threads
├── core/
│   ├── config.py     # All tunable constants in one place
│   ├── index.py      # Thread-safe in-memory index (the shared data store)
│   ├── crawler.py    # Worker threads: fetch → parse → enqueue → store
│   ├── searcher.py   # Query engine: reads live index, ranks results
│   ├── dashboard.py  # CLI real-time display (optional; runs in its own thread)
│   └── api.py        # Flask web dashboard + SSE + /start + /search
├── templates/
│   └── dashboard.html
├── product_prd.md
├── recommendation.md
└── readme.md
```

---

## 2. Component Responsibilities

### config.py
- Single source of truth for all tunable values
- No logic, just constants
- Example values: SEED_URL, MAX_DEPTH, MAX_WORKERS, QUEUE_MAX_SIZE, REQUEST_DELAY_SEC

### index.py — `CrawlIndex`
- Owns two shared data structures:
  - `_store: dict[url → PageRecord]` — the index
  - `_visited: set[str]` — URLs already seen
- Wraps both behind a `threading.Lock`
- Public methods:
  - `mark_visited(url) → bool` — atomically check-and-add to visited set
  - `add_page(record: PageRecord)` — write a page into the store
  - `search(query: str) → list[SearchResult]` — scored search read
  - `stats() → dict` — returns counts for the dashboard

### crawler.py — `CrawlerWorker`
- Each worker is a `threading.Thread`
- Loop: `url_queue.get()` → fetch → parse links → filter → enqueue new URLs → store page
- Uses `urllib.request` for HTTP, `html.parser` (via `HTMLParser` subclass) for link + title extraction
- Respects `REQUEST_DELAY_SEC` between fetches
- Handles exceptions (timeout, HTTP error, decode error) silently — logs and continues
- Calls `index.mark_visited()` before enqueuing any URL to prevent duplicates

### searcher.py — `search(query, index)`
- Pure function (no state, no threads)
- Tokenizes query into keywords
- Iterates over index store, computes a relevance score per page:
  - `score = sum(word_freq.get(kw, 0) for kw in keywords)`
  - `score += 2 * sum(1 for kw in keywords if kw in title.lower())` (title bonus)
- Returns top-N results sorted by score as `(url, origin_url, depth)` triples

### dashboard.py — `Dashboard`
- Runs in a dedicated `threading.Thread` (daemon)
- Every 1.5 seconds: clears terminal, prints metrics from `index.stats()`
- Metrics shown:
  - URLs indexed / URLs queued / Queue depth
  - Throttling status (active workers vs MAX_WORKERS)
  - Last indexed URL
- Also prints search results when the main thread passes them in

### main.py
- Parses CLI args (seed URL, depth override)
- Instantiates `CrawlIndex`, `queue.Queue(maxsize=QUEUE_MAX_SIZE)`
- Seeds the queue with `(SEED_URL, depth=0)`
- Spawns `MAX_WORKERS` `CrawlerWorker` threads
- Spawns 1 `Dashboard` thread
- Runs an input loop: user types a query → calls `searcher.search()` → dashboard displays results
- Joins all threads on KeyboardInterrupt

---

## 3. Concurrency Design

```
                        ┌──────────────────────────────┐
                        │         queue.Queue          │
                        │   (bounded: QUEUE_MAX_SIZE)  │
                        │                              │
  main.py ──seed──▶     │  (url, depth) tuples         │
                        └────────────┬─────────────────┘
                                     │  .get() blocks when empty
                   ┌─────────────────┼──────────────────┐
                   ▼                 ▼                   ▼
            Worker-1           Worker-2  ...       Worker-N
               │                   │                    │
               └───────────────────┴────────────────────┘
                                   │
                              writes to
                                   │
                                   ▼
                        ┌──────────────────┐
                        │   CrawlIndex     │
                        │                 │
                        │  threading.Lock │◀── searcher reads (same lock)
                        │  _store: dict   │
                        │  _visited: set  │
                        └──────────────────┘
```

### Back-Pressure
- `queue.Queue(maxsize=QUEUE_MAX_SIZE)` — workers calling `.put()` will **block** automatically when the queue is full
- This is Python's built-in back-pressure: no URLs are dropped, workers simply wait
- `REQUEST_DELAY_SEC` adds per-worker rate limiting on top

### Thread Safety Rules
- ALL reads and writes to `_store` and `_visited` go through `CrawlIndex` methods
- No worker ever touches the raw dict/set directly
- The `mark_visited` method is atomic: check + add happen inside a single lock acquisition
- Dashboard reads via `stats()` also acquire the lock (brief read, acceptable cost)

---

## 4. Data Structures

### PageRecord (stored in index)
```python
@dataclass
class PageRecord:
    url: str
    origin_url: str
    depth: int
    title: str
    word_freq: dict[str, int]   # lowercase word → count
```

### QueueItem (passed through queue)
```python
(url: str, origin_url: str, depth: int)
```

### SearchResult (returned to user)
```python
@dataclass
class SearchResult:
    url: str
    origin_url: str
    depth: int
    score: float
```

---

## 5. Error Handling Strategy

| Error Type | Handling |
|---|---|
| HTTP 4xx / 5xx | Log URL + status code, skip page, continue |
| Connection timeout | Log URL, skip page, continue |
| UnicodeDecodeError | Skip page, continue |
| Malformed URL | Skip during normalization, never enqueued |
| Queue full | Worker blocks (back-pressure — this is expected behavior) |

---

## 6. URL Normalization Rules

Before any URL is enqueued, apply:
1. Resolve relative URLs against the current page's base URL (`urllib.parse.urljoin`)
2. Strip URL fragments (`#section` → removed)
3. Strip query strings (optional, configurable)
4. Lowercase scheme and host
5. If `SAME_DOMAIN_ONLY=True`, discard URLs whose netloc differs from the seed's netloc

---

## 7. Build Order for Cursor (Phase 4)

Build in this exact sequence to keep each step testable:

1. **`config.py`** — constants only, no dependencies
2. **`index.py`** — `CrawlIndex` with lock, `mark_visited`, `add_page`, `stats`; unit-testable in isolation
3. **`crawler.py`** — one `CrawlerWorker` thread; test with a single known URL
4. **`searcher.py`** — pure function; test with a hand-built index
5. **`dashboard.py`** — display only; wire to a mock `stats()` first
6. **`main.py`** — assemble all pieces, test end-to-end with depth=1, then depth=2

---

*End of Architecture Document*
