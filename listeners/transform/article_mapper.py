class FootballArticleMapper:
    """Maps PerplexitySearch article dicts to the article_queue column shape."""

    def __init__(
        self,
        source_type: str = "web",
        source_name: str = "FootballNewsSites",
        competition: str = "Premier League",
    ) -> None:
        self.source_type = source_type
        self.source_name = source_name
        self.competition = competition

    def enrich(self, results: list[dict]) -> list[dict]:
        return [
            {
                "source_type":      self.source_type,
                "source_name":      self.source_name,
                "source_record_id": item.get("url"),
                "source_url":       item.get("url"),
                "title":            item.get("title"),
                "body_text":        item.get("content"),
                "published_at":     item.get("published_at"),
                "topic":            item.get("topic"),
                "competition":      self.competition,
                "club":             None,
                "player_name":      None,
            }
            for item in results
            if item.get("url")
        ]
