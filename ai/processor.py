import json
import logging
import re
import sqlite3
import time
from urllib.parse import urlparse

import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 17


def _get_model():
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


def build_prompt(item: dict, existing_tags: list[str]) -> str:
    if item["type"] == "comment":
        content = f'Title of saved post: "{item["title"]}"\nSaved comment: {(item["body"] or "")[:500]}'
    elif item["url"] and "reddit.com" not in item["url"]:
        domain = urlparse(item["url"]).netloc
        content = f'Title: "{item["title"]}"\nSubreddit: r/{item["subreddit"]}\nLinks to: {domain}'
    else:
        body = (item["body"] or "")[:500]
        content = f'Title: "{item["title"]}"\n{body}'.strip()

    tags_hint = ""
    if existing_tags:
        sample = ", ".join(existing_tags[:50])
        tags_hint = f"\nPrefer reusing these existing tags where relevant: {sample}"

    return f"""Summarize this saved Reddit item and assign tags.

{content}

Respond with JSON only (no markdown fences):
{{
  "summary": "1-2 sentence plain English summary",
  "tags": ["tag1", "tag2"]
}}

Rules:
- summary: factual, 1-2 sentences, no filler phrases
- tags: 2-5 lowercase strings, hyphens instead of spaces{tags_hint}"""


def parse_response(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


def _get_existing_tags(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM tags WHERE source IN ('ai', 'user') ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows]


def process_batch(conn: sqlite3.Connection) -> int:
    rows = conn.execute("""
        SELECT id, type, title, body, url, subreddit
        FROM saved_items
        WHERE ai_status = 'pending' AND ai_error_count < 3
        LIMIT ?
    """, (BATCH_SIZE,)).fetchall()

    if not rows:
        return 0

    model = _get_model()
    existing_tags = _get_existing_tags(conn)
    processed = 0

    for row in rows:
        item = dict(row)
        prompt = build_prompt(item, existing_tags)
        try:
            response = model.generate_content(prompt)
            result = parse_response(response.text)
            summary = result.get("summary", "")
            tags = [t.lower().strip().replace(" ", "-") for t in result.get("tags", []) if t.strip()]

            conn.execute(
                "UPDATE saved_items SET summary = ?, ai_status = 'done' WHERE id = ?",
                (summary, item["id"])
            )
            for tag_name in tags:
                conn.execute(
                    "INSERT OR IGNORE INTO tags (name, source) VALUES (?, 'ai')", (tag_name,)
                )
                conn.execute("""
                    INSERT OR IGNORE INTO item_tags (item_id, tag_id)
                    SELECT ?, id FROM tags WHERE name = ?
                """, (item["id"], tag_name))
            conn.commit()
            existing_tags = list(set(existing_tags + tags))
            processed += 1
        except Exception as e:
            logger.warning("AI processing failed for %s: %s", item["id"], e)
            conn.execute("""
                UPDATE saved_items
                SET ai_error_count = ai_error_count + 1,
                    ai_status = CASE WHEN ai_error_count + 1 >= 3 THEN 'error' ELSE 'pending' END
                WHERE id = ?
            """, (item["id"],))
            conn.commit()

        time.sleep(0.05)

    return processed
