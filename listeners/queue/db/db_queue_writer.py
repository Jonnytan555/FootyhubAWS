import pandas as pd

from utils.scraper.persistence.db_insert_handler import DbInsertHandler
from listeners.queue.queue_writer import QueueWriter

_KEY_COLS = ["source_type", "source_name", "source_record_id"]

_DB_COLS = [
    "source_type", "source_name", "source_record_id", "source_url",
    "title", "body_text", "published_at",
    "topic", "status",
]


class DbQueueWriter(QueueWriter):
    def __init__(self, handler: DbInsertHandler) -> None:
        self._handler = handler

    def write(self, rows: list[dict]) -> None:
        if not rows:
            return

        rows = [{**row, "status": "pending"} for row in rows]
        rows = [row for row in rows if all(row.get(k) for k in _KEY_COLS)]

        self._handler.handle(pd.DataFrame(rows)[_DB_COLS])
