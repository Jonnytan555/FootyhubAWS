import json
import logging

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path


class WebSearchReader(ABC):
    """Base class for web search readers. Handles deduplication with expiry; subclasses implement search."""

    def __init__(
        self,
        topics: list[dict],
        seen_urls_path: str | None = None,
        seen_url_expiry_days: int = 3,
    ) -> None:
        self.topics = topics
        self.seen_urls_path = Path(seen_urls_path) if seen_urls_path else None
        self.seen_url_expiry_days = seen_url_expiry_days
        self._seen: dict[str, str] = self._load_seen_urls()

    def read(self) -> list[dict]:
        articles = []

        for topic in self.topics:
            logging.info("Searching: %s", topic.get("query"))

            for article in self.search(topic):
                url = article.get("url")

                if url and url in self._seen:
                    continue

                if url:
                    self._seen[url] = datetime.now(timezone.utc).date().isoformat()

                articles.append(article)

        self._save_seen_urls()
        return articles

    @abstractmethod
    def search(self, topic: dict) -> list[dict]:
        """Search for articles on the given topic and return a list of article dicts."""

    def _load_seen_urls(self) -> dict[str, str]:
        if not (self.seen_urls_path and self.seen_urls_path.exists()):
            return {}

        text = self.seen_urls_path.read_text().strip()
        if not text:
            return {}
        raw = json.loads(text)

        if isinstance(raw, list):
            # migrate old format (plain list) — treat all as today so they expire naturally
            today = datetime.now(timezone.utc).date().isoformat()
            return {url: today for url in raw}

        cutoff = (datetime.now(timezone.utc).date() - timedelta(days=self.seen_url_expiry_days)).isoformat()
        fresh = {url: date for url, date in raw.items() if date >= cutoff}

        expired = len(raw) - len(fresh)
        if expired:
            logging.info("Expired %d seen URLs older than %d days", expired, self.seen_url_expiry_days)

        return fresh

    def _save_seen_urls(self) -> None:
        if self.seen_urls_path:
            self.seen_urls_path.write_text(json.dumps(self._seen, indent=2))
