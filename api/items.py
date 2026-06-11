import sqlite3
import time
from typing import Optional
from fastapi import APIRouter, Depends
from database import get_db
from reddit.auth import get_reddit_instance

router = APIRouter()


def _get_items_with_tags(conn: sqlite3.Connection, conditions: list[str],
                         params: list, limit: int, offset: int) -> tuple[list[dict], int]:
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    total = conn.execute(f"SELECT COUNT(*) FROM saved_items si {where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT si.* FROM saved_items si {where} ORDER BY si.saved_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        tag_rows = conn.execute("""
            SELECT t.id, t.name, t.color, t.source
            FROM item_tags it JOIN tags t ON it.tag_id = t.id
            WHERE it.item_id = ? ORDER BY t.name
        """, (item["id"],)).fetchall()
        item["tags"] = [dict(t) for t in tag_rows]
        items.append(item)
    return items, total


@router.get("/items")
def list_items(
    search: Optional[str] = None,
    tags: Optional[str] = None,
    type: Optional[str] = None,
    age: Optional[str] = None,
    subreddit: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    conn: sqlite3.Connection = Depends(get_db),
):
    conditions: list[str] = []
    params: list = []

    if search:
        like = f"%{search}%"
        conditions.append("""(
            si.title LIKE ? OR si.summary LIKE ? OR
            EXISTS (SELECT 1 FROM item_tags it JOIN tags t ON it.tag_id = t.id
                    WHERE it.item_id = si.id AND t.name LIKE ?)
        )""")
        params.extend([like, like, like])

    if type:
        conditions.append("si.type = ?")
        params.append(type)

    if subreddit:
        conditions.append("si.subreddit = ?")
        params.append(subreddit)

    if age == "old":
        conditions.append("si.created_utc < ?")
        params.append(time.time() - 365 * 24 * 3600)

    if tags:
        for tag in (t.strip() for t in tags.split(",") if t.strip()):
            conditions.append("""EXISTS (
                SELECT 1 FROM item_tags it JOIN tags t ON it.tag_id = t.id
                WHERE it.item_id = si.id AND t.name = ?
            )""")
            params.append(tag)

    items, total = _get_items_with_tags(conn, conditions, params, limit, (page - 1) * limit)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.delete("/items/{item_id}")
def delete_item(item_id: str, conn: sqlite3.Connection = Depends(get_db)):
    reddit = get_reddit_instance(conn)
    if reddit:
        try:
            item = conn.execute("SELECT type FROM saved_items WHERE id = ?", (item_id,)).fetchone()
            if item:
                obj = reddit.submission(id=item_id[3:]) if item["type"] == "post" \
                    else reddit.comment(id=item_id[3:])
                obj.unsave()
        except Exception:
            pass
    conn.execute("DELETE FROM saved_items WHERE id = ?", (item_id,))
    return {"ok": True}


@router.post("/items/bulk-unsave")
def bulk_unsave(body: dict, conn: sqlite3.Connection = Depends(get_db)):
    ids: list[str] = body.get("ids", [])
    reddit = get_reddit_instance(conn)
    for item_id in ids:
        if reddit:
            try:
                item = conn.execute(
                    "SELECT type FROM saved_items WHERE id = ?", (item_id,)
                ).fetchone()
                if item:
                    obj = reddit.submission(id=item_id[3:]) if item["type"] == "post" \
                        else reddit.comment(id=item_id[3:])
                    obj.unsave()
            except Exception:
                pass
        conn.execute("DELETE FROM saved_items WHERE id = ?", (item_id,))
    return {"ok": True, "removed": len(ids)}
