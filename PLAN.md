# FootyHub — Build Plan

## Stack
- **FastAPI** — Python web framework
- **Jinja2** — server-side HTML templates
- **HTMX** — dynamic UI without writing JavaScript
- **SQL Server** — database (via SQLAlchemy)
- **passlib + bcrypt** — password hashing
- **python-jose** — JWT tokens

---

## What's Built

### 1. Feed (complete)
News articles from `dbo.articles`, filterable by competition, club, theme. HTMX swaps the article list without a page reload.

### 2. Auth (complete)
JWT stored in an HttpOnly cookie. Modal overlay on the feed until logged in.

### 3. Likes (complete)
Per-article like toggle (♡ → ♥). HTMX replaces the button in place. "Liked" tab filters to liked articles only.

---

## File Structure

```
api/
  app.py                          — entry point, loads .env, mounts router
  web/
    routes.py                     — all route handlers (feed, auth, likes)
    queries.py                    — all DB queries (articles, likes)
    auth.py                       — JWT utils + user DB functions
  templates/
    base.html                     — shared layout, all CSS, nav, auth overlay
    feed.html                     — filter bar + feed tabs + article list
    partials/
      article_list.html           — article cards (rendered by HTMX on filter)
      auth_modal.html             — login / register tabbed form
```

---

## SQL Tables

```sql
-- Run these in SSMS before starting the app

CREATE TABLE dbo.users (
    id            INT IDENTITY PRIMARY KEY,
    username      NVARCHAR(100) UNIQUE NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    created_at    DATETIME DEFAULT GETDATE()
);

CREATE TABLE dbo.article_likes (
    user_id    INT NOT NULL,
    article_id INT NOT NULL,
    PRIMARY KEY (user_id, article_id)
);
```

---

## .env

```
PERPLEXITY_API_KEY=...
ANTHROPIC_API_KEY=...
JWT_SECRET=footyhub-jwt-secret-change-in-production
```

Generate a proper secret with:
```python
import secrets; print(secrets.token_hex(32))
```

---

## Dependencies

```
pip install python-jose[cryptography] passlib[bcrypt] "bcrypt==3.2.2"
```

> Note: bcrypt must be pinned to 3.2.2 — passlib is incompatible with bcrypt 4+

---

## Code

### `api/app.py`

```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from api.web.routes import router

app = FastAPI()
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="127.0.0.1", port=8000, reload=False)
```

---

### `api/web/auth.py`
JWT utilities and user DB functions. No routes — routes live in `routes.py`.

```python
import os, sys, sqlalchemy as sa
sys.path.insert(0, ...)

from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from starlette.requests import Request
from api.web.queries import engine

SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM  = "HS256"
_pwd       = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)

def create_token(user_id: int, username: str) -> str:
    return jwt.encode(
        {"sub": str(user_id), "username": username,
         "exp": datetime.utcnow() + timedelta(hours=24)},
        SECRET_KEY, algorithm=ALGORITHM,
    )

def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def get_user_by_username(username: str):
    with engine.connect() as conn:
        return conn.execute(
            sa.text("SELECT id, username, password_hash FROM dbo.users WHERE username = :username"),
            {"username": username},
        ).fetchone()

def create_user(username: str, password_hash: str) -> int:
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("INSERT INTO dbo.users (username, password_hash) OUTPUT INSERTED.id "
                    "VALUES (:username, :password_hash)"),
            {"username": username, "password_hash": password_hash},
        ).fetchone()
        conn.commit()
        return row[0]
```

**Concept:** JWT encodes `user_id + username + expiry` into a signed string. The server verifies the signature using `JWT_SECRET` — no DB lookup needed on every request. `HttpOnly` cookies mean JavaScript can never read the token (XSS protection).

---

### `api/web/queries.py`
Articles and likes queries only. User queries live in `auth.py`.

```python
def get_articles(competition=None, club=None, theme=None, user_id=None, liked_only=False):
    params = {"user_id": user_id or 0}
    join = "INNER JOIN" if liked_only else "LEFT JOIN"
    query = f"""
        SELECT a.id, a.source_url, a.competition, a.club, a.theme,
               a.published_at, a.clubs_mentioned, a.players_mentioned, a.body_text,
               CASE WHEN al.user_id IS NOT NULL THEN 1 ELSE 0 END AS liked
        FROM dbo.articles a
        {join} dbo.article_likes al ON al.article_id = a.id AND al.user_id = :user_id
        WHERE 1=1
    """
    # filters appended here ...
    query += " ORDER BY a.published_at DESC"
    with engine.connect() as conn:
        return conn.execute(sa.text(query), params).fetchall()

def toggle_like(user_id: int, article_id: int) -> None:
    # INSERT if not exists, DELETE if exists

def get_like_state(user_id: int, article_id: int) -> bool:
    # returns True if user has liked the article
```

