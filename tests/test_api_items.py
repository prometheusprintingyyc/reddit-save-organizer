import time
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


def _seed_item(db, item_id="t3_abc", title="Test Post", subreddit="python",
               ai_status="done", created_utc=None, is_nsfw=0):
    db.execute("""
        INSERT INTO saved_items
        (id, type, title, body, subreddit, author, score, permalink,
         created_utc, saved_at, synced_at, ai_status, ai_error_count, is_nsfw)
        VALUES (?, 'post', ?, 'body', ?, 'user', 10, '/r/test',
                ?, ?, ?, ?, 0, ?)
    """, (item_id, title, subreddit,
          created_utc or time.time(), time.time(), time.time(), ai_status, is_nsfw))
    db.commit()


@pytest.fixture
def client(db):
    from main import app
    from database import get_db
    app.dependency_overrides[get_db] = lambda: (yield db)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_items_returns_empty(client):
    response = client.get("/api/items")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_items_returns_seeded_item(client, db):
    _seed_item(db)
    response = client.get("/api/items")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == "t3_abc"
    assert items[0]["tags"] == []


def test_list_items_filter_by_type(client, db):
    _seed_item(db, "t3_post", title="A Post")
    db.execute("""
        INSERT INTO saved_items
        (id, type, title, body, subreddit, author, score, permalink,
         created_utc, saved_at, synced_at, ai_status, ai_error_count, is_nsfw)
        VALUES ('t1_cmt', 'comment', 'A Comment', 'body', 'python', 'user', 5,
                '/r/test', ?, ?, ?, 'done', 0, 0)
    """, (time.time(), time.time(), time.time()))
    db.commit()
    response = client.get("/api/items?type=comment")
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == "t1_cmt"


def test_list_items_filter_by_tag(client, db):
    _seed_item(db, "t3_tagged")
    _seed_item(db, "t3_untagged", title="Other")
    db.execute("INSERT INTO tags (name, source) VALUES ('python', 'ai')")
    db.execute("INSERT INTO item_tags (item_id, tag_id) VALUES ('t3_tagged', 1)")
    db.commit()
    response = client.get("/api/items?tags=python")
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == "t3_tagged"


def test_delete_item_removes_from_db(client, db):
    _seed_item(db)
    with patch("api.items.get_reddit_instance", return_value=None):
        response = client.delete("/api/items/t3_abc")
    assert response.status_code == 200
    row = db.execute("SELECT id FROM saved_items WHERE id = 't3_abc'").fetchone()
    assert row is None


def test_bulk_unsave_removes_items(client, db):
    _seed_item(db, "t3_a")
    _seed_item(db, "t3_b", title="B")
    with patch("api.items.get_reddit_instance", return_value=None):
        response = client.post("/api/items/bulk-unsave", json={"ids": ["t3_a", "t3_b"]})
    assert response.status_code == 200
    count = db.execute("SELECT COUNT(*) FROM saved_items").fetchone()[0]
    assert count == 0
