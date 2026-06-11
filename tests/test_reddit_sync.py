import time
from unittest.mock import MagicMock


def _make_submission(fullname="t3_abc", title="Test Post", selftext="body text",
                     subreddit="python", score=100, created_utc=None, is_nsfw=False):
    sub = MagicMock()
    sub.fullname = fullname
    sub.title = title
    sub.selftext = selftext
    sub.is_self = True
    sub.url = f"https://www.reddit.com/r/python/comments/abc/test"
    sub.subreddit.display_name = subreddit
    sub.author.name = "testuser"
    sub.score = score
    sub.permalink = f"/r/{subreddit}/comments/abc/test"
    sub.created_utc = created_utc or (time.time() - 100)
    sub.over_18 = is_nsfw
    sub.thumbnail = "self"
    # Make isinstance check work
    import praw.models
    sub.__class__ = praw.models.Submission
    return sub


def _make_comment(fullname="t1_xyz", body="Great comment", subreddit="python", score=50):
    comment = MagicMock()
    comment.fullname = fullname
    comment.body = body
    comment.submission.title = "Parent Post Title"
    comment.subreddit.display_name = subreddit
    comment.author.name = "commenter"
    comment.score = score
    comment.permalink = f"/r/{subreddit}/comments/abc/test/xyz"
    comment.created_utc = time.time() - 100
    import praw.models
    comment.__class__ = praw.models.Comment
    return comment


def test_sync_inserts_new_post(db):
    from reddit.sync import sync_saved_items
    reddit = MagicMock()
    reddit.user.me.return_value.saved.return_value = [_make_submission()]
    fetched, new = sync_saved_items(reddit, db)
    assert fetched == 1
    assert new == 1
    row = db.execute("SELECT * FROM saved_items WHERE id = 't3_abc'").fetchone()
    assert row["type"] == "post"
    assert row["title"] == "Test Post"
    assert row["ai_status"] == "pending"


def test_sync_upserts_existing_post(db):
    from reddit.sync import sync_saved_items
    reddit = MagicMock()
    sub = _make_submission(score=100)
    reddit.user.me.return_value.saved.return_value = [sub]
    sync_saved_items(reddit, db)
    sub.score = 200
    reddit.user.me.return_value.saved.return_value = [sub]
    fetched, new = sync_saved_items(reddit, db)
    assert new == 0  # Not new on second sync
    row = db.execute("SELECT score FROM saved_items WHERE id = 't3_abc'").fetchone()
    assert row["score"] == 200


def test_sync_applies_old_tag_for_old_post(db):
    from reddit.sync import sync_saved_items
    reddit = MagicMock()
    old_time = time.time() - (400 * 24 * 3600)  # 400 days ago
    reddit.user.me.return_value.saved.return_value = [_make_submission(created_utc=old_time)]
    sync_saved_items(reddit, db)
    tags = db.execute("""
        SELECT t.name FROM item_tags it JOIN tags t ON it.tag_id = t.id WHERE it.item_id = 't3_abc'
    """).fetchall()
    tag_names = {row["name"] for row in tags}
    assert "old" in tag_names


def test_sync_inserts_comment(db):
    from reddit.sync import sync_saved_items
    reddit = MagicMock()
    reddit.user.me.return_value.saved.return_value = [_make_comment()]
    fetched, new = sync_saved_items(reddit, db)
    assert new == 1
    row = db.execute("SELECT * FROM saved_items WHERE id = 't1_xyz'").fetchone()
    assert row["type"] == "comment"
    assert row["title"] == "Parent Post Title"
