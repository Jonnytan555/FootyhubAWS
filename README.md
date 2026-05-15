# FootyHub

A full-stack football news aggregator with an AI-powered chatbot. Articles are automatically scraped, enriched with metadata by Claude, and surfaced in a filterable feed. Logged-in users can like articles and chat with an AI assistant that searches the article database in real time.

---

## Features

- **Automated news pipeline** — publisher scrapes articles via Perplexity search; subscriber enriches each with Claude Haiku (tagging competition, club, players, theme) and writes to the database
- **Filterable feed** — filter by competition, club, or theme with instant HTMX partial swaps (no page reload)
- **Authentication** — register/login modal overlay; JWT stored in an HttpOnly cookie
- **Article likes** — per-user likes with instant HTMX toggle
- **AI chatbot** — floating chat panel backed by Claude Opus; Claude autonomously searches the article database using tool use to answer questions in real time

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI + Jinja2 + HTMX |
| AI | Anthropic Claude (Opus 4 for chat, Haiku for enrichment) |
| Database | SQL Server via SQLAlchemy |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Scheduler | APScheduler (cron-based) |
| Message queue | ActiveMQ (STOMP protocol) |
| Search | Perplexity API |

---

## Architecture

```
Perplexity API
      │
      ▼
 Publisher  (runners/)
 Searches football topics → writes to article_queue table
      │
      ▼
 Subscriber  (listeners/)
 Claude Haiku enriches each article
 Tags: competition, club, players_mentioned, theme
      │
      ▼
 dbo.articles table
      │
      ▼
 FastAPI web app  (api/)
 Feed · Filters · Auth · Likes · AI Chat
```

---

## AI Chatbot — How It Works

The chatbot uses Claude's **tool use** (agentic loop). Claude is given two tools:

- `search_articles(query, club, competition, theme)` — full-text search across the articles table
- `get_article(article_id)` — fetch the complete body text of one article

When a user asks a question, Claude autonomously decides whether to search, which filters to apply, and whether to fetch a full article before forming its answer. The orchestration is a simple `while True` loop — no framework needed.

```python
while True:
    response = client.messages.create(model=..., tools=TOOLS, messages=messages)

    if response.stop_reason == "end_turn":
        return response  # Claude is done

    # Claude called a tool — run it and feed the result back
    messages.append({"role": "assistant", "content": response.content})
    tool_results = [run_tool(block) for block in response.content if block.type == "tool_use"]
    messages.append({"role": "user", "content": tool_results})
```

---

## Project Structure

```
api/
  app.py                      — FastAPI entry point
  web/
    routes.py                 — all route handlers
    queries.py                — database queries
    auth.py                   — JWT + password hashing
    models.py                 — Pydantic request models
    chat_service.py           — Claude agentic loop
  ai/
    tools.py                  — tool definitions (JSON schema)
    article_tools.py          — tool implementations (DB queries)
    system_prompt.txt         — Claude system prompt
  templates/
    base.html                 — shared layout + all CSS
    feed.html                 — main feed page
    partials/
      article_list.html       — article cards (HTMX partial)
      chat_panel.html         — floating chat UI
      auth_modal.html         — login/register overlay

listeners/                    — subscriber pipeline (enrichment)
runners/                      — publisher + scheduler
sql/                          — database schema scripts
utils/                        — shared DB + scraper utilities
```

---

## Setup

### Prerequisites

- Python 3.11+
- SQL Server (local or remote)
- [Anthropic API key](https://console.anthropic.com/)
- [Perplexity API key](https://www.perplexity.ai/) (for the publisher)
- ODBC Driver 17 for SQL Server

### Install dependencies

```bash
pip install -r requirements.txt
```

### Environment variables

```bash
cp .env.example .env
```

Edit `.env` with your API keys and JWT secret.

### Database

Run the scripts in `sql/` against your SQL Server instance to create the required tables (`articles`, `article_queue`, `users`, `article_likes`, `chat_messages`).

### Run the web app

```bash
python api/app.py
```

Open [http://localhost:8000](http://localhost:8000)

### Run the pipeline

```bash
# Scrape articles and add to queue
python runners/run_publisher.py

# Enrich queued articles with Claude and save to articles table
python runners/run_subscriber.py

# Or run both on a schedule (every 6 hours by default)
python runners/scheduler/main.py
```

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `dbo.articles` | Enriched articles (competition, club, theme, players) |
| `dbo.article_queue` | Raw scraped articles pending enrichment |
| `dbo.users` | Registered users |
| `dbo.article_likes` | Per-user article likes |
| `dbo.chat_messages` | Per-user chat history |
