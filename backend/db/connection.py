from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from backend.config import DATABASE_PATH
from backend.errors import APIError, INFERENCE_ERROR

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(path: Path | None = None) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(path) as connection:
        connection.executescript(schema)


@contextmanager
def session(path: Path | None = None):
    connection = connect(path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def check_database(path: Path | None = None) -> str:
    try:
        with session(path) as connection:
            connection.execute("SELECT 1").fetchone()
        return "ok"
    except sqlite3.Error as exc:
        raise APIError(500, INFERENCE_ERROR, f"Database unavailable: {exc}") from exc
