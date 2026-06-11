import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import get_db

router = APIRouter()


class TagCreate(BaseModel):
    name: str


class ItemTagBody(BaseModel):
    tag_id: int


@router.get("/tags")
def list_tags(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute(
        "SELECT id, name, color, source FROM tags ORDER BY name"
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/tags", status_code=201)
def create_tag(body: TagCreate, conn: sqlite3.Connection = Depends(get_db)):
    name = body.name.strip().lower()
    existing = conn.execute(
        "SELECT id, name, color, source FROM tags WHERE name = ?", (name,)
    ).fetchone()
    if existing:
        return JSONResponse(status_code=200, content=dict(existing))
    conn.execute("INSERT INTO tags (name, source) VALUES (?, 'user')", (name,))
    row = conn.execute(
        "SELECT id, name, color, source FROM tags WHERE name = ?", (name,)
    ).fetchone()
    return dict(row)


@router.post("/items/{item_id}/tags")
def add_tag_to_item(
    item_id: str, body: ItemTagBody, conn: sqlite3.Connection = Depends(get_db)
):
    item = conn.execute(
        "SELECT id FROM saved_items WHERE id = ?", (item_id,)
    ).fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    tag = conn.execute(
        "SELECT id FROM tags WHERE id = ?", (body.tag_id,)
    ).fetchone()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    conn.execute(
        "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
        (item_id, body.tag_id),
    )
    return {"ok": True}


@router.delete("/items/{item_id}/tags/{tag_id}")
def remove_tag_from_item(
    item_id: str, tag_id: int, conn: sqlite3.Connection = Depends(get_db)
):
    conn.execute(
        "DELETE FROM item_tags WHERE item_id = ? AND tag_id = ?", (item_id, tag_id)
    )
    return {"ok": True}
