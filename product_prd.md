# Product Requirements Document (PRD)
## Project: "Google in a Day" — Web Crawler & Real-Time Search Engine

**Course:** AI Aided Computer Engineering — Istanbul Technical University  
**Date:** March 2026  
**Version:** 1.0

---

## 1. Overview

### 1.1 Purpose
This document defines the requirements for a functional web crawler and real-time search engine built in Python, using only language-native libraries. The system simulates the core indexing and querying pipeline of a search engine, demonstrating concurrent system design, back-pressure management, and thread-safe data access.

### 1.2 Background
Modern search engines like Google operate two core subsystems: an **indexer** that continuously discovers and stores web content, and a **searcher** that queries the index in real time. This project replicates those two subsystems at a small scale using Python concurrency primitives, without relying on high-level scraping frameworks.

### 1.3 Scope
- A concurrent web crawler (Indexer) that recursively follows links from a seed URL up to depth `k`
- A query engine (Searcher) that can run simultaneously with the indexer
- A real-time dashboard (UI/CLI) for system visibility
- Optional: persistence layer for resumable crawls

---

## 2. Goals & Non-Goals

### Goals
- Build a working crawler using only Python-native libraries (`urllib`, `html.parser`, `threading`, `queue`)
- Support concurrent indexing and searching without data corruption
- Implement back-pressure to prevent the system from overwhelming itself
- Provide a real-time dashboard showing crawl progress and queue state
- Produce clean, explainable, AI-assisted code with documented design decisions

### Non-Goals
- Crawling at production scale (millions of URLs)
- Full-text ranking algorithms (TF-IDF, PageRank) — a simple heuristic is sufficient
- JavaScript rendering (only static HTML pages will be crawled)
- Authentication or session handling for protected pages

---

## 3. Users & Stakeholders

| Role | Description |
|---|---|
| Student / Developer | Builds and runs the system locally; uses CLI/dashboard to monitor |
| Course Instructor | Evaluates architectural decisions, code quality, and AI stewardship |

---

## 4. Functional Requirements

### 4.1 Indexer (Web Crawler)

| ID | Requirement |
|---|---|
| I-01 | The crawler SHALL accept a seed URL and a maximum crawl depth `k` as inputs |
| I-02 | The crawler SHALL recursively follow all valid hyperlinks found on each page |
| I-03 | The crawler SHALL maintain a `visited` set to ensure no URL is crawled more than once |
| I-04 | The crawler SHALL use Python's `urllib.request` for HTTP fetching and `html.parser` for link extraction |
| I-05 | The crawler SHALL NOT use Scrapy, BeautifulSoup, requests, or any third-party scraping library |
| I-06 | The crawler SHALL store each indexed page as a record containing: `url`, `origin_url`, `depth`, `title`, and `word_frequency` map |
| I-07 | The crawler SHALL normalize URLs (strip fragments, resolve relative paths) before enqueuing |

### 4.2 Back-Pressure & Concurrency

| ID | Requirement |
|---|---|
| B-01 | The system SHALL use a bounded `queue.Queue` to limit the number of URLs queued at any time |
| B-02 | The system SHALL support a configurable number of worker threads (e.g., `MAX_WORKERS = 5`) |
| B-03 | Worker threads SHALL block (not crash) when the queue is full, implementing natural back-pressure |
| B-04 | All shared data structures (visited set, index store) SHALL be protected by `threading.Lock` or use thread-safe alternatives |
| B-05 | The system SHALL expose a throttle/rate-limit mechanism (e.g., configurable delay between requests per worker) |

### 4.3 Searcher (Query Engine)

| ID | Requirement |
|---|---|
| S-01 | The searcher SHALL accept a keyword query string as input |
| S-02 | The searcher SHALL return a ranked list of result triples: `(relevant_url, origin_url, depth)` |
| S-03 | Relevancy SHALL be determined by a simple heuristic: keyword frequency in page content + keyword presence in page title (title match weighted 2x) |
| S-04 | The searcher SHALL be able to run concurrently while the indexer is active, reading from a live index |
| S-05 | Search reads SHALL acquire a shared read lock to prevent reading partially written index entries |

