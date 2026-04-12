"""
SQLite database helpers used by the desktop application.
"""

from __future__ import annotations

import os

from app.utils.db_sqlite import (
    close_pool as close_db,
    execute_sql,
    get_sqlite_connection as get_db_connection,
    get_sqlite_connection_sync as get_db_connection_sync,
    is_sqlite_available,
)

LEGACY_TABLE_RENAMES = {
    "qd_users": "zhiyiquant_users",
    "qd_strategies_trading": "zhiyiquant_strategies_trading",
    "qd_strategy_positions": "zhiyiquant_strategy_positions",
    "qd_strategy_trades": "zhiyiquant_strategy_trades",
    "qd_strategy_notifications": "zhiyiquant_strategy_notifications",
    "qd_indicator_codes": "zhiyiquant_indicator_codes",
    "qd_watchlist": "zhiyiquant_watchlist",
    "qd_analysis_memory": "zhiyiquant_analysis_memory",
    "qd_backtest_runs": "zhiyiquant_backtest_runs",
    "qd_exchange_credentials": "zhiyiquant_exchange_credentials",
    "qd_manual_positions": "zhiyiquant_manual_positions",
    "qd_manual_positions_closed": "zhiyiquant_manual_positions_closed",
    "qd_position_alerts": "zhiyiquant_position_alerts",
    "qd_position_monitors": "zhiyiquant_position_monitors",
    "qd_market_symbols": "zhiyiquant_market_symbols",
}

REQUIRED_COLUMNS = {
    "zhiyiquant_strategies_trading": {
        "last_rebalance_at": "TIMESTAMP",
    },
    "zhiyiquant_position_monitors": {
        "last_error": "TEXT DEFAULT ''",
    },
    "zhiyiquant_market_symbols": {
        "updated_at": "TIMESTAMP",
    },
}


def get_db_type() -> str:
    return "sqlite"


def _load_init_sql() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    init_sql_path = os.path.join(base_dir, "migrations", "init.sql")
    if not os.path.exists(init_sql_path):
        raise FileNotFoundError(f"init.sql not found at {init_sql_path}")
    with open(init_sql_path, "r", encoding="utf-8") as file:
        return file.read()


def _list_tables(conn) -> set[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    rows = cursor.fetchall() or []
    cursor.close()
    return {str(row.get("name") or "") for row in rows}


def _list_columns(conn, table_name: str) -> set[str]:
    cursor = conn.cursor()
    cursor.execute(f'PRAGMA table_info("{table_name}")')
    rows = cursor.fetchall() or []
    cursor.close()
    return {str(row.get("name") or "") for row in rows}


def _migrate_legacy_tables(conn, logger) -> None:
    tables = _list_tables(conn)
    renamed_pairs: list[tuple[str, str]] = []

    for old_name, new_name in LEGACY_TABLE_RENAMES.items():
        if old_name not in tables or new_name in tables:
            continue
        conn._conn.execute(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"')
        renamed_pairs.append((old_name, new_name))

    if renamed_pairs:
        conn.commit()
        renamed = ", ".join(f"{old}->{new}" for old, new in renamed_pairs)
        logger.info(f"Migrated legacy SQLite tables in place: {renamed}")


def _ensure_schema_compatibility(conn, logger) -> None:
    tables = _list_tables(conn)
    changed = False

    for table_name, columns in REQUIRED_COLUMNS.items():
        if table_name not in tables:
            continue

        existing_columns = _list_columns(conn, table_name)
        for column_name, column_spec in columns.items():
            if column_name in existing_columns:
                continue
            conn._conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {column_spec}')
            changed = True
            logger.info(f"Added missing column {table_name}.{column_name}")

    if changed:
        conn.commit()


def init_database():
    """
    Initialize the local SQLite database, preserving existing desktop data.
    """
    if not is_sqlite_available():
        raise RuntimeError("Cannot connect to SQLite database.")

    from app.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("SQLite connection verified")
    init_sql = _load_init_sql()

    with get_db_connection() as conn:
        _migrate_legacy_tables(conn, logger)
        conn._conn.executescript(init_sql)
        _ensure_schema_compatibility(conn, logger)
        conn.commit()
        logger.info("SQLite database schema initialized successfully")


def close_db_connection():
    pass


__all__ = [
    "get_db_connection",
    "get_db_connection_sync",
    "close_db_connection",
    "init_database",
    "close_db",
    "get_db_type",
    "execute_sql",
]
