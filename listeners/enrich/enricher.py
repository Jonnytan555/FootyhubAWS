import logging
import anthropic
from pathlib import Path
from retry import retry

from listeners.enrich.tagger_tools import build_tag_tool

_SYSTEM = (Path(__file__).parent / "tagger_system.txt").read_text()


class Enricher:
    def __init__(self, api_key: str, taxonomy: dict, model: str = "claude-haiku-4-5") -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self._tool = build_tag_tool(taxonomy)

    def enrich(self, articles: list[dict]) -> list[dict]:
        enriched = []
        failed_count = 0

        for article in articles:
            try:
                tags = self._tag(article.get("body_text") or article.get("title") or "")
                
                logging.info(
                    "Tagged [%s] → competition=%s club=%s player=%s theme=%s",
                    article.get("source_record_id", "?")[:60],
                    tags.get("competition"), tags.get("club"),
                    tags.get("player_name"), tags.get("theme"),
                )

                enriched.append({**article, **tags})
                
            except Exception as e:
                logging.warning("Enricher failed %s: %s", article.get("source_record_id"), e)
                enriched.append({**article, "_tagging_failed": True})
                failed_count += 1

        enriched = self._dedup(enriched)
        logging.info("Enrichment complete — tagged: %d, failed: %d", len(enriched) - failed_count, failed_count)
        return enriched

    @retry(exceptions=(anthropic.APIStatusError, anthropic.APIConnectionError), tries=3, delay=10, backoff=2, logger=logging.getLogger())
    def _tag(self, text: str) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": text[:4000]}],
            tools=[self._tool],
            tool_choice={"type": "any"},
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == "tag_article":
                inp = block.input
                clubs   = inp.get("clubs", []) or []
                players = inp.get("players", []) or []
                return {
                    "competition":      inp.get("competition"),
                    "theme":            inp.get("theme"),
                    "club":             clubs[0]  if clubs   else None,
                    "player_name":      players[0] if players else None,
                    "clubs_mentioned":  ", ".join(clubs),
                    "players_mentioned": ", ".join(players),
                }
        return {
            "competition": None, "theme": None,
            "club": None, "player_name": None,
            "clubs_mentioned": "", "players_mentioned": "",
        }
    
    def _dedup(self, articles: list[dict]) -> list[dict]:
        keyed: dict[tuple, dict] = {}
        unkeyed: list[dict] = []

        for article in articles:
            player = article.get("player_name")
            if not player:
                unkeyed.append(article)
                continue
            key = (player, article.get("club"), article.get("theme"), article.get("topic"))
            existing = keyed.get(key)
            if existing is None or len(article.get("body_text") or "") > len(existing.get("body_text") or ""):
                keyed[key] = article

        result = list(keyed.values()) + unkeyed
        dropped = len(articles) - len(result)
        if dropped:
            logging.info("Deduped %d duplicate stories (same player/club/theme)", dropped)
        return result
