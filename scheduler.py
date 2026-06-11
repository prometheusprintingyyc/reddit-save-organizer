import sqlite3
import time
from apscheduler.schedulers.background import BackgroundScheduler
from config import settings
from database import _create_schema


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _create_schema(conn)
    conn.commit()
    return conn


def run_sync_job() -> None:
    conn = _get_conn()
    from reddit.auth import get_reddit_instance
    from reddit.sync import sync_saved_items
    reddit = get_reddit_instance(conn)
    if not reddit:
        conn.close()
        return
    log_id = conn.execute(
        "INSERT INTO sync_log (started_at, status) VALUES (?, 'running')", (time.time(),)
    ).lastrowid
    conn.commit()
    try:
        fetched, new = sync_saved_items(reddit, conn)
        conn.execute(
            "UPDATE sync_log SET status='done', completed_at=?, items_fetched=?, items_new=? WHERE id=?",
            (time.time(), fetched, new, log_id)
        )
    except Exception as e:
        conn.execute(
            "UPDATE sync_log SET status='error', completed_at=?, error_message=? WHERE id=?",
            (time.time(), str(e), log_id)
        )
    conn.commit()
    conn.close()


def run_ai_job() -> None:
    conn = _get_conn()
    from ai.processor import process_batch
    process_batch(conn)
    conn.close()


def create_scheduler(sync_interval_hours: int = 6) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_sync_job, "interval", hours=sync_interval_hours, id="sync")
    scheduler.add_job(run_ai_job, "interval", minutes=15, id="ai_processor")
    return scheduler
