import sqlalchemy as sa
from api.web.queries import engine

def search_articles(query: str, club=None, competition=None, theme=None) -> list[dict]:
    params = {"query": f"%{query}%"}

    sql = ("SELECT id, competition, club, theme, body_text "
           "FROM articles "
           "WHERE body_text LIKE :query")

    if club:        sql += " AND club = :club";        params["club"] = club
    if competition: sql += " AND competition = :comp"; params["comp"] = competition
    if theme:       sql += " AND theme = :theme";      params["theme"] = theme

    sql += " ORDER BY published_at DESC LIMIT 5"

    with engine.connect() as conn:
        rows = conn.execute(sa.text(sql), params).fetchall()
    return [{"id": r.id, "competition": r.competition, "club": r.club,
             "theme": r.theme, "snippet": r.body_text[:300]} for r in rows]

def get_article(article_id: int) -> dict:
    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT id, competition, club, theme, body_text "
            "FROM articles WHERE id = :id"
        ), {"id": article_id}).fetchone()
    return {"id": row.id, "competition": row.competition, "club": row.club,
            "theme": row.theme, "body_text": row.body_text} if row else {}
