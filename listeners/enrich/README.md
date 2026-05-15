# Enrichment — How It Works

The enrichment stage is where AI enters the pipeline. Raw articles arrive from the queue with a title and body text. This stage sends each one to Claude, which reads the text and extracts structured labels — competition, theme, clubs, players. Those labels are merged back into the article dict and saved to `dbo.articles`.

---

## Files

| File | Role |
|---|---|
| `claude_enricher.py` | The enricher — loops articles, calls Claude, handles failures |
| `tagger_tools.py` | The JSON schema that constrains Claude's output |
| `tagger_system.txt` | The system prompt that tells Claude its role |

---

## `tagger_tools.py` — line by line

```python
def build_tag_tool(taxonomy: dict) -> dict:
```
Takes the `FOOTBALL_TREE` dict (passed in from `run_subscriber.py`) and returns a Claude tool definition. Called once at startup when `ClaudeEnricher.__init__` runs — not on every article.

```python
    competitions = list(taxonomy.keys())
    clubs  = sorted({club  for comp in taxonomy.values() for club  in comp.get("clubs",  [])})
    themes = sorted({theme for comp in taxonomy.values() for theme in comp.get("themes", [])})
```
These three lines flatten `FOOTBALL_TREE` into three plain lists. The `{}` makes a set first (removes duplicates), then `sorted()` gives alphabetical order. If you add a club to `FOOTBALL_TREE`, it automatically appears in `clubs` next time the subscriber starts — no other file needs changing.

```python
    return {
        "name": "tag_article",
        "description": "Extract football entities from article text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "competition": {
                    "type": ["string", "null"],
                    "enum": competitions + [None],
```
`"enum"` is the key constraint. Claude can **only** return one of the values in this list for `competition`. If the article isn't clearly about a specific competition, Claude must return `null` — it cannot invent a value. This is what makes the output reliable: Claude is picking from a dropdown, not writing free text.

```python
                "clubs": {
                    "type": "array",
                    "items": {"type": "string", "enum": clubs},
```
`clubs` is an array rather than a single string so Claude can return multiple clubs when an article mentions more than one — e.g. a transfer article about Arsenal signing a Chelsea player returns `["Arsenal", "Chelsea"]`. Each item in the array is still constrained to the enum.

```python
                "players": {
                    "type": "array",
                    "items": {"type": "string"},
```
No `enum` here — you can't list every footballer in advance. Claude writes the player names as free text. This means player names come back in whatever format Claude produces ("Ben White", "B. White", "Benjamin White") rather than a controlled vocabulary.

```python
            "required": ["competition", "theme", "clubs", "players"],
```
All four fields must be present in Claude's response — no field can be omitted. `competition` and `theme` can be `null` (allowed by the enum), but they must be explicitly included. `clubs` and `players` can be empty arrays `[]` but must be present.

---

## `claude_enricher.py` — line by line

### Startup

```python
_SYSTEM = (Path(__file__).parent / "tagger_system.txt").read_text()
```
Reads the system prompt from the `.txt` file next to this file, at import time. `__file__` is the path to `claude_enricher.py` itself, `.parent` is the `enrich/` folder, so this always finds `tagger_system.txt` regardless of where you run the script from.

```python
class ClaudeEnricher:
    def __init__(self, api_key: str, taxonomy: dict, model: str = "claude-haiku-4-5") -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self._tool = build_tag_tool(taxonomy)
```
Three things happen at construction:
- `anthropic.Anthropic(api_key=...)` — creates the API client (one connection, reused for all articles)
- `self.model` — stored so `_tag()` can use it; defaults to Haiku (fast and cheap for extraction)
- `build_tag_tool(taxonomy)` — builds the schema once and stores it as `self._tool`; this dict is sent to Claude unchanged on every call

### The loop — `enrich()`

```python
    def enrich(self, articles: list[dict]) -> list[dict]:
        enriched = []
        failed_count = 0

        for article in articles:
            try:
                tags = self._tag(article.get("body_text") or article.get("title") or "")
```
`article.get("body_text") or article.get("title") or ""` — picks the best available text in order of preference. `body_text` is the full article content from Perplexity. If that's empty or None, falls back to the title. If that's also empty, sends an empty string (Claude will return nulls, article gets tagged as failed downstream).

```python
                enriched.append({**article, **tags})
```
`**article` spreads all the original article fields, `**tags` spreads the returned tag fields on top. If a tag key matches an existing field (e.g. `competition` was already `None` in the queue row), the tag value overwrites it. This is how the enriched dict is built — one merged dict, not two separate objects.

```python
            except Exception as e:
                logging.warning("Enricher failed %s: %s", article.get("source_record_id"), e)
                enriched.append({**article, "_tagging_failed": True})
                failed_count += 1
```
On any exception (API timeout, network error, malformed response), the article is still appended — with `_tagging_failed: True` instead of tags. It is **not** dropped. The pipeline checks for this flag after `enrich()` returns and routes flagged articles to `mark_failed()` on the queue reader, so they get retried on the next subscriber run.

### The Claude call — `_tag()`

```python
    def _tag(self, text: str) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": text[:4000]}],
            tools=[self._tool],
            tool_choice={"type": "any"},
        )
```
- `max_tokens=512` — caps the response length. Tag extraction needs very few tokens; 512 is generous but prevents runaway cost.
- `text[:4000]` — truncates the article to 4000 characters. Claude's context window is much larger, but most tagging decisions can be made from the first few paragraphs. Saves tokens on long articles.
- `tools=[self._tool]` — passes the schema as a list (Claude supports multiple tools; we only use one).
- `tool_choice={"type": "any"}` — forces Claude to use one of the provided tools rather than replying in plain text. Without this, Claude might write "This article is about Arsenal..." instead of filling in the schema.

```python
        for block in response.content:
            if block.type == "tool_use" and block.name == "tag_article":
                inp = block.input
```
Claude's response is a list of content blocks — it can mix text and tool calls in one response. The loop finds the `tool_use` block named `tag_article`. `block.input` is a plain Python dict matching the schema exactly.

```python
                clubs   = inp.get("clubs", []) or []
                players = inp.get("players", []) or []
```
`inp.get("clubs", []) or []` handles two edge cases: the key being missing (returns `[]`) and the key being present but set to `None` (the `or []` converts that to `[]`). Without this, `", ".join(None)` would crash.

```python
                return {
                    "competition":      inp.get("competition"),
                    "theme":            inp.get("theme"),
                    "club":             clubs[0]  if clubs   else None,
                    "player_name":      players[0] if players else None,
                    "clubs_mentioned":  ", ".join(clubs),
                    "players_mentioned": ", ".join(players),
                }
```
Two columns per concept — `club` / `clubs_mentioned` and `player_name` / `players_mentioned`:
- `club` and `player_name` are the **primary** values (single strings), kept for the DB columns that were there from the start
- `clubs_mentioned` and `players_mentioned` are the **full** values (comma-separated), added later to capture multi-club articles

`clubs[0] if clubs else None` — takes the first club as the primary. If Claude returned `["Arsenal", "Chelsea"]`, `club = "Arsenal"` and `clubs_mentioned = "Arsenal, Chelsea"`.

```python
        return {
            "competition": None, "theme": None,
            "club": None, "player_name": None,
            "clubs_mentioned": "", "players_mentioned": "",
        }
```
This only runs if no `tool_use` block was found — Claude responded in plain text despite `tool_choice: "any"`. Returns safe nulls so the article can still be written to the DB without crashing. In practice this rarely happens.
