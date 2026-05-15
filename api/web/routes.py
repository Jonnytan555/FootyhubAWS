from pathlib import Path
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from api.web.chat_service import chat
from api.web.models import ChatRequest
from runners.ai.taxonomy import FOOTBALL_TREE
from api.web.queries import get_articles, toggle_like, get_like_state, save_message, get_chat_history
from api.web.auth import (
    get_current_user, get_user_by_username, create_user,
    hash_password, verify_password, create_token,
)


router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

competitions = list(FOOTBALL_TREE.keys())
clubs        = sorted({c for comp in FOOTBALL_TREE.values() for c in comp.get("clubs", [])})
themes       = sorted({t for comp in FOOTBALL_TREE.values() for t in comp.get("themes", [])})


# --- Feed ---

@router.get("/")
def index(request: Request, current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"]) if current_user else None
    articles = get_articles(user_id=user_id)
    chat_history = get_chat_history(user_id) if user_id else []
    return templates.TemplateResponse("feed.html", {
        "request":      request,
        "articles":     articles,
        "competitions": competitions,
        "clubs":        clubs,
        "themes":       themes,
        "current_user": current_user,
        "chat_history": chat_history,
        "error":        request.query_params.get("error"),
        "tab":          request.query_params.get("tab", "login"),
    })


@router.get("/articles")
def articles(
    request: Request,
    current_user=Depends(get_current_user),
    competition: str | None = None,
    club: str | None = None,
    theme: str | None = None,
    liked_only: str | None = None,
):
    user_id = int(current_user["sub"]) if current_user else None
    rows = get_articles(competition or None, club or None, theme or None, user_id=user_id, liked_only=bool(liked_only))
    return templates.TemplateResponse("partials/article_list.html", {
        "request":      request,
        "articles":     rows,
        "current_user": current_user,
    })


# --- Auth ---

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_username(form.username)
    if not user or not verify_password(form.password, user.password_hash):
        return RedirectResponse("/?error=Invalid+username+or+password&tab=login", status_code=303)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", create_token(user.id, user.username), httponly=True, samesite="lax")
    return response


@router.post("/register")
def register(form: OAuth2PasswordRequestForm = Depends()):
    if get_user_by_username(form.username):
        return RedirectResponse("/?error=Username+already+taken&tab=register", status_code=303)
    user_id = create_user(form.username, hash_password(form.password))
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", create_token(user_id, form.username), httponly=True, samesite="lax")
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

def _select_options(values: list, selected: str) -> str:
    opts = '<option value="">All</option>'
    for v in values:
        sel = " selected" if v == selected else ""
        opts += f'<option value="{v}"{sel}>{v}</option>'
    return opts


# --- Chat ---
@router.post("/chat")
def chat_endpoint(body: ChatRequest):
    reply, _ = chat([{"role": "user", "content": body.message}])
    return {"reply": reply}


@router.post("/chat/send")
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
        club        = filter_action.get("club") or ""
        competition = filter_action.get("competition") or ""
        theme       = filter_action.get("theme") or ""

        filtered = get_articles(
            competition=competition or None,
            club=club or None,
            theme=theme or None,
            user_id=user_id,
        )
        article_html = templates.env.get_template("partials/article_list.html").render(
            articles=filtered, current_user=current_user,
        )

        html += (
            f'<div id="article-list" hx-swap-oob="true">{article_html}</div>'
            f'<select id="filter-competition" name="competition" hx-get="/articles" hx-target="#article-list" hx-trigger="change" hx-include="#filters" hx-swap-oob="true">{_select_options(competitions, competition)}</select>'
            f'<select id="filter-club" name="club" hx-get="/articles" hx-target="#article-list" hx-trigger="change" hx-include="#filters" hx-swap-oob="true">{_select_options(clubs, club)}</select>'
            f'<select id="filter-theme" name="theme" hx-get="/articles" hx-target="#article-list" hx-trigger="change" hx-include="#filters" hx-swap-oob="true">{_select_options(themes, theme)}</select>'
        )

    return HTMLResponse(html)
