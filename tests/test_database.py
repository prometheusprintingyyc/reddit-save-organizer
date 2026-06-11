import sqlite3
import pytest


def test_schema_creates_all_tables(db):
    tables = {row[0] for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert {"saved_items", "tags", "item_tags", "sync_log", "user_settings"} <= tables


def test_user_settings_crud(db):
    db.execute("INSERT INTO user_settings (key, value) VALUES ('test_key', 'test_val')")
    db.commit()
    row = db.execute("SELECT value FROM user_settings WHERE key = 'test_key'").fetchone()
    assert row["value"] == "test_val"


def test_item_tags_cascade_delete(db):
    db.execute("""
        INSERT INTO saved_items (id, type, subreddit, ai_status, ai_error_count)
        VALUES ('t3_abc', 'post', 'python', 'pending', 0)
    """)
    db.execute("INSERT INTO tags (name, source) VALUES ('python', 'ai')")
    db.execute("INSERT INTO item_tags (item_id, tag_id) VALUES ('t3_abc', 1)")
    db.commit()
    db.execute("DELETE FROM saved_items WHERE id = 't3_abc'")
    db.commit()
    count = db.execute("SELECT COUNT(*) FROM item_tags WHERE item_id = 't3_abc'").fetchone()[0]
    assert count == 0
