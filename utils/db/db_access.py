import os
import sqlalchemy as sa


def build_engine(
    server: str | None = None,
    database: str | None = None,
    driver: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> sa.engine.Engine:
    """
    Build a SQLAlchemy engine for SQL Server.
    Falls back to env vars then sensible defaults.
    Uses Windows Authentication when no user/password provided.
    """
    server   = server   or os.getenv("DB_SERVER", "")
    database = database or os.getenv("DB_NAME",   "")
    driver   = driver   or os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    user     = user     or os.getenv("DB_USER",   "")
    password = password or os.getenv("DB_PASS",   "")

    drv = driver.replace(" ", "+")

    if user:
        return sa.create_engine(
            f"mssql+pyodbc://{user}:{password}@{server}/{database}?driver={drv}"
        )
    return sa.create_engine(
        f"mssql+pyodbc://{server}/{database}?driver={drv}&trusted_connection=yes"
    )


engine = build_engine()
