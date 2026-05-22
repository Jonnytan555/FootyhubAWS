import logging
import uuid

import pandas as pd
import sqlalchemy as sa


class DbInsertHandler:

    def __init__(
        self,
        engine: sa.Engine,
        table_name: str,
        schema: str,
        key_cols: list[str],
    ) -> None:
        self.engine = engine
        self.table_name = table_name
        self.schema = schema
        self.key_cols = key_cols

    def handle(self, df: pd.DataFrame, dropNa: bool = False, dtypes=None, created_date: str = 'CreatedDate') -> list[dict]:
        if df is None or df.empty:
            return []

        temp = f"{self.table_name}_tmp_{uuid.uuid4().hex[:12]}"
        columns = df.columns.tolist()
        col_list = ", ".join(f'"{c}"' for c in columns)
        src_cols = ", ".join(f'source."{c}"' for c in columns)
        join_clause = " AND ".join(f'target."{c}" = source."{c}"' for c in self.key_cols)

        insert_sql = f"""
            INSERT INTO "{self.schema}"."{self.table_name}" ({col_list})
            SELECT {src_cols}
            FROM "{self.schema}"."{temp}" AS source
            WHERE NOT EXISTS (
                SELECT 1 FROM "{self.schema}"."{self.table_name}" AS target
                WHERE {join_clause}
            )
            RETURNING *
        """

        try:
            df.to_sql(
                temp,
                con=self.engine,
                schema=self.schema,
                if_exists="replace",
                index=False,
            )

            with self.engine.begin() as conn:
                result = conn.execute(sa.text(insert_sql))
                rows = result.fetchall()
                keys = list(result.keys())

            inserted = [dict(zip(keys, row)) for row in rows]

            logging.info("[DbInsertHandler] Inserted %d new rows into %s.%s",
                         len(inserted), self.schema, self.table_name)
            return inserted

        except Exception:
            logging.exception("[DbInsertHandler] Failed to insert into %s.%s",
                              self.schema, self.table_name)
            raise

        finally:
            self._drop_temp(temp)

    def _drop_temp(self, temp: str) -> None:
        try:
            with self.engine.begin() as conn:
                conn.execute(sa.text(f'DROP TABLE IF EXISTS "{self.schema}"."{temp}"'))
        except Exception:
            logging.warning("[DbInsertHandler] Failed to drop temp table %s", temp)
