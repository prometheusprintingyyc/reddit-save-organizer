import sqlite3
import time
import logging
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from reddit.auth import get_reddit_instance
from reddit.sync import sync_saved_items

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/sync/status")
def get_sync_status(conn: sqlite3.Connection = Depends(get_db)):
    last = conn.execute(
        "SELECT * FROM sync_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    pending_ai = conn.execute(
        "SELECT COUNT(*) FROM saved_items WHERE ai_status = 'pending'"
    ).fetchone()[0]
    total_items = conn.execute(
        "SELECT COUNT(*) FROM saved_items"
    ).fetchone()[0]
    return {
        "last_sync": dict(last) if last else None,
        "pending_ai": pending_ai,
        "total_items": total_items,
    }


@router.post("/sync/trigger")
def trigger_sync(conn: sqlite3.Connection = Depends(get_db)):
    reddit = get_reddit_instance(conn)
    if not reddit:
        raise HTTPException(status_code=401, detail="Not authenticated with Reddit")
    conn.execute(
        "INSERT INTO sync_log (started_at, status) VALUES (?, 'running')",
        (time.time(),),
    )
    conn.commit()
    log_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    try:
        fetched, new = sync_saved_items(reddit, conn)
        now = time.time()
        conn.execute(
            """UPDATE sync_log
               SET completed_at = ?, items_fetched = ?, items_new = ?, status = 'done'
               WHERE id = ?""",
            (now, fetched, new, log_id),
        )
        conn.commit()
        return {"ok": True, "items_fetched": fetched, "items_new": new}
    except Exception as e:
        logger.exception("Sync failed")
        conn.execute(
            "UPDATE sync_log SET status = 'error', error_message = ? WHERE id = ?",
            (str(e), log_id),
        )
        conn.commit()
        raise HTTPException(status_code=500, detail=str(e))
