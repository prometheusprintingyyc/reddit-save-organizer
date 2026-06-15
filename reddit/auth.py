import sqlite3
import praw
from config import settings
from database import get_credential

USER_AGENT = "redditsave/1.0"


def get_reddit_instance(conn: sqlite3.Connection) -> praw.Reddit | None:
    client_id = get_credential(conn, "reddit_client_id") or settings.reddit_client_id
    client_secret = get_credential(conn, "reddit_client_secret") or settings.reddit_client_secret
    username = get_credential(conn, "reddit_username") or settings.reddit_username
    password = get_credential(conn, "reddit_password") or settings.reddit_password

    if not all([client_id, client_secret, username, password]):
        return None

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        user_agent=USER_AGENT,
    )


def is_authenticated(conn: sqlite3.Connection) -> bool:
    client_id = get_credential(conn, "reddit_client_id") or settings.reddit_client_id
    client_secret = get_credential(conn, "reddit_client_secret") or settings.reddit_client_secret
    username = get_credential(conn, "reddit_username") or settings.reddit_username
    password = get_credential(conn, "reddit_password") or settings.reddit_password
    return bool(client_id and client_secret and username and password)
