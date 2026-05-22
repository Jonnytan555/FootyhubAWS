import anthropic, os, json
from pathlib import Path

from api.ai.tools import TOOLS
from api.ai.article_tools import search_articles, get_article
from api.web.queries import save_favourite_club

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
_BASE_PROMPT = (Path(__file__).parent.parent / "ai/system_prompt.txt").read_text()
TOOL_MAP = {"search_articles": search_articles, "get_article": get_article}


def _build_prompt(favourite_club: str | None) -> str:
    if favourite_club:
        return _BASE_PROMPT + f"\n\nThe user's favourite club is {favourite_club}. When they ask general questions without specifying a club, search for {favourite_club} news first."
    return _BASE_PROMPT


def chat(messages: list[dict], user_id: int = 0, favourite_club: str | None = None) -> tuple[str, dict | None]:
    filter_action = None

    while True:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            system=_build_prompt(favourite_club),
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = next(b.text for b in response.content if hasattr(b, "text"))
            return text, filter_action

        # Claude wants to use a tool
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []

        for block in response.content:
            if block.type == "tool_use":
                if block.name == "set_filter":
                    filter_action = block.input
                    result = {"status": "filters updated"}
                elif block.name == "set_favourite_club":
                    club = str(block.input["club"])
                    save_favourite_club(user_id, club)
                    favourite_club = club
                    result = {"status": f"Favourite club saved as {club}"}
                else:
                    result = TOOL_MAP[block.name](**block.input)
                content = json.dumps(result) if result else "no results found"
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})


