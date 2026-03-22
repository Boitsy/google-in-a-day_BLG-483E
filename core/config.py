"""Tunable defaults for the crawler and searcher. Constants only — no logic."""

SEED_URL: str = "https://example.com/"
MAX_DEPTH: int = 3
MAX_WORKERS: int = 5
QUEUE_MAX_SIZE: int = 100
REQUEST_DELAY_SEC: float = 0.5
REQUEST_TIMEOUT_SEC: float = 5.0
SAME_DOMAIN_ONLY: bool = True
TOP_N_RESULTS: int = 10
