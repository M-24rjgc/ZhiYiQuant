"""
Database Connection Utility - SQLite

Provides unified interface for SQLite database operations.

Usage:
    from app.utils.db import get_db_connection
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        conn.commit()
"""

# Re-export from SQLite module
from app.utils.db_sqlite import (
    get_sqlite_connection as get_db_connection,
    get_sqlite_connection_sync as get_db_connection_sync,
    is_sqlite_available,
    close_pool as close_db,
    execute_sql
)


def get_db_type() -> str:
    """Get database type (sqlite)"""
    return 'sqlite'


def is_postgres() -> bool:
    """Check if using PostgreSQL (False)"""
    return False


def init_database():
    """
    Initialize database connection.
    Schema is created via migrations/init.sql if needed.
    """
    if is_sqlite_available():
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("SQLite connection verified")
        
        # Initialize schema if db is empty
        _init_schema()
    else:
        raise RuntimeError("Cannot connect to SQLite database.")

def _init_schema():
    """Run init.sql to initialize database schema if not already initialized"""
    from app.utils.logger import get_logger
    import os
    
    logger = get_logger(__name__)
    
    try:
        # Check if users table exists to determine if schema is initialized
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qd_users'")
            if cursor.fetchone():
                return # Already initialized
            
            # Read init.sql
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            init_sql_path = os.path.join(base_dir, 'migrations', 'init.sql')
            
            if not os.path.exists(init_sql_path):
                logger.warning(f"init.sql not found at {init_sql_path}")
                return
                
            with open(init_sql_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
                
            # Execute script
            # SQLite execute() only runs one statement, we need executescript() from raw cursor
            # But we can access the underlying sqlite3 connection via _conn
            conn._conn.executescript(sql_script)
            conn.commit()
            logger.info("SQLite database schema initialized successfully from init.sql")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database schema: {e}")

# Legacy alias
def close_db_connection():
    """Legacy alias for close_db"""
    pass


__all__ = [
    'get_db_connection',
    'get_db_connection_sync',
    'close_db_connection',
    'init_database',
    'close_db',
    'get_db_type',
    'is_postgres',
    'execute_sql'
]
