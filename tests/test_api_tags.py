import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(db):
    from main import app
    from database import get_db
    app.dependency_overrides[get_db] = lambda: (yield db)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_tags_empty(client):
    response = client.get("/api/tags")
    assert response.status_code == 200
    assert response.json() == []


def test_list_tags_returns_all(client, db):
    db.execute("INSERT INTO tags (name, source) VALUES ('python', 'ai')")
    db.execute("INSERT INTO tags (name, source) VALUES ('tutorial', 'user')")
    db.commit()
    response = client.get("/api/tags")
    data = response.json()
    assert len(data) == 2
    names = {t["name"] for t in data}
    assert names == {"python", "tutorial"}


def test_create_tag_succeeds(client):
    response = client.post("/api/tags", json={"name": "newtag"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "newtag"
    assert data["source"] == "user"
    assert data["id"] is not None


def test_create_tag_duplicate_returns_existing(client, db):
    db.execute("INSERT INTO tags (name, source) VALUES ('existing', 'ai')")
    db.commit()
    response = client.post("/api/tags", json={"name": "existing"})
    assert response.status_code == 200
    assert response.json()["name"] == "existing"


def test_create_tag_normalizes_to_lowercase(client):
    response = client.post("/api/tags", json={"name": "MyTag"})
    assert response.status_code == 201
    assert response.json()["name"] == "mytag"


def test_add_tag_to_item(client, db):
    import time
    db.execute("""
        INSERT INTO saved_items
        (id, type, title, body, subreddit, author, score, permalink,
         created_utc, saved_at, synced_at, ai_status, ai_error_count, is_nsfw)
        VALUES ('t3_x', 'post', 'T', 'B', 'sub', 'u', 1, '/r/sub', ?, ?, ?, 'done', 0, 0)
    """, (time.time(), time.time(), time.time()))
    db.execute("INSERT INTO tags (name, source) VALUES ('cool', 'user')")
    tag_id = db.execute("SELECT id FROM tags WHERE name='cool'").fetchone()[0]
    db.commit()
    response = client.post("/api/items/t3_x/tags", json={"tag_id": tag_id})
    assert response.status_code == 200
    row = db.execute(
        "SELECT 1 FROM item_tags WHERE item_id='t3_x' AND tag_id=?", (tag_id,)
    ).fetchone()
    assert row is not None


def test_remove_tag_from_item(client, db):
    import time
    db.execute("""
        INSERT INTO saved_items
        (id, type, title, body, subreddit, author, score, permalink,
         created_utc, saved_at, synced_at, ai_status, ai_error_count, is_nsfw)
        VALUES ('t3_y', 'post', 'T', 'B', 'sub', 'u', 1, '/r/sub', ?, ?, ?, 'done', 0, 0)
    """, (time.time(), time.time(), time.time()))
    db.execute("INSERT INTO tags (name, source) VALUES ('removeme', 'user')")
    tag_id = db.execute("SELECT id FROM tags WHERE name='removeme'").fetchone()[0]
    db.execute("INSERT INTO item_tags (item_id, tag_id) VALUES ('t3_y', ?)", (tag_id,))
    db.commit()
    response = client.delete(f"/api/items/t3_y/tags/{tag_id}")
    assert response.status_code == 200
    row = db.execute(
        "SELECT 1 FROM item_tags WHERE item_id='t3_y' AND tag_id=?", (tag_id,)
    ).fetchone()
    assert row is None
