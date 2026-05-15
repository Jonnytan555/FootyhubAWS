import sqlalchemy as sa

from listeners.queue.queue_reader import QueueConsumer


class DbQueueReader(QueueConsumer):
    def __init__(self, engine, source_type: str | None = None) -> None:
        self.engine = engine
        self.source_type = source_type

    def read(self) -> list[dict]:
        query = """
            SELECT
                id,
                source_type,
                source_name,
                source_record_id,
                source_url,
                title,
                body_text,
                published_at,
                topic
            FROM article_queue
            WHERE status IN ('pending', 'failed')
            AND NOT EXISTS (
                SELECT 1 FROM dbo.articles a
                WHERE a.source_record_id = article_queue.source_record_id
            )
        """

        params = {}

        if self.source_type:
            query += " AND source_type = :source_type"
            params["source_type"] = self.source_type

        with self.engine.connect() as conn:
            rows = conn.execute(sa.text(query), params).fetchall()

        return [
            {
                "article_candidate_id": r.id,
                "source_type":          r.source_type,
                "source_name":          r.source_name,
                "source_record_id":     r.source_record_id,
                "source_url":           r.source_url,
                "title":                r.title,
                "body_text":            r.body_text,
                "published_at":         r.published_at,
                "topic":                r.topic,
            }
            for r in rows
        ]

    def mark_processed(self, items: list[dict]) -> None:
        self._update_status([r["article_candidate_id"] for r in items if r.get("article_candidate_id")], "processed")

    def mark_failed(self, items: list[dict]) -> None:
        self._update_status([r["article_candidate_id"] for r in items if r.get("article_candidate_id")], "failed")

    def _update_status(self, ids: list[int], status: str) -> None:
        if not ids:
            return
        
        placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
        
        params = {f"id_{i}": v for i, v in enumerate(ids)}
        
        params["status"] = status
        
        with self.engine.begin() as conn:
            conn.execute(
                sa.text(f"UPDATE dbo.article_queue SET status = :status WHERE id IN ({placeholders})"),
                params,
            )
