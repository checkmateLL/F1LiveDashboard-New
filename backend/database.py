import sqlite3
import logging
from typing import Optional
import os
from contextlib import contextmanager

from backend.error_handling import DatabaseError

logger = logging.getLogger(__name__)

def get_connection(db_path: str = "f1_data_full_2025.db") -> sqlite3.Connection:
    """
    Get a connection to the SQLite database with proper error handling.
    
    Parameters:
    - db_path: Path to the SQLite database file
    
    Returns:
    - SQLite connection object
    
    Raises:
    - DatabaseError: If connection cannot be established
    """
    try:
        if not os.path.exists(db_path):
            raise DatabaseError(f"Database file not found: {db_path}")
            
        connection = sqlite3.connect(db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        logger.info(f"Connected to SQLite database: {db_path}")
        return connection
    except sqlite3.Error as e:
        error_msg = f"Error connecting to database: {str(e)}"
        logger.error(error_msg)
        raise DatabaseError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error connecting to database: {str(e)}"
        logger.error(error_msg)
        raise DatabaseError(error_msg)

@contextmanager
def get_db_connection(db_path: str = "f1_data_full_2025.db"):
    """
    Context manager for database connections to ensure proper cleanup.
    
    Parameters:
    - db_path: Path to the SQLite database file
    
    Yields:
    - SQLite connection object
    
    Raises:
    - DatabaseError: If connection cannot be established
    """
    conn = None
    try:
        conn = get_connection(db_path)
        yield conn
    except DatabaseError:
        # Re-raise database errors
        raise
    except Exception as e:
        error_msg = f"Unexpected error in database connection: {str(e)}"
        logger.error(error_msg)
        raise DatabaseError(error_msg)
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")