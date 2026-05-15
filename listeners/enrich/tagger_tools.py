def build_tag_tool(taxonomy: dict) -> dict:
    """Build the tag_article Claude tool schema from the enrichment taxonomy."""

    competitions = list(taxonomy.keys())
    clubs  = sorted({club  for comp in taxonomy.values() for club  in comp.get("clubs",  [])})
    themes = sorted({theme for comp in taxonomy.values() for theme in comp.get("themes", [])})

    return {
        "name": "tag_article",
        "description": "Extract football entities from article text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "competition": {
                    "type": ["string", "null"],
                    "enum": competitions + [None],
                    "description": "Football competition the article is primarily about.",
                },
                "theme": {
                    "type": ["string", "null"],
                    "enum": themes + [None],
                    "description": "Primary theme of the article.",
                },
                "clubs": {
                    "type": "array",
                    "items": {"type": "string", "enum": clubs},
                    "description": "All football clubs mentioned in the article.",
                },
                "players": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "All players mentioned by full name.",
                },
            },
            "required": ["competition", "theme", "clubs", "players"],
        },
    }
