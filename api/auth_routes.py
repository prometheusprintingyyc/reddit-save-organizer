import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from database import get_db
from reddit.auth import get_auth_url, get_reddit_instance, handle_callback, is_authenticated

router = APIRouter()


@router.get("/auth/login")
def login(conn: sqlite3.Connection = Depends(get_db)):
    url = get_auth_url(conn)
    return RedirectResponse(url, status_code=302)


@router.get("/auth/callback")
def callback(
    state: str,
    code: Optional[str] = None,
    error: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    if error or not code:
        return RedirectResponse("/?error=access_denied", status_code=302)
    success = handle_callback(conn, code=code, state=state)
    if not success:
        return RedirectResponse("/?error=auth_failed", status_code=302)
    return RedirectResponse("/", status_code=302)


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