**Concept:** `INNER JOIN` instead of `LEFT JOIN` when `liked_only=True` — INNER JOIN only returns rows where both sides match, so only liked articles come back.

---

### `api/web/routes.py`

```python
# --- Feed ---

@router.get("/")
def index(request: Request, current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"]) if current_user else None
    articles = get_articles(user_id=user_id)
    return templates.TemplateResponse("feed.html", {
        "request": request, "articles": articles,
        "competitions": competitions, "clubs": clubs, "themes": themes,
        "current_user": current_user,
        "error": request.query_params.get("error"),
        "tab":   request.query_params.get("tab", "login"),
    })

@router.get("/articles")
def articles(request, current_user=Depends(get_current_user),
             competition=None, club=None, theme=None, liked_only=None):
    user_id = int(current_user["sub"]) if current_user else None
    rows = get_articles(..., user_id=user_id, liked_only=bool(liked_only))
    return templates.TemplateResponse("partials/article_list.html", {...})

# --- Auth ---

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_username(form.username)
    if not user or not verify_password(form.password, user.password_hash):
        return RedirectResponse("/?error=Invalid+username+or+password&tab=login", status_code=303)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", create_token(user.id, user.username),
                        httponly=True, samesite="lax")
    return response

@router.post("/register")
def register(form: OAuth2PasswordRequestForm = Depends()):
    if get_user_by_username(form.username):
        return RedirectResponse("/?error=Username+already+taken&tab=register", status_code=303)
    user_id = create_user(form.username, hash_password(form.password))
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", create_token(user_id, form.username),
                        httponly=True, samesite="lax")
    return response

@router.post("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("access_token")
    return response

# --- Likes ---

@router.post("/like/{article_id}")
def like(article_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        return HTMLResponse(status_code=401)
    uid = int(current_user["sub"])
    toggle_like(uid, article_id)
    liked = get_like_state(uid, article_id)
    heart = "♥" if liked else "♡"
    return HTMLResponse(
        f'<button id="like-{article_id}" hx-post="/like/{article_id}" '
        f'hx-target="#like-{article_id}" hx-swap="outerHTML" class="like-btn">{heart}</button>'
    )
```

**Concept:** `Depends(get_current_user)` runs before every route that uses it — FastAPI injects the decoded user dict automatically. `hx-swap="outerHTML"` replaces the button element itself with whatever the server returns.

---

### `api/templates/feed.html`

```html
{% extends "base.html" %}
{% block content %}

<!-- Tabs -->
<div class="feed-tabs">
    <button class="feed-tab active"
            hx-get="/articles" hx-target="#article-list" hx-include="#filters"
            onclick="setFeedTab(this)">All</button>
    {% if current_user %}
    <button class="feed-tab"
            hx-get="/articles" hx-target="#article-list" hx-include="#filters"
            hx-vals='{"liked_only": "1"}'
            onclick="setFeedTab(this)">♥ Liked</button>
    {% endif %}
</div>

<!-- Filters -->
<form id="filters" ...>
    <select name="competition" hx-get="/articles" hx-target="#article-list"
            hx-trigger="change" hx-include="#filters">...</select>
    <!-- club, theme selects -->
</form>

<div id="article-list">
    {% include "partials/article_list.html" %}
</div>
{% endblock %}
```

**Concept:** `hx-vals` injects extra query params into the HTMX request. `hx-include="#filters"` also sends all the filter dropdowns — so tabs and filters work together.

---

### `api/templates/partials/auth_modal.html`

```html
<div class="auth-modal">
    <h2>Welcome to FootyHub</h2>
    <div class="auth-tabs">
        <button class="tab-btn active" onclick="showTab('login', this)">Login</button>
        <button class="tab-btn" onclick="showTab('register', this)">Register</button>
    </div>
    {% if error %}<p class="auth-error">{{ error }}</p>{% endif %}
    <div id="tab-login" class="tab-content">
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
    <div id="tab-register" class="tab-content hidden">
        <form method="POST" action="/register">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Create account</button>
        </form>
    </div>
</div>
```

**Concept:** Standard HTML form POST — no JavaScript needed for submission. The server sets the cookie and redirects back to `/`. If login fails, the server redirects to `/?error=...` and the modal displays the error from `request.query_params`.

