# Google in a Day
A functional web crawler and real-time search engine built with Python — no third-party scraping libraries.

Built for the AI Aided Computer Engineering course at Istanbul Technical University.

---

## Demo

Start the server, open `http://127.0.0.1:5000`, enter a seed URL and depth, and watch the dashboard crawl and index pages in real time. Search the live index from the browser while crawling is still in progress.

---

## Features

- **Concurrent crawler** — configurable worker thread pool crawls pages in parallel
- **Real-time web dashboard** — live stat cards, queue depth chart, and last indexed URL updating via Server-Sent Events
- **Live search** — keyword search runs against the index while the crawler is still active
- **Back-pressure** — bounded queue automatically throttles workers when the system is under load
- **Thread-safe index** — all shared state protected by `threading.Lock`
- **Native Python only** — crawler uses `urllib` and `html.parser`, no Scrapy or BeautifulSoup

---

## Requirements

- Python 3.11+
- Flask (`pip install flask`)

No other dependencies.

---

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/google-in-a-day
cd google-in-a-day
pip install flask
```

---

## Running

```bash
python main.py
```

Then open **http://127.0.0.1:5000** in your browser.

You can also override the seed URL and depth from the command line:

```bash
python main.py --url "https://quotes.toscrape.com/" --depth 2
```

Optional `--url` / `--depth` only update `core.config` at process startup; you still start the crawl from the browser (**Start Crawl**).

---

## Usage

1. Open `http://127.0.0.1:5000`
2. Enter an Origin URL (e.g. `https://quotes.toscrape.com/`) and Max Depth (1–5)
3. Click **Start Crawl** — the dashboard activates and metrics update live
4. Type a query in the Search box and click **Search** to query the live index
5. Press `Ctrl+C` in the terminal to stop

Good seed URLs for testing:
- `https://quotes.toscrape.com/` — crawler-friendly, lots of links
- `https://books.toscrape.com/` — larger site, good for depth 2
- `https://crawler-test.com/` — designed for crawler testing

---

## Configuration

All tunable values live in `config.py`:

| Parameter | Default | Description |
|---|---|---|
| `SEED_URL` | `https://example.com/` | Default seed (overridden by UI or CLI) |
| `MAX_DEPTH` | `3` | Maximum crawl depth |
| `MAX_WORKERS` | `5` | Number of concurrent crawler threads |
| `QUEUE_MAX_SIZE` | `100` | Bounded queue size (back-pressure) |
| `REQUEST_DELAY_SEC` | `0.5` | Polite delay between requests per worker |
| `REQUEST_TIMEOUT_SEC` | `5.0` | HTTP request timeout |
| `SAME_DOMAIN_ONLY` | `True` | Restrict crawl to seed domain |
| `TOP_N_RESULTS` | `10` | Max search results returned |

---

## Architecture

```
google-in-a-day/
├── main.py           # Entry point: wires all components together
├── core/
│   ├── config.py     # All tunable constants
│   ├── index.py      # Thread-safe in-memory index (CrawlIndex)
│   ├── crawler.py    # Worker threads: fetch → parse → enqueue → store
│   ├── searcher.py   # Pure search function: keyword scoring over live index
│   ├── api.py        # Flask server: SSE stream, /start, /search routes
│   └── dashboard.py  # Optional CLI dashboard (terminal)
└── templates/
    └── dashboard.html  # Browser UI: stat cards, live chart, search
```

### How it works

1. `main.py` starts `MAX_WORKERS` `CrawlerWorker` threads and a Flask server
2. The browser hits `/start` with a seed URL — this seeds the queue and begins crawling
3. Each worker dequeues a `(url, origin_url, depth)` tuple, fetches the page with `urllib`, parses links with `html.parser`, and stores a `PageRecord` in `CrawlIndex`
4. New URLs are enqueued only if `mark_visited()` returns True (atomic check-and-add under a lock)
5. The browser connects to `/stream` (SSE) and receives index stats every 1.5 seconds
6. `/search` runs `core.searcher.search()` against the live index and returns ranked results

### Back-pressure

`queue.Queue(maxsize=QUEUE_MAX_SIZE)` is Python's built-in back-pressure mechanism. Workers calling `.put()` block automatically when the queue is full — no URLs are dropped, workers simply wait. The dashboard shows "THROTTLED" when queue depth exceeds 80% of capacity.

### Thread safety

All reads and writes to the shared index (`_store`, `_visited`) go through `CrawlIndex` methods which acquire a `threading.Lock`. No worker ever accesses raw dicts or sets directly. `mark_visited()` is atomic: the check and add happen inside a single lock acquisition.

---

## Project Deliverables

- `readme.md` — this file
- `product_prd.md` — full Product Requirements Document
- `recommendation.md` — production deployment roadmap

---

## Author

David Dogukan Erenel — Istanbul Technical University, AI Aided Computer Engineering, March 2026
