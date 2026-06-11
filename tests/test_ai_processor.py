import time
from unittest.mock import MagicMock, patch


def _insert_item(db, item_id="t3_abc", item_type="post", title="Test", body="body",
                 url=None, subreddit="python", ai_status="pending", ai_error_count=0):
    db.execute("""
        INSERT INTO saved_items
        (id, type, title, body, url, subreddit, author, score, permalink,
         created_utc, saved_at, synced_at, ai_status, ai_error_count, is_nsfw)
        VALUES (?, ?, ?, ?, ?, ?, 'user', 10, '/r/test', ?, ?, ?, ?, ?, 0)
    """, (item_id, item_type, title, body, url, subreddit,
          time.time(), time.time(), time.time(), ai_status, ai_error_count))
    db.commit()


def test_build_prompt_text_post():
    from ai.processor import build_prompt
    item = {"type": "post", "title": "How to use FastAPI", "body": "Install it first",
            "url": None, "subreddit": "python"}
    prompt = build_prompt(item, existing_tags=[])
    assert "How to use FastAPI" in prompt
    assert "Install it first" in prompt


def test_build_prompt_comment_uses_parent_title():
    from ai.processor import build_prompt
    item = {"type": "comment", "title": "Parent Post Title", "body": "Great answer",
            "url": None, "subreddit": "python"}
    prompt = build_prompt(item, existing_tags=[])
    assert "Parent Post Title" in prompt
    assert "Great answer" in prompt


def test_build_prompt_includes_existing_tags():
    from ai.processor import build_prompt
    item = {"type": "post", "title": "T", "body": "B", "url": None, "subreddit": "python"}
    prompt = build_prompt(item, existing_tags=["python", "tutorial"])
    assert "python" in prompt
    assert "tutorial" in prompt


def test_parse_response_plain_json():
    from ai.processor import parse_response
    text = '{"summary": "A great post.", "tags": ["python", "tutorial"]}'
    result = parse_response(text)
    assert result["summary"] == "A great post."
    assert result["tags"] == ["python", "tutorial"]


def test_parse_response_strips_markdown_fences():
    from ai.processor import parse_response
    text = '```json\n{"summary": "Post.", "tags": ["a"]}\n```'
    result = parse_response(text)
    assert result["summary"] == "Post."


def test_process_batch_marks_item_done(db):
    from ai.processor import process_batch
    _insert_item(db)
    mock_response = MagicMock()
    mock_response.text = '{"summary": "A post about Python.", "tags": ["python", "web"]}'
    with patch("ai.processor._get_model") as mock_get_model:
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_get_model.return_value = mock_model
        count = process_batch(db)
    assert count == 1
    row = db.execute("SELECT ai_status, summary FROM saved_items WHERE id = 't3_abc'").fetchone()
    assert row["ai_status"] == "done"
    assert "Python" in row["summary"]


def test_process_batch_increments_error_count_on_failure(db):
    from ai.processor import process_batch
    _insert_item(db)
    with patch("ai.processor._get_model") as mock_get_model:
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API error")
        mock_get_model.return_value = mock_model
        process_batch(db)
    row = db.execute("SELECT ai_error_count, ai_status FROM saved_items WHERE id = 't3_abc'").fetchone()
    assert row["ai_error_count"] == 1
    assert row["ai_status"] == "pending"


def test_process_batch_sets_error_status_after_three_failures(db):
    from ai.processor import process_batch
    _insert_item(db, ai_error_count=2)
    with patch("ai.processor._get_model") as mock_get_model:
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API error")
        mock_get_model.return_value = mock_model
        process_batch(db)
    row = db.execute("SELECT ai_status FROM saved_items WHERE id = 't3_abc'").fetchone()
    assert row["ai_status"] == "error"