---

## Data Flow

### Login
```
User fills form → POST /login (form data)
  → get_user_by_username() — DB lookup
  → verify_password() — bcrypt check
  → create_token() — JWT signed with JWT_SECRET
  → Set-Cookie: access_token=<jwt>; HttpOnly
  → 303 redirect to GET /
    → get_current_user() reads cookie, decodes JWT
    → feed renders with username in nav, modal hidden
```

### Like toggle
```
User clicks ♡ → HTMX POST /like/{id}
  → get_current_user() from cookie
  → toggle_like() — INSERT or DELETE in article_likes
  → get_like_state() — check current state
  → return <button>♥</button> HTML
  → HTMX swaps the button in place (outerHTML)
```

### Liked tab
```
User clicks ♥ Liked → HTMX GET /articles?liked_only=1
  → get_articles(liked_only=True) — INNER JOIN article_likes
  → only returns articles the user has liked
  → HTMX swaps #article-list
```

---

## Known Issues / Notes

- `bcrypt` must be `3.2.2` — passlib is incompatible with bcrypt 4+
- Run with `reload=False` on Windows — multiple reload processes can cause port conflicts
- `JWT_SECRET` must be in `.env` before starting the app
- Register route still fails (500) — to be investigated

---

## Next Steps

- [ ] Fix register 500 error
- [ ] Add pagination to the feed
- [ ] Show like count per article
- [ ] User profile page (all liked articles)

---

# Stage 6 — Chatbot Enhancements

## Overview

Five additions that each teach a different concept about what AI tools can do beyond answering questions.

| Sub-stage | Feature | What you ask | Concept |
|-----------|---------|-------------|---------|
| 6a | Update feed filters | "Show me only Arsenal news" | Tool returns a UI action — AI controls the page |
| 6b | Like an article via chat | "Like that Ben White article" | Tools can write to the DB — AI has side effects |
| 6c | Summarise liked articles | "What have I been reading about?" | Tool reads personalised user data |
| 6d | Favourite club preference | "Set my favourite club to Liverpool" | Tool persists a user preference — shapes future AI behaviour |
| 6e | Scroll to an article | "Show me the PSG final story in the feed" | Tool triggers a JavaScript action in the browser |

---

## Stage 6a — Update Feed Filters

**What you'll see:** Type "Show me only Arsenal news" → the competition/club dropdowns update and the article list refreshes to Arsenal articles, without leaving the chat.

### How it works

HTMX has a feature called **out-of-band swaps** (`hx-swap-oob`). Normally a `/chat-partial` response swaps HTML into `#chat-messages`. With OOB, the same response can *also* update other elements on the page at the same time — in this case, the filter dropdowns and article list.

Claude calls a new tool `set_filter` with the values it understood from the user. The route detects this tool result and appends OOB swap HTML to the response.

### New tool — `api/ai/tools.py`

```python
{
    "name": "set_filter",
    "description": "Update the feed filters to show articles for a specific club, competition, or theme. Call this when the user asks to see or filter news for a specific team or topic.",
    "input_schema": {
        "type": "object",
        "properties": {
            "club":        {"type": "string"},
            "competition": {"type": "string"},
            "theme":       {"type": "string"},
        },
    },
},
```

### Updated `chat_service.py`

`chat()` needs to return both the reply text AND any filter action Claude requested. Change the return type to a tuple:

```python
def chat(messages: list[dict]) -> tuple[str, dict | None]:
    filter_action = None

    while True:
        response = client.messages.create(...)

        if response.stop_reason == "end_turn":
            text = next(b.text for b in response.content if hasattr(b, "text"))
            return text, filter_action

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for block in response.content:
            if block.type == "tool_use":
                if block.name == "set_filter":
                    filter_action = block.input   # {"club": "Arsenal", ...}
                    result = {"status": "filters updated"}
                else:
                    result = TOOL_MAP[block.name](**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
        messages.append({"role": "user", "content": tool_results})
```

### Updated `/chat-partial` route

