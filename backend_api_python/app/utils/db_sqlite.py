"""
SQLite Database Connection Utility
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config.database import SQLiteConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

_local = threading.local()


def _now_utc_str() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


_INTERVAL_LITERAL_RE = re.compile(
    r"NOW\(\)\s*([+-])\s*INTERVAL\s*'(\d+)\s+([a-zA-Z]+)'",
    re.IGNORECASE,
)
_INTERVAL_PARAM_RE = re.compile(
    r"NOW\(\)\s*([+-])\s*INTERVAL\s*'\s*\?\s*([a-zA-Z]+)\s*'",
    re.IGNORECASE,
)


def _normalize_interval_unit(unit: str) -> str:
    u = (unit or "").strip().lower()
    if u.endswith("s"):
        u = u[:-1]
    if u not in {"second", "minute", "hour", "day"}:
        return "second"
    return u


def _convert_sql_for_sqlite(query: str) -> str:
    q = query

    q = q.replace("%s", "?")

    def _repl_literal(m: re.Match[str]) -> str:
        sign = m.group(1)
        n = m.group(2)
        unit = _normalize_interval_unit(m.group(3))
        mod = f"{sign}{n} {unit}s"
        return f"datetime('now', '{mod}')"

    q = _INTERVAL_LITERAL_RE.sub(_repl_literal, q)

    def _repl_param(m: re.Match[str]) -> str:
        sign = m.group(1)
        unit = _normalize_interval_unit(m.group(2))
        return f"datetime('now', '{sign}' || ? || ' {unit}s')"

    q = _INTERVAL_PARAM_RE.sub(_repl_param, q)

    return q


def _open_connection() -> sqlite3.Connection:
    db_path = SQLiteConfig.get_path()
    def _connect(path: str) -> sqlite3.Connection:
        db_dir = os.path.dirname(path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.execute("PRAGMA schema_version;")
        return conn

    try:
        conn = _connect(db_path)
    except Exception:
        fallback_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        fallback_path = os.path.join(fallback_base, "data", "zhiyiquant.db")
        conn = _connect(fallback_path)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
    except Exception:
        pass

    try:
        conn.create_function("NOW", 0, _now_utc_str)
    except Exception:
        pass

    return conn


def _get_thread_connection() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = _open_connection()
        _local.conn = conn
    return conn


class SQLiteCursor:
    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor

    def execute(self, query: str, args: Any = None):
        q = _convert_sql_for_sqlite(query)
        if args is None:
            return self._cursor.execute(q)
        if not isinstance(args, (tuple, list)):
            args = (args,)
        return self._cursor.execute(q, args)

    def executemany(self, query: str, seq_of_args):
        q = _convert_sql_for_sqlite(query)
        return self._cursor.executemany(q, seq_of_args)

    def fetchone(self) -> Optional[Dict[str, Any]]:
        row = self._cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, sqlite3.Row):
            return dict(row)
        return row

    def fetchall(self) -> List[Dict[str, Any]]:
        rows = self._cursor.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], sqlite3.Row):
            return [dict(r) for r in rows]
        return rows

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass

    @property
    def lastrowid(self) -> Optional[int]:
        try:
            return self._cursor.lastrowid
        except Exception:
            return None

    @property
    def rowcount(self) -> int:
        try:
            return self._cursor.rowcount
        except Exception:
            return -1


class SQLiteConnection:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def cursor(self) -> SQLiteCursor:
        return SQLiteCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        pass


@contextmanager
def get_sqlite_connection():
    conn = _get_thread_connection()
    db = SQLiteConnection(conn)
    try:
        yield db
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.error(f"SQLite operation error: {e}")
        raise


def get_sqlite_connection_sync() -> SQLiteConnection:
    return SQLiteConnection(_get_thread_connection())


def execute_sql(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    with get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if sql.strip().upper().startswith("SELECT"):
            return cursor.fetchall()
        conn.commit()
        return []


def is_sqlite_available() -> bool:
    try:
        with get_sqlite_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
        return True
    except Exception:
        return False


def close_pool():
    conn = getattr(_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        try:
            delattr(_local, "conn")
        except Exception:
            pass
