# Creating a New Runner

A runner is a sport-specific implementation of the generic pipeline. The pipeline itself (`listeners/`) is reusable — you only need to provide the sport-specific pieces and wire them together.

---

## Folder structure

```
runners_{sport}/
  ai/
    taxonomy.py                  ← domain tree (competitions, clubs/teams, themes)
    {sport}_search_functions.py  ← builds the Perplexity prompt
    {sport}_search_prompt.txt    ← prompt template with {query} and {max_results}
    {sport}_perplexity_search.py ← subclass of PerplexitySearch, overrides build_prompt()
  appsettings.py                 ← all config for this sport (no imports)
  run_publisher.py               ← wires publisher pipeline
  run_subscriber.py              ← wires subscriber pipeline
```

---

## Step 1 — Define your taxonomy (`ai/taxonomy.py`)

The taxonomy drives two things: the Claude tool schema (what entities to extract) and the UI dropdowns.

```python
RUGBY_TREE = {
    "Premiership": {
        "clubs": ["Bath", "Bristol Bears", "Exeter Chiefs", ...],
        "themes": ["Transfers", "Injuries", "Results", "Fixtures"],
    },
    "Six Nations": {
        "clubs": [],
        "themes": ["Results", "Fixtures", "Tactics"],
    },
}
```

---

## Step 2 — Define your search topics (`ai/topics.py`)

Each topic is a Perplexity query + a label written to the queue.

```python
RUGBY_TOPICS = [
    {"query": "Premiership rugby latest news injuries team updates", "topic": "Breaking News"},
    {"query": "Premiership rugby transfer news signings contracts",  "topic": "Transfers"},
    {"query": "Six Nations results fixtures latest news",           "topic": "Six Nations"},
]
```

---

## Step 3 — Write the search prompt (`ai/{sport}_search_prompt.txt`)

Plain text with two placeholders. Perplexity will be instructed to write one paragraph per citation.

```
Find up to {max_results} recent rugby news articles about: {query}.
For each source you cite, write a separate paragraph starting with its citation number in brackets,
e.g. [1] Summary here. [2] Next summary here.
Include specific facts, names, scores, and dates. Do not merge sources into one block.
```

---

## Step 4 — Implement the search (`ai/{sport}_perplexity_search.py`)

Subclass `PerplexitySearch` and override `build_prompt()` to use your prompt file.

```python
from pipeline.read.perplexity_search import PerplexitySearch
from runners_rugby.ai.rugby_search_functions import build_rugby_search_prompt


class RugbyPerplexitySearch(PerplexitySearch):
    def build_prompt(self, topic: dict, today: str) -> str:
        return build_rugby_search_prompt(topic.get("query", "rugby news"), self.max_results_per_topic)
```

```python
# ai/rugby_search_functions.py
from pathlib import Path

_PROMPT = (Path(__file__).parent / "rugby_search_prompt.txt").read_text()

def build_rugby_search_prompt(query: str, max_results: int) -> str:
    return _PROMPT.format(query=query, max_results=max_results)
```

---

## Step 5 — Configure (`appsettings.py`)

No imports — pure literals only.

```python
SOURCE_NAME = "RugbyNewsSites"
SOURCE_TYPE = "rugby"

SEARCH_MODEL          = "sonar-pro"
MAX_RESULTS_PER_TOPIC = 10
MIN_CITATION_LENGTH   = 80
SEEN_URL_EXPIRY_DAYS  = 3

ENRICH_MODEL = "claude-haiku-4-5"

APP_NAME = "rugbyhub"

DB_SERVER = "localhost"
DB_NAME   = "RugbyHub"
DB_DRIVER = "ODBC Driver 17 for SQL Server"
```

---

## Step 6 — Wire the publisher (`run_publisher.py`)

The publisher fetches articles from Perplexity and writes them to `article_queue`.

```python
ArticlePipeline(
    reader=RugbyPerplexitySearch(
        api_key=os.environ["PERPLEXITY_API_KEY"],
        topics=RUGBY_TOPICS,
        model=settings.SEARCH_MODEL,
        max_results_per_topic=settings.MAX_RESULTS_PER_TOPIC,
        min_citation_length=settings.MIN_CITATION_LENGTH,
        seen_urls_path=SEEN_URLS_PATH,
        seen_url_expiry_days=settings.SEEN_URL_EXPIRY_DAYS,
    ),
    enricher=ArticleMapper(source_name=settings.SOURCE_NAME, source_type=settings.SOURCE_TYPE),
    writer=DbQueueWriter(
        handler=DbInsertHandler(engine=engine, table_name="article_queue", schema="dbo",
                                key_cols=["source_type", "source_name", "source_record_id"])
    ),
).run()
```

---

## Step 7 — Wire the subscriber (`run_subscriber.py`)

The subscriber reads from `article_queue`, tags with Claude, writes to `articles`.

```python
ArticlePipeline(
    reader=DbQueueReader(engine=engine, source_type=settings.SOURCE_TYPE),
    enricher=Enricher(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        taxonomy=RUGBY_TREE,
        model=settings.ENRICH_MODEL,
    ),
    writer=ArticleWriter(engine=engine),
).run()
```

---

## What you never touch

These are generic and shared across all runners:

| Component | Location |
|---|---|
| `ArticlePipeline` | `listeners/article_pipeline.py` |
| `PerplexitySearch` | `listeners/read/perplexity_search.py` |
| `WebSearchReader` | `listeners/read/web_search_reader.py` |
| `DbQueueReader` | `listeners/queue/db/db_queue_reader.py` |
| `DbQueueWriter` | `listeners/queue/db/db_queue_writer.py` |
| `Enricher` | `listeners/enrich/enricher.py` |
| `ArticleWriter` | `listeners/save/article_writer.py` |
| `DbInsertHandler` | `utils/scraper/persistence/db_insert_handler.py` |
| `build_engine` | `db/db.py` |

The only things you write for a new sport are the taxonomy, topics, prompt, and search subclass.