```python
@router.post("/chat-partial")
def chat_partial(message: str = Form(...), current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"])
    history = get_chat_history(user_id)
    history.append({"role": "user", "content": message})
    reply, filter_action = chat(history)
    save_message(user_id, "user", message)
    save_message(user_id, "assistant", reply)

    html = (
        f'<div class="chat-msg chat-msg--user">{message}</div>'
        f'<div class="chat-msg chat-msg--assistant">{reply}</div>'
    )

    if filter_action:
        club        = filter_action.get("club", "")
        competition = filter_action.get("competition", "")
        theme       = filter_action.get("theme", "")
        # OOB swap updates the filter selects
        html += f'''
        <select name="competition" id="filter-competition"
                hx-get="/articles" hx-target="#article-list"
                hx-trigger="load" hx-include="#filters"
                hx-swap-oob="true">
            <option value="">All competitions</option>
            {_options(competitions, competition)}
        </select>
        <select name="club" id="filter-club"
                hx-swap-oob="true">
            <option value="">All clubs</option>
            {_options(clubs, club)}
        </select>
        '''

    return HTMLResponse(html)
```

**Concept:** `hx-swap-oob="true"` on an element in the response tells HTMX: "find the element on the page with this same `id` and replace it with this one." A single server response can update multiple independent parts of the page simultaneously.

### Data flow
```
User: "Show me only Arsenal news"
  → POST /chat-partial
    → Claude calls set_filter(club="Arsenal")
    → filter_action = {"club": "Arsenal"}
    → reply = "Filtering to Arsenal news now"
    → response HTML has:
        [chat reply divs]
        [<select id="filter-club" hx-swap-oob="true" hx-trigger="load"> with Arsenal selected]
  → HTMX appends reply to #chat-messages
  → HTMX finds filter-club on page, replaces it with new select
  → new select fires hx-trigger="load" → GET /articles?club=Arsenal
  → #article-list swaps to Arsenal articles
```

---

## Stage 6b — Like an Article via Chat

**What you'll see:** Ask "Like the Ben White article" → Claude searches for it, calls `like_article`, and confirms it's liked. The heart in the feed updates next time you load the page.

### New tool — `api/ai/tools.py`

```python
{
    "name": "like_article",
    "description": "Like or unlike an article on behalf of the user. Use search_articles first to find the article ID.",
    "input_schema": {
        "type": "object",
        "properties": {
            "article_id": {"type": "integer"},
            "action":     {"type": "string", "enum": ["like", "unlike"]},
        },
        "required": ["article_id", "action"],
    },
},
```

### New tool implementation — `api/ai/article_tools.py`

```python
def like_article(article_id: int, action: str, user_id: int) -> dict:
    from api.web.queries import toggle_like, get_like_state
    liked = get_like_state(user_id, article_id)
    if (action == "like" and not liked) or (action == "unlike" and liked):
        toggle_like(user_id, article_id)
    state = get_like_state(user_id, article_id)
    return {"article_id": article_id, "liked": state}
```

`like_article` needs the `user_id` (who is liking), but Claude doesn't know it — it's in the JWT, not the conversation. Pass it into the tool at call time in `chat_service.py`:

```python
# chat() takes user_id so it can inject it into like_article calls
def chat(messages: list[dict], user_id: int) -> tuple[str, dict | None]:
    ...
    for block in response.content:
        if block.type == "tool_use":
            if block.name == "like_article":
                result = like_article(**block.input, user_id=user_id)
            else:
                result = TOOL_MAP[block.name](**block.input)
```

**Concept:** Tools can write to the database, not just read. Claude acts as an agent on the user's behalf. The user ID comes from the JWT (trusted, server-side) — Claude never knows or controls it, which keeps it safe.

---

## Stage 6c — Summarise Liked Articles

**What you'll see:** Ask "What have I been reading about?" → Claude fetches your liked articles and gives a personalised summary of your interests.

### New tool — `api/ai/tools.py`

```python
{
    "name": "get_liked_articles",
    "description": "Fetch the articles the current user has liked. Use this to summarise what the user has been reading or to make personalised recommendations.",
    "input_schema": {
        "type": "object",
        "properties": {},
    },
},
```

### New tool implementation — `api/ai/article_tools.py`

```python
def get_liked_articles(user_id: int) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT a.id, a.competition, a.club, a.theme, a.body_text
            FROM dbo.articles a
            INNER JOIN dbo.article_likes al ON al.article_id = a.id
            WHERE al.user_id = :user_id
            ORDER BY a.published_at DESC
        """), {"user_id": user_id}).fetchall()
    return [{"id": r.id, "competition": r.competition, "club": r.club,
             "theme": r.theme, "snippet": r.body_text[:200]} for r in rows]
```

Same pattern as `like_article` — inject `user_id` into the tool call from `chat_service.py`.

**Concept:** The AI can personalise its answers using data it retrieves about *you specifically*, not just the general article database. The user never tells Claude what they like — Claude looks it up.

---

## Stage 6d — Favourite Club Preference

