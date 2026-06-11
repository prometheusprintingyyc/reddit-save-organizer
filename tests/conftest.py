import os

os.environ.setdefault("DATABASE_PATH", "./dev.db")

import sqlite3
import pytest
from database import _create_schema


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _create_schema(conn)
    conn.commit()
    yield conn
    conn.close()
