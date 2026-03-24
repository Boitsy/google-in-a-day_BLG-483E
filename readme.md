# 🕸️ Google in a Day

A functional web crawler, indexer, and real-time search engine built natively with Python — no third-party scraping libraries.

Built for the **AI Aided Computer Engineering** course at Istanbul Technical University.

---

## ⚡ Features

- **Concurrent Crawler:** A configurable pool of worker threads crawls pages in parallel.
- **Real-Time Dashboard:** Flask-powered live status dashboard with Server-Sent Events (SSE) tracking queue depth, indexed pages, and active URLs.
- **RESTful API:** Run queries via the modern `GET /search` endpoint or the real-time UI.
- **Dual-Port Server:** Hosts the API simultaneously on `127.0.0.1:5000` and `127.0.0.1:3600`.
- **Index Persistence:** Automatically saves the parsed inverted index to `data/storage/p.data` when crawling finishes.
- **Live Search:** Execute keyword searches against the index natively while the crawler is still active.
- **Back-Pressure Mechanism:** Bounded queues gracefully throttle worker threads under heavy loads.
- **Native Python:** Implemented purely with `urllib`, `html.parser`, and core libraries. No Scrapy or BeautifulSoup required.

---

## 🚀 Quick Start

### Requirements
- Python `3.11+`
- Flask (`pip install flask`)

### Setup and Run
```bash
git clone https://github.com/Boitsy/google-in-a-day_BLG-483E.git
cd google-in-a-day_BLG-483E
pip install flask
python main.py
```

Then, open **http://127.0.0.1:5000** (or **http://127.0.0.1:3600**) in your web browser.

You can also override the seed URL and depth from the command line:
```bash
python main.py --url "https://quotes.toscrape.com/" --depth 2
```

> **Note:** Providing `--url` and `--depth` via the CLI only updates `core.config` at startup. You must still click **Start Crawl** in the browser to begin.

---

## 📖 Usage

1. Open `http://127.0.0.1:5000` or `http://127.0.0.1:3600`.
2. Enter an **Origin URL** (e.g., `https://quotes.toscrape.com/`) and a **Max Depth** (1–5).
3. Click **Start Crawl** — the dashboard activates, and real-time metrics begin streaming.
4. Use the **Search** box or hit the `GET /search?query={your_term}` endpoint to query the live index.
5. Once the queue drains, the inverted index is securely persisted to disk at `data/storage/p.data`.
6. Press `Ctrl+C` in the terminal to stop the crawler gracefully.

**Crawler-friendly Seed URLs:**
- `https://quotes.toscrape.com/` — Lots of text and pagination links.
- `https://books.toscrape.com/` — A larger site, ideal for depth 2 or 3.
- `https://crawler-test.com/` — Designed explicitly for crawler verification.

---

## ⚙️ Configuration

Tune crawler behavior via `core/config.py`:

| Parameter | Default | Description |
|---|---|---|
| `SEED_URL` | `https://example.com/` | Default seed (overridden by UI or CLI) |
| `MAX_DEPTH` | `3` | Maximum crawl depth |
| `MAX_WORKERS` | `5` | Number of concurrent crawler threads |
| `QUEUE_MAX_SIZE` | `100` | Bounded queue size for back-pressure |
| `REQUEST_DELAY_SEC` | `0.5` | Polite delay between requests per worker |
| `REQUEST_TIMEOUT_SEC` | `5.0` | HTTP request timeout |
| `SAME_DOMAIN_ONLY` | `True` | Restricts the crawl rigidly to the seed domain |
| `TOP_N_RESULTS` | `10` | Maximum search results returned by the engine |

---

## 🏗️ Architecture

```text
google-in-a-day/
├── main.py           # Core entry point wiring the threads and dual-servers
├── data/storage/     # Saved index data (e.g. p.data)
├── core/
│   ├── config.py     # Centralized tunable constants
│   ├── index.py      # Thread-safe inverted index manager
│   ├── crawler.py    # Multi-threaded worker pipeline
│   ├── searcher.py   # TF-IDF / Frequency based keyword scoring
│   ├── storage.py    # Persistence logic to save the index to disk
│   └── api.py        # Flask App: dual-port daemon, SSE stream, persistence hooks
└── templates/
    └── dashboard.html# Real-time UI with D3/Chart options
```

### Inner Workings
1. **Concurrency:** `main.py` launches `MAX_WORKERS` tracking threads alongside dual daemonized Flask servers.
2. **Execution Pipeline:** Workers pull URLs from the queue, fetch via `urllib`, parse HTML, build word frequencies, and commit `PageRecords` to the synchronized `CrawlIndex`.
3. **Thread Safety:** All index interactions use `threading.Lock`. Atomic validation ensures pages are indexed exactly once.
4. **Data Persistence:** The `/start` API triggers a background daemon that `.join()`s the URL queue. Once the crawl concludes, it triggers `save_index()`. 

---

## 📑 Project Deliverables

- [`readme.md`](./readme.md) — Documentation
- `product_prd.md` — Complete Product Requirements Document
- `recommendation.md` — Roadmap for production-scale deployment