**What you'll see:** Tell the chat "Set my favourite club to Liverpool" → confirmed. From then on, asking "any news?" automatically searches Liverpool without being asked.

### SQL

```sql
ALTER TABLE dbo.users ADD favourite_club NVARCHAR(100) NULL;
```

### New tools — `api/ai/tools.py`

```python
{
    "name": "set_favourite_club",
    "description": "Save the user's favourite football club. They will then get club-specific results by default.",
    "input_schema": {
        "type": "object",
        "properties": {
            "club": {"type": "string"},
        },
        "required": ["club"],
    },
},
{
    "name": "get_user_preferences",
    "description": "Get the user's saved preferences, including their favourite club.",
    "input_schema": {"type": "object", "properties": {}},
},
```

### Updated system prompt — `api/ai/system_prompt.txt`

Inject the user's favourite club at request time:

```python
# in chat_service.py
def build_system_prompt(favourite_club: str | None) -> str:
    base = SYSTEM_PROMPT
    if favourite_club:
        base += f"\n\nThe user's favourite club is {favourite_club}. When they ask general questions, default to searching for {favourite_club} news first."
    return base
```

**Concept:** Persistent user preferences change the AI's *default behaviour* without the user needing to repeat themselves. The preference is injected into the system prompt at call time — Claude reads it as part of its instructions.

---

## Stage 6e — Scroll to an Article in the Feed

**What you'll see:** Ask "Show me the PSG final story in the feed" → Claude finds the article, and the page smoothly scrolls to that card in the article list and briefly highlights it.

### New tool — `api/ai/tools.py`

```python
{
    "name": "highlight_article",
    "description": "Scroll to and highlight a specific article in the feed. Use search_articles first to find the article ID, then call this to bring it into view.",
    "input_schema": {
        "type": "object",
        "properties": {
            "article_id": {"type": "integer"},
        },
        "required": ["article_id"],
    },
},
```

This tool doesn't query the DB — it just returns a marker:

```python
def highlight_article(article_id: int) -> dict:
    return {"scroll_to_article": article_id}
```

### Updated `/chat-partial` route

Detect the scroll marker and append an inline `<script>` to the response:

```python
if scroll_to := tool_results.get("scroll_to_article"):
    html += f'''
    <script>
        const el = document.getElementById("article-{scroll_to}");
        if (el) {{
            el.scrollIntoView({{behavior: "smooth", block: "center"}});
            el.classList.add("highlight");
            setTimeout(() => el.classList.remove("highlight"), 2000);
        }}
    </script>
    '''
```

Add the highlight CSS to `base.html`:

```css
.card.highlight {
    outline: 2px solid #3949ab;
    transition: outline 0.3s;
}
```

Each article card needs `id="article-{{ a.id }}"` in `article_list.html`.

**Concept:** The server can return `<script>` tags inside HTMX responses — HTMX executes them after the swap. This lets the AI trigger browser behaviour (scrolling, highlighting, animations) without a dedicated JavaScript API — the server just sends the script.

---

## Files Changed in Stage 6

| File | Change |
|------|--------|
| `api/ai/tools.py` | Add `set_filter`, `like_article`, `get_liked_articles`, `set_favourite_club`, `get_user_preferences`, `highlight_article` tools |
| `api/ai/article_tools.py` | Implement `like_article`, `get_liked_articles`, `highlight_article` |
| `api/web/chat_service.py` | Return `(reply, filter_action)` tuple; pass `user_id` into tools; inject favourite club into system prompt |
| `api/web/routes.py` | Unpack tuple from `chat()`; build OOB swap HTML for filters; build scroll script for highlight |
| `api/web/queries.py` | Add `get_favourite_club`, `set_favourite_club` |
| `api/templates/partials/article_list.html` | Add `id="article-{{ a.id }}"` to each card |
| `api/templates/base.html` | Add `.card.highlight` CSS |
| `api/ai/system_prompt.txt` | Update to mention new tools |

## SQL to run before starting

```sql
ALTER TABLE dbo.users ADD favourite_club NVARCHAR(100) NULL;
```

## Verification

1. **6a** — "Show me only Champions League news" → dropdowns update, feed reloads filtered
2. **6b** — "Like the Ben White injury article" → ♡ → ♥ in feed next reload
3. **6c** — Like 3 articles, then ask "What have I been reading about?" → personalised summary
4. **6d** — "Set my favourite club to Arsenal" → ask "any news?" → Arsenal results by default
5. **6e** — "Show me the Liverpool vs Chelsea preview in the feed" → page scrolls and highlights the card
