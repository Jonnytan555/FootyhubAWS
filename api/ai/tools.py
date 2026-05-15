TOOLS = [
    {
        "name": "set_filter",
        "description": "Update the feed filters to show articles for a specific club, competition, or theme. Call this when the user asks to see, filter, or show news for a specific team, competition, or topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "club":        {"type": "string"},
                "competition": {"type": "string"},
                "theme":       {"type": "string"},
            },
        },
    },
    {
        "name": "search_articles",
        "description": "Search football articles by keyword, club, competition, or theme.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":       {"type": "string", "description": "Search term"},
                "club":        {"type": "string"},
                "competition": {"type": "string"},
                "theme":       {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_article",
        "description": "Fetch the full body text of a specific article by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "article_id": {"type": "integer"},
            },
            "required": ["article_id"],
        },
    },
]