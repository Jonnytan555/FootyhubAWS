import anthropic, os, json
from pathlib import Path

from api.ai.tools import TOOLS
from api.ai.article_tools import search_articles, get_article

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
SYSTEM_PROMPT = (Path(__file__).parent.parent / "ai/system_prompt.txt").read_text()
TOOL_MAP = {"search_articles": search_articles, "get_article": get_article}


def chat(messages: list[dict]) -> tuple[str, dict | None]:
    filter_action = None

    while True:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
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
                else:
                    result = TOOL_MAP[block.name](**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
        messages.append({"role": "user", "content": tool_results})