### 4.4 System Visibility & Dashboard

| ID | Requirement |
|---|---|
| U-01 | A CLI dashboard SHALL display real-time metrics, refreshing every 1–2 seconds |
| U-02 | The dashboard SHALL show: URLs processed, URLs queued, current queue depth, and throttling status |
| U-03 | The dashboard SHALL show the most recently indexed URL |
| U-04 | A search prompt SHALL be accessible from the dashboard while crawling is in progress |

### 4.5 Persistence (Bonus)

| ID | Requirement |
|---|---|
| P-01 | The system SHOULD serialize the `visited` set and index to disk (e.g., JSON or SQLite) at regular intervals |
| P-02 | On startup, the system SHOULD detect and resume from a saved state if one exists |

---

## 5. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | The crawler should process at least 10 pages/min with default settings on a standard laptop |
| Reliability | The crawler SHALL handle HTTP errors (404, 500, timeouts) gracefully without crashing |
| Safety | The crawler SHALL respect a domain scope limit (e.g., only follow links within the same domain as the seed URL) |
| Maintainability | Code SHALL be modular: separate files for `crawler.py`, `searcher.py`, `index.py`, `dashboard.py`, and `main.py` |
| Explainability | Every major design choice SHALL be commented or documented so the developer can explain it without referring to AI |

---

## 6. System Architecture (High-Level)

```
┌─────────────────────────────────────────────────────┐
│                      main.py                        │
│         (entry point, config, orchestration)        │
└───────┬─────────────────────────────────┬───────────┘
        │                                 │
        ▼                                 ▼
┌───────────────┐                ┌─────────────────┐
│  crawler.py   │                │  searcher.py    │
│  (N workers,  │──── writes ───▶│  (reads index   │
│   threading)  │                │   concurrently) │
└───────┬───────┘                └─────────────────┘
        │
        ▼
┌───────────────┐
│   index.py    │
│ (thread-safe  │
│  data store)  │
└───────────────┘
        │
        ▼
┌───────────────┐
│ dashboard.py  │
│ (CLI real-time│
│  metrics)     │
└───────────────┘
```

---

## 7. Data Model

### Indexed Page Record
```python
{
  "url": "https://example.com/page",
  "origin_url": "https://example.com",
  "depth": 2,
  "title": "Page Title",
  "word_freq": {"python": 5, "crawler": 3, ...}
}
```

### Search Result Triple
```python
(relevant_url: str, origin_url: str, depth: int)
```

---

## 8. Configuration

All configurable values SHALL be defined in a `config.py` file:

| Parameter | Default | Description |
|---|---|---|
| `SEED_URL` | (user input) | Starting URL for the crawl |
| `MAX_DEPTH` | `3` | Maximum crawl depth |
| `MAX_WORKERS` | `5` | Number of concurrent crawler threads |
| `QUEUE_MAX_SIZE` | `100` | Maximum bounded queue size (back-pressure) |
| `REQUEST_DELAY_SEC` | `0.5` | Delay between requests per worker |
| `REQUEST_TIMEOUT_SEC` | `5` | HTTP request timeout |
| `SAME_DOMAIN_ONLY` | `True` | Restrict crawl to seed domain |

---

## 9. Grading Alignment

| Criteria | Weight | How This PRD Addresses It |
|---|---|---|
| Functionality | 40% | I-01 through S-05 cover all crawl and search behaviors |
| Architectural Sensibility | 40% | B-01 through B-05 define back-pressure and thread safety explicitly |
| AI Stewardship | 20% | Modular design and config externalization make code explainable |

---

## 10. Deliverables

- `readme.md` — Setup, run instructions, and architecture summary
- `product_prd.md` — This document
- `recommendation.md` — 2-paragraph production deployment roadmap
- Public GitHub repository with all source code

---

*End of PRD*
