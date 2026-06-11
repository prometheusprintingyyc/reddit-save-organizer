import time
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client(db):
    from main import app
    from database import get_db
    app.dependency_overrides[get_db] = lambda: (yield db)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _seed_sync_log(db, status="done", started_at=None, completed_at=None,
                   items_fetched=10, items_new=5):
    db.execute("""
        INSERT INTO sync_log (started_at, completed_at, items_fetched, items_new, status)
        VALUES (?, ?, ?, ?, ?)
    """, (started_at or time.time(), completed_at or time.time(), items_fetched, items_new, status))
    db.commit()


# --- sync_routes tests ---

def test_get_sync_status_empty(client):
    response = client.get("/api/sync/status")
    assert response.status_code == 200
    data = response.json()
    assert data["last_sync"] is None
    assert data["pending_ai"] == 0
    assert data["total_items"] == 0


def test_get_sync_status_with_log(client, db):
    _seed_sync_log(db, status="done", items_fetched=20, items_new=3)
    response = client.get("/api/sync/status")
    data = response.json()
    assert data["last_sync"]["status"] == "done"
    assert data["last_sync"]["items_fetched"] == 20


def test_trigger_sync_unauthenticated(client):
    with patch("api.sync_routes.get_reddit_instance", return_value=None):
        response = client.post("/api/sync/trigger")
    assert response.status_code == 401


def test_trigger_sync_success(client, db):
    mock_reddit = MagicMock()
    with patch("api.sync_routes.get_reddit_instance", return_value=mock_reddit), \
         patch("api.sync_routes.sync_saved_items", return_value=(10, 3)):
        response = client.post("/api/sync/trigger")
    assert response.status_code == 200
    data = response.json()
    assert data["items_fetched"] == 10
    assert data["items_new"] == 3
    row = db.execute("SELECT status FROM sync_log ORDER BY id DESC LIMIT 1").fetchone()
    assert row["status"] == "done"


def test_trigger_sync_writes_error_on_failure(client, db):
    mock_reddit = MagicMock()
    with patch("api.sync_routes.get_reddit_instance", return_value=mock_reddit), \
         patch("api.sync_routes.sync_saved_items", side_effect=Exception("boom")):
        response = client.post("/api/sync/trigger")
    assert response.status_code == 500
    row = db.execute("SELECT status, error_message FROM sync_log ORDER BY id DESC LIMIT 1").fetchone()
    assert row["status"] == "error"
    assert "boom" in row["error_message"]


# --- settings tests ---

def test_get_settings_defaults(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "sync_interval_hours" in data


def test_update_setting(client, db):
    response = client.patch("/api/settings", json={"sync_interval_hours": 12})
    assert response.status_code == 200
    row = db.execute(
        "SELECT value FROM user_settings WHERE key = 'sync_interval_hours'"
    ).fetchone()
    assert row["value"] == "12"


def test_get_ai_stats(client, db):
    import time as t
    for status in ["pending", "done", "done", "error"]:
        db.execute("""
            INSERT INTO saved_items
            (id, type, title, body, subreddit, author, score, permalink,
             created_utc, saved_at, synced_at, ai_status, ai_error_count, is_nsfw)
            VALUES (?, 'post', 'T', 'B', 'sub', 'u', 1, '/r/sub', ?, ?, ?, ?, 0, 0)
        """, (f"t3_{status[:2]}{t.time()}", t.time(), t.time(), t.time(), status))
    db.commit()
    response = client.get("/api/settings/ai-stats")
    data = response.json()
    assert data["total"] == 4
    assert data["done"] == 2
    assert data["pending"] == 1
    assert data["error"] == 1
