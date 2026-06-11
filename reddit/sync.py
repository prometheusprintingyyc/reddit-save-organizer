import time
import sqlite3
import praw
import praw.models


def apply_system_tags(conn: sqlite3.Connection, item_id: str, subreddit: str,
                      is_nsfw: bool, created_utc: float, is_deleted: bool = False) -> None:
    one_year_ago = time.time() - (365 * 24 * 3600)
    system_tags = [f"r/{subreddit.lower()}"]
    if is_nsfw:
        system_tags.append("nsfw")
    if created_utc < one_year_ago:
        system_tags.append("old")
    if is_deleted:
        system_tags.append("deleted")
    for name in system_tags:
        conn.execute("INSERT OR IGNORE INTO tags (name, source) VALUES (?, 'system')", (name,))
        conn.execute("""
            INSERT OR IGNORE INTO item_tags (item_id, tag_id)
            SELECT ?, id FROM tags WHERE name = ?
        """, (item_id, name))


def sync_saved_items(reddit: praw.Reddit, conn: sqlite3.Connection) -> tuple[int, int]:
    fetched = 0
    new = 0
    now = time.time()

    for item in reddit.user.me().saved(limit=None):
        fetched += 1

        if isinstance(item, praw.models.Submission):
            item_id = item.fullname
            item_type = "post"
            title = item.title
            is_deleted = item.selftext in ("[removed]", "[deleted]")
            body = "" if is_deleted else item.selftext
            url = None if item.is_self else item.url
            subreddit = item.subreddit.display_name
            author = str(item.author) if item.author else "[deleted]"
            score = item.score
            permalink = f"https://reddit.com{item.permalink}"
            created_utc = item.created_utc
            is_nsfw = item.over_18
            thumbnail_url = item.thumbnail if item.thumbnail.startswith("http") else None
        elif isinstance(item, praw.models.Comment):
            item_id = item.fullname
            item_type = "comment"
            title = item.submission.title
            body = item.body
            url = None
            subreddit = item.subreddit.display_name
            author = str(item.author) if item.author else "[deleted]"
            score = item.score
            permalink = f"https://reddit.com{item.permalink}"
            created_utc = item.created_utc
            is_nsfw = False
            is_deleted = False
            thumbnail_url = None
        else:
            continue

        existing = conn.execute("SELECT id FROM saved_items WHERE id = ?", (item_id,)).fetchone()

        if existing:
            conn.execute(
                "UPDATE saved_items SET score = ?, synced_at = ? WHERE id = ?",
                (score, now, item_id)
            )
        else:
            new += 1
            conn.execute("""
                INSERT INTO saved_items
                (id, type, title, body, url, subreddit, author, score, permalink,
                 created_utc, saved_at, synced_at, ai_status, ai_error_count, is_nsfw, thumbnail_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?)
            """, (item_id, item_type, title, body, url, subreddit, author, score,
                  permalink, created_utc, now, now, 1 if is_nsfw else 0, thumbnail_url))
            apply_system_tags(conn, item_id, subreddit, is_nsfw, created_utc, is_deleted)

    conn.commit()
    return fetched, new
