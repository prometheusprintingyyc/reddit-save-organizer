import sqlite3
from fastapi import APIRouter, Depends
from database import get_db
from reddit.auth import get_reddit_instance, is_authenticated

router = APIRouter()


@router.get("/api/auth/status")
def auth_status(conn: sqlite3.Connection = Depends(get_db)):
    if not is_authenticated(conn):
        return {"authenticated": False, "username": None}
    reddit = get_reddit_instance(conn)
    try:
        username = reddit.user.me().name
    except Exception:
        return {"authenticated": False, "username": None}
    return {"authenticated": True, "username": username}
