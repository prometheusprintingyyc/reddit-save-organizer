import sqlite3
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from database import get_db
from config import settings as app_settings

router = APIRouter()


class SettingsPatch(BaseModel):
    sync_interval_hours: int | None = Field(default=None, ge=1)


def _get_setting(conn: sqlite3.Connection, key: str, default: str) -> str:
    row = conn.execute(
        "SELECT value FROM user_settings WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else default


@router.get("/settings")
def get_settings(conn: sqlite3.Connection = Depends(get_db)):
    return {
        "sync_interval_hours": int(
            _get_setting(conn, "sync_interval_hours", str(app_settings.sync_interval_hours))
        ),
    }


@router.patch("/settings")
def update_settings(body: SettingsPatch, conn: sqlite3.Connection = Depends(get_db)):
    if body.sync_interval_hours is not None:
        conn.execute(
            "INSERT OR REPLACE INTO user_settings (key, value) VALUES ('sync_interval_hours', ?)",
            (str(body.sync_interval_hours),),
        )
        conn.commit()
    return {"ok": True}


@router.get("/settings/ai-stats")
def get_ai_stats(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute(
        "SELECT ai_status, COUNT(*) as cnt FROM saved_items GROUP BY ai_status"
    ).fetchall()
    stats = {r["ai_status"]: r["cnt"] for r in rows}
    total = sum(stats.values())
    return {
        "total": total,
        "done": stats.get("done", 0),
        "pending": stats.get("pending", 0),
        "error": stats.get("error", 0),
    }
