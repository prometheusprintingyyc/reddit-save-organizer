import sqlite3
from config import settings


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS saved_items (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            title TEXT,
            body TEXT,
            url TEXT,
            subreddit TEXT NOT NULL DEFAULT '',
            author TEXT,
            score INTEGER DEFAULT 0,
            permalink TEXT,
            created_utc REAL DEFAULT 0,
            saved_at REAL DEFAULT 0,
            synced_at REAL DEFAULT 0,
            summary TEXT,
            ai_status TEXT NOT NULL DEFAULT 'pending',
            ai_error_count INTEGER NOT NULL DEFAULT 0,
            thumbnail_url TEXT,
            is_nsfw INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color TEXT,
            source TEXT NOT NULL DEFAULT 'ai'
        );

        CREATE TABLE IF NOT EXISTS item_tags (
            item_id TEXT NOT NULL REFERENCES saved_items(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (item_id, tag_id)
        );

        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at REAL NOT NULL,
            completed_at REAL,
            items_fetched INTEGER DEFAULT 0,
            items_new INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'running',
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)


def init_db() -> None:
    conn = sqlite3.connect(settings.database_path)
    conn.execute("PRAGMA foreign_keys = ON")
    _create_schema(conn)
    conn.commit()
    conn.close()


def get_credential(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute(
        "SELECT value FROM user_settings WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else default


def get_db():
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
