import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from database import get_db

router = APIRouter()


class TagCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v


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
    try:
        conn.execute("INSERT INTO tags (name, source) VALUES (?, 'user')", (name,))
        row = conn.execute(
            "SELECT id, name, color, source FROM tags WHERE name = ?", (name,)
        ).fetchone()
        return dict(row)
    except sqlite3.IntegrityError:
        row = conn.execute(
            "SELECT id, name, color, source FROM tags WHERE name = ?", (name,)
        ).fetchone()
        return JSONResponse(status_code=200, content=dict(row))


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
    cur = conn.execute(
        "DELETE FROM item_tags WHERE item_id = ? AND tag_id = ?", (item_id, tag_id)
    )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Tag not assigned to item")
    return {"ok": True}
