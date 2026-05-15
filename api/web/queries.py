import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import sqlalchemy as sa
import runners.appsettings as settings
from utils.db.db_access import build_engine

engine = build_engine(server=settings.DB_SERVER, database=settings.DB_NAME, driver=settings.DB_DRIVER)

#-- Articles

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

    if competition:
        query += " AND a.competition = :competition"
        params["competition"] = competition

    if club:
        query += " AND a.club = :club"
        params["club"] = club

    if theme:
        query += " AND a.theme = :theme"
        params["theme"] = theme

    query += " ORDER BY a.published_at DESC"

    with engine.connect() as conn:
        return conn.execute(sa.text(query), params).fetchall()

# --- likes ---

def toggle_like(user_id: int, article_id: int) -> None:
    with engine.connect() as conn:
        existing = conn.execute(
            sa.text("SELECT 1 FROM dbo.article_likes WHERE user_id = :uid AND article_id = :aid"),
            {"uid": user_id, "aid": article_id},
        ).fetchone()
        if existing:
            conn.execute(
                sa.text("DELETE FROM dbo.article_likes WHERE user_id = :uid AND article_id = :aid"),
                {"uid": user_id, "aid": article_id},
            )
        else:
            conn.execute(
                sa.text("INSERT INTO dbo.article_likes (user_id, article_id) VALUES (:uid, :aid)"),
                {"uid": user_id, "aid": article_id},
            )
        conn.commit()


def get_like_state(user_id: int, article_id: int) -> bool:
    with engine.connect() as conn:
        return conn.execute(
            sa.text("SELECT 1 FROM dbo.article_likes "
                    "WHERE user_id = :uid AND article_id = :aid"),
            {"uid": user_id, "aid": article_id},
        ).fetchone() is not None

# --- Chat message ---

def save_message(user_id: int, role: str, content: str) -> None:
    with engine.connect() as conn:
        conn.execute(sa.text(
            "INSERT INTO dbo.chat_messages (user_id, role, content) "
            "VALUES (:uid, :role, :content)"
        ), {"uid": user_id, "role": role, "content": content})
        conn.commit()


def get_chat_history(user_id: int) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(sa.text(
            "SELECT role, content "
            "FROM dbo.chat_messages "
            "WHERE user_id = :uid "
            "ORDER BY created_at"
        ), {"uid": user_id}).fetchall()
    return [{"role": r.role, "content": r.content} for r in rows]

def get_recent_articles_for_chat(n: int = 20) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(sa.text(
            "SELECT TOP(:n) id, competition, club, theme, body_text "
            "FROM dbo.articles "
            "ORDER BY published_at DESC"
        ), {"n": n}).fetchall()
        return [{"id": r.id, "competition": r.competition, "club": r.club,
                 "theme": r.theme, "body_text": r.body_text} for r in rows]
    

