# FootyhubAWS

A full-stack football news aggregator with an AI-powered chatbot, running on AWS. Articles are fetched via Perplexity, enriched by Claude, queued through SQS, stored in PostgreSQL, and served through a FastAPI/HTMX web app.

---

## Features

- **Automated news pipeline** — publisher fetches articles via Perplexity; subscriber enriches each with Claude (tagging competition, club, players, theme) and writes to the database
- **Filterable feed** — filter by competition, club, or theme with instant HTMX partial swaps (no page reload)
- **Authentication** — register/login modal overlay; JWT stored in an HttpOnly cookie
- **Article likes** — per-user likes with instant HTMX toggle
- **AI chatbot** — floating chat panel backed by Claude Opus; searches the article database in real time using tool use
- **Favourite club** — users can tell the chatbot their favourite club; it personalises all responses accordingly

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI + Jinja2 + HTMX |
| AI | Anthropic Claude (Opus 4 for chat, Haiku for enrichment) |
| Article search | Perplexity API |
| Database | PostgreSQL (installed on EC2) |
| Message queue | AWS SQS |
| Auth | JWT (python-jose) + bcrypt |
| Scheduler | APScheduler |
| Server | EC2 t3.micro, Ubuntu 22.04 |

---

## Architecture

```
Perplexity API
      │
      ▼
 run_publisher.py  ──►  AWS SQS  ──►  run_subscriber.py
 (fetch articles)         queue        (enrich with Claude)
                                              │
                                              ▼
                                    PostgreSQL (on EC2)
                                              │
                                              ▼
                                    FastAPI web app (HTMX)
                                     + Claude AI chatbot
```

Everything runs on a single EC2 t3.micro instance (free tier).

---

## AI Chatbot — How It Works

The chatbot uses Claude's **tool use** (agentic loop). Claude is given tools to search articles and save user preferences:

- `search_articles(query, club, competition, theme)` — full-text search across the articles table
- `get_article(article_id)` — fetch the complete body text of one article
- `set_favourite_club(club)` — persist the user's preferred club; used to personalise future responses

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

## Database Schema

| Table | Purpose |
|-------|---------|
| `articles` | Enriched, published football articles |
| `article_queue` | Raw articles awaiting enrichment |
| `users` | Registered users + favourite club |
| `article_likes` | Per-user article likes |
| `chat_messages` | Per-user chat history |

---

## Project Structure

```
api/
  app.py                      — FastAPI entry point
  web/
    routes.py                 — all route handlers
    queries.py                — database queries
    auth.py                   — JWT + password hashing
    chat_service.py           — Claude agentic loop
  ai/
    tools.py                  — tool definitions (JSON schema)
    article_tools.py          — tool implementations
    system_prompt.txt         — Claude system prompt
  templates/
    feed.html                 — main feed page
    partials/                 — HTMX partials (articles, chat, auth)

listeners/                    — subscriber pipeline (SQS → enrich → save)
  queue/sqs/                  — SQSQueueConsumer + SQSQueueWriter
runners/                      — publisher + scheduler
sql/
  postgres_schema.sql         — database table definitions
deploy/
  footyhub-web.service        — systemd service (web app)
  footyhub-scheduler.service  — systemd service (scheduler)
  nginx.conf                  — nginx reverse proxy config
  iam-policy.json             — IAM policy for EC2 role
utils/                        — shared DB utilities
```

---

## EC2 Deployment (full guide)

### 1. Launch EC2 instance

- **AMI:** Ubuntu 22.04 LTS
- **Instance type:** t3.micro (free tier)
- **Key pair:** create and download `.pem` file — keep it safe
- **Security group inbound rules:**
  - SSH (port 22) — your IP
  - HTTP (port 80) — 0.0.0.0/0
  - Custom TCP (port 8000) — 0.0.0.0/0

### 2. SSH into the instance

```powershell
ssh -i "C:\path\to\your-key.pem" ubuntu@<ec2-public-ip>
```

### 3. Install dependencies

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv postgresql nginx git
```

### 4. Set up PostgreSQL

```bash
sudo -u postgres psql
```

Inside psql:
```sql
CREATE DATABASE footyhub;
CREATE USER footyhub WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE footyhub TO footyhub;
\q
```

Grant schema permissions:
```bash
sudo -u postgres psql -d footyhub
```
```sql
GRANT ALL ON SCHEMA public TO footyhub;
\q
```

### 5. Clone the repo

```bash
git clone https://github.com/Jonnytan555/FootyhubAWS.git
cd FootyhubAWS
```

### 6. Create virtual environment and install packages

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Note:** Ubuntu 26.04 ships with Python 3.14. Some package versions are incompatible — run this after install:
> ```bash
> pip install "fastapi==0.115.5" "starlette==0.41.3"
> ```

### 7. Create the database tables

```bash
psql -h localhost -U footyhub -d footyhub -f sql/postgres_schema.sql
```

### 8. Configure environment variables

```bash
nano .env
```

```
ANTHROPIC_API_KEY=...
PERPLEXITY_API_KEY=...
JWT_SECRET=...

DB_HOST=localhost
DB_NAME=footyhub
DB_USER=footyhub
DB_PASSWORD=...

SQS_QUEUE_URL=https://sqs.eu-west-2.amazonaws.com/YOUR_ACCOUNT_ID/footyhub-articles
AWS_REGION=eu-west-2
```

### 9. Create SQS queue

In AWS Console → SQS → Create queue:
- Type: **Standard**
- Name: `footyhub-articles`
- Update `SQS_QUEUE_URL` in `.env` with the real URL

### 10. Create IAM role for EC2

The EC2 instance needs permission to read/write SQS. In AWS Console:
1. IAM → Roles → Create role → EC2
2. Attach the policy from `deploy/iam-policy.json` (replace `YOUR_ACCOUNT_ID`)
3. Attach the role to the EC2 instance: **EC2 → Actions → Security → Modify IAM role**

### 11. Run the app

```bash
source venv/bin/activate

# Web server (test run)
uvicorn api.app:app --host 0.0.0.0 --port 8000

# Publisher (fetch articles → SQS)
python -m runners.run_publisher

# Subscriber (SQS → enrich → save to DB)
python -m runners.run_subscriber
```

### 12. Run as background services (systemd)

```bash
sudo cp deploy/footyhub-web.service /etc/systemd/system/
sudo cp deploy/footyhub-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable footyhub-web footyhub-scheduler
sudo systemctl start footyhub-web footyhub-scheduler
```

Check status:
```bash
sudo systemctl status footyhub-web
sudo systemctl status footyhub-scheduler
```

### 13. Configure nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/footyhub
sudo ln -s /etc/nginx/sites-available/footyhub /etc/nginx/sites-enabled/footyhub
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

---

## Updating the app after code changes

On your local machine:
```powershell
git add .
git commit -m "describe what changed"
git push
```

On the server:
```bash
cd ~/FootyhubAWS
git pull
source venv/bin/activate
sudo systemctl restart footyhub-web footyhub-scheduler
```

---

## Useful server commands

| Command | Purpose |
|---------|---------|
| `sudo journalctl -u footyhub-web -f` | Stream web app logs |
| `sudo journalctl -u footyhub-scheduler -f` | Stream scheduler logs |
| `sudo systemctl restart footyhub-web` | Restart after code change |
| `sudo nginx -t` | Test nginx config |
| `sudo -u postgres psql -d footyhub` | Connect to database |

---

## Git Workflow

```powershell
git add .
git commit -m "describe what changed"
git push
```
