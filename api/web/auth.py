import os
import sys
import sqlalchemy as sa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
        {"sub": str(user_id), "username": username, "exp": datetime.utcnow() + timedelta(hours=24)},
        SECRET_KEY,
        algorithm=ALGORITHM,
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
            sa.text(
                "INSERT INTO dbo.users (username, password_hash) OUTPUT INSERTED.id "
                "VALUES (:username, :password_hash)"
            ),
            {"username": username, "password_hash": password_hash},
        ).fetchone()
        conn.commit()
        return row[0]
