import pandas as pd

from utils.scraper.persistence.db_insert_handler import DbInsertHandler

_KEY_COLS = ["source_type", "source_name", "source_record_id"]

_DB_COLS = [
    "source_type", "source_name", "source_record_id", "source_url",
    "title", "body_text", "published_at",
    "topic", "competition", "theme", "club", "player_name",
    "clubs_mentioned", "players_mentioned",
]


class ArticleWriter(DbInsertHandler):
    def __init__(self, engine) -> None:
        super().__init__(
            engine=engine,
            table_name="articles",
            schema="dbo",
            key_cols=_KEY_COLS,
        )

    def write(self, rows: list[dict]) -> None:
        if not rows:
            return
        df = pd.DataFrame(rows)[_DB_COLS]
        self.handle(df)
