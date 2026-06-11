import secrets
import sqlite3
import praw
from config import settings

REDDIT_SCOPES = ["identity", "history", "save"]
USER_AGENT = "redditsave/1.0"


def _reddit_base() -> praw.Reddit:
    return praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        redirect_uri=settings.reddit_redirect_uri,
        user_agent=USER_AGENT,
    )


def is_authenticated(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT value FROM user_settings WHERE key = 'reddit_refresh_token'"
    ).fetchone()
    return row is not None


def get_reddit_instance(conn: sqlite3.Connection) -> praw.Reddit | None:
    row = conn.execute(
        "SELECT value FROM user_settings WHERE key = 'reddit_refresh_token'"
    ).fetchone()
    if not row:
        return None
    return praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        redirect_uri=settings.reddit_redirect_uri,
        user_agent=USER_AGENT,
        refresh_token=row["value"],
    )


def get_auth_url(conn: sqlite3.Connection) -> str:
    state = secrets.token_urlsafe(16)
    conn.execute(
        "INSERT OR REPLACE INTO user_settings (key, value) VALUES ('oauth_state', ?)",
        (state,)
    )
    conn.commit()
    return _reddit_base().auth.url(scopes=REDDIT_SCOPES, state=state, duration="permanent")


def handle_callback(conn: sqlite3.Connection, code: str, state: str) -> bool:
    row = conn.execute(
        "SELECT value FROM user_settings WHERE key = 'oauth_state'"
    ).fetchone()
    if not row or row["value"] != state:
        return False
    reddit = _reddit_base()
    refresh_token = reddit.auth.authorize(code)
    conn.execute(
        "INSERT OR REPLACE INTO user_settings (key, value) VALUES ('reddit_refresh_token', ?)",
        (refresh_token,)
    )
    conn.execute("DELETE FROM user_settings WHERE key = 'oauth_state'")
    conn.commit()
    return True
