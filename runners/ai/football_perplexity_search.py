from pathlib import Path
from listeners.read.perplexity_search import PerplexitySearch

_PROMPT = (Path(__file__).parent / "football_search_prompt.txt").read_text()


class FootballPerplexitySearch(PerplexitySearch):
    _BLOCKED_DOMAINS = PerplexitySearch._BLOCKED_DOMAINS | {"mancity.com"}

    def build_prompt(self, topic: dict, today: str) -> str:
        query = topic.get("query", "football news")
        return _PROMPT.format(query=query, max_results=self.max_results_per_topic)
