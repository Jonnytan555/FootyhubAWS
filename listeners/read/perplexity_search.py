import re
import logging
import httpx
from urllib.parse import urlparse

from pathlib import Path
from datetime import datetime, timezone
from listeners.read.web_search_reader import WebSearchReader

_PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
_PROMPT = (Path(__file__).parent / "search_prompt.txt").read_text()
_BLOCKED_DOMAINS = {"youtube.com", "youtu.be"}

class PerplexitySearch(WebSearchReader):

    def __init__(
        self,
        api_key: str,
        topics: list[dict],
        model: str = "sonar",
        max_results_per_topic: int = 5,
        min_citation_length: int = 80,
        base_url: str = _PERPLEXITY_URL,
        seen_urls_path: str | None = None,
        seen_url_expiry_days: int = 3,
        prompt_path: Path | None = None,
        extra_blocked_domains: set[str] | None = None,
    ) -> None:
        super().__init__(topics, seen_urls_path, seen_url_expiry_days)
        self.api_key = api_key
        self.model = model
        self.max_results_per_topic = max_results_per_topic
        self.min_citation_length = min_citation_length
        self.base_url = base_url
        self._prompt = prompt_path.read_text() if prompt_path else _PROMPT
        self._blocked = _BLOCKED_DOMAINS | (extra_blocked_domains or set())

    def search(self, topic: dict) -> list[dict]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        prompt = self.build_prompt(topic, today)
        content, citations = self._fetch(prompt)
        citation_content = self._parse_citations(content)
        return self._build_articles(topic, today, content, citations, citation_content)

    def build_prompt(self, topic: dict, today: str) -> str:
        return self._prompt.format(
            query=topic.get("query", "news"),
            max_results=self.max_results_per_topic,
        )

    def _build_articles(self, topic: dict, today: str, content: str, citations: list[str], citation_content: dict[int, str]) -> list[dict]:
        query = topic.get("query", "football news")
        results = []

        for idx, url in enumerate(citations[:self.max_results_per_topic], start=1):
            hostname = urlparse(url).hostname or ""
            if any(hostname == d or hostname.endswith("." + d) for d in self._blocked):
                logging.info("Skipping [%d] %s — blocked domain", idx, url)
                continue
            citation_text = citation_content.get(idx, "")
            if len(citation_text) < self.min_citation_length:
                logging.warning("Skipping [%d] %s — citation text too short (%d chars)", idx, url, len(citation_text))
                continue
            results.append({
                "title":        f"{query} — {today}",
                "url":          url,
                "content":      citation_text,
                "published_at": today,
                "topic":        topic.get("topic"),
            })

        return results

    def _fetch(self, prompt: str) -> tuple[str, list[str]]:
        response = httpx.post(
            self.base_url,
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "search_recency_filter": "week",
            },
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        citations = data.get("citations", [])
        return content, citations

    def _parse_citations(self, content: str) -> dict[int, str]:
        parts = re.split(r'\[(\d+)\]', content)
        result: dict[int, str] = {}
        i = 1
        while i < len(parts) - 1:
            try:
                result[int(parts[i])] = parts[i + 1].strip()
                i += 2
            except (ValueError, IndexError):
                i += 1
        return result
