import sqlite3
import logging
from typing import Optional
import os
from contextlib import contextmanager

from backend.error_handling import DatabaseError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Database file path
DB_PATH = os.getenv("SQLITE_DB_PATH", "f1_data.db")

# Connection pooling (singleton instance)
class SQLiteConnectionPool:
    """Singleton connection pool to reuse database connections."""
    _instance = None

    def __new__(cls, db_path=DB_PATH):
        if cls._instance is None:
            cls._instance = super(SQLiteConnectionPool, cls).__new__(cls)
            cls._instance.db_path = db_path
            cls._instance._connection = None
        return cls._instance

    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper error handling."""
        if self._connection is None:
            try:
                self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
                self._connection.row_factory = sqlite3.Row
                logger.info(f"Connected to SQLite database: {self.db_path}")
            except sqlite3.Error as e:
                raise DatabaseError(f"Database connection error: {str(e)}")
        return self._connection

    def close_connection(self):
        """Closes the database connection if it exists."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed.")

# Context manager for managing connections
@contextmanager
def get_db_connection():
    """Context manager for database connections using the connection pool."""
    pool = SQLiteConnectionPool()
    conn = pool.get_connection()
    try:
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise DatabaseError(f"Unexpected database error: {str(e)}")
    finally:
        pool.close_connection()