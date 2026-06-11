import secrets
import sqlite3
import praw
import prawcore.exceptions
from config import settings
from database import get_credential

REDDIT_SCOPES = ["identity", "history", "save"]
USER_AGENT = "redditsave/1.0"


def _reddit_base(conn: sqlite3.Connection | None = None) -> praw.Reddit:
    client_id = (get_credential(conn, "reddit_client_id") if conn else "") or settings.reddit_client_id
    client_secret = (get_credential(conn, "reddit_client_secret") if conn else "") or settings.reddit_client_secret
    redirect_uri = (get_credential(conn, "reddit_redirect_uri") if conn else "") or settings.reddit_redirect_uri
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
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
    client_id = get_credential(conn, "reddit_client_id") or settings.reddit_client_id
    client_secret = get_credential(conn, "reddit_client_secret") or settings.reddit_client_secret
    redirect_uri = get_credential(conn, "reddit_redirect_uri") or settings.reddit_redirect_uri
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        user_agent=USER_AGENT,
        refresh_token=row["value"],
    )


def get_auth_url(conn: sqlite3.Connection) -> str:
    state = secrets.token_urlsafe(16)
    conn.execute(
        "INSERT OR REPLACE INTO user_settings (key, value) VALUES ('oauth_state', ?)",
        (state,)
    )
    return _reddit_base(conn).auth.url(scopes=REDDIT_SCOPES, state=state, duration="permanent")


def handle_callback(conn: sqlite3.Connection, code: str, state: str) -> bool:
    row = conn.execute(
        "SELECT value FROM user_settings WHERE key = 'oauth_state'"
    ).fetchone()
    if not row or row["value"] != state:
        return False
    reddit = _reddit_base(conn)
    try:
        refresh_token = reddit.auth.authorize(code)
    except prawcore.exceptions.OAuthException:
        return False
    if not refresh_token:
        return False
    conn.execute(
        "INSERT OR REPLACE INTO user_settings (key, value) VALUES ('reddit_refresh_token', ?)",
        (refresh_token,)
    )
    conn.execute("DELETE FROM user_settings WHERE key = 'oauth_state'")
    return True
