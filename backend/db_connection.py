import sqlite3
import pandas as pd
import logging
import os
from typing import Dict, Any, List, Optional, Tuple, Union
from contextlib import contextmanager

from backend.database import get_db_connection
from backend.error_handling import DatabaseError, ResourceNotFoundError, ValidationError, handle_exception

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DatabaseConnectionHandler:
    """Wrapper for SQLite database connections with improved error handling and logging."""

    def __init__(self, db_path="f1_data_full_2025.db"):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        try:
            logger.debug(f"Attempting connection to database: {self.db_path}")

            if not os.path.exists(self.db_path):
                logger.error(f"Database file not found: {self.db_path}")
                raise DatabaseError(f"Database file not found: {self.db_path}")

            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row

            logger.debug(f"Successfully connected to database: {self.db_path}")
            return self
        except sqlite3.Error as e:
            logger.exception(f"Error connecting to database: {e}")
            raise DatabaseError(f"Error connecting to database: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("Database connection closed")
    
    def execute_query(self, query: str, params: Tuple = ()) -> pd.DataFrame:
        logger.debug(f"Executing SQL Query: {query} with params {params}")
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                return pd.DataFrame()  # ✅ Ensure an empty DataFrame instead of None

            columns = [desc[0] for desc in cursor.description]
            return pd.DataFrame(rows, columns=columns)  # ✅ Convert list of dicts into DataFrame
        except sqlite3.Error as e:
            logger.exception(f"Database query execution error: {e}")
            raise DatabaseError(f"Database query execution error: {e}")
    
    def get_event(self, event_id: Union[int, str]) -> Dict[str, Any]:
        try:
            event_id_int = int(event_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid event ID format: {event_id}")
            raise ValidationError(f"Invalid event ID format: {event_id}")

        query = """
            SELECT id, round_number, country, location, official_event_name,
                   event_name, event_date, event_format, year
            FROM events
            WHERE id = ?
        """
        result = self.execute_query(query, (event_id_int,))
        if not result:
            logger.warning(f"Event not found: ID {event_id_int}")
            raise ResourceNotFoundError("Event", event_id_int)
        return result[0]
    
    def get_session(self, session_id: Union[int, str]) -> Dict[str, Any]:
        try:
            session_id_int = int(session_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid session ID format: {session_id}")
            raise ValidationError(f"Invalid session ID format: {session_id}")

        query = """
            SELECT id, name, date, session_type, total_laps, event_id
            FROM sessions
            WHERE id = ?
        """
        result = self.execute_query(query, (session_id_int,))
        if not result:
            logger.warning(f"Session not found: ID {session_id_int}")
            raise ResourceNotFoundError("Session", session_id_int)
        return result[0]

    def get_sessions_for_event(self, event_id: Union[int, str]) -> List[Dict[str, Any]]:
        try:
            event_id_int = int(event_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid event ID format: {event_id}")
            raise ValidationError(f"Invalid event ID format: {event_id}")

        query = """
            SELECT id, name, date, session_type, total_laps, event_id
            FROM sessions
            WHERE event_id = ?
            ORDER BY date
        """
        result = self.execute_query(query, (event_id_int,))
        if not result:
            logger.warning(f"No sessions found for event ID {event_id_int}")
        return result

    def get_lap_times(self, session_id: Union[int, str]) -> List[Dict[str, Any]]:
        try:
            session_id_int = int(session_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid session ID format: {session_id}")
            raise ValidationError(f"Invalid session ID format: {session_id}")

        query = """
            SELECT lap_number, lap_time, sector1_time, sector2_time, sector3_time,
                   compound, tyre_life, is_personal_best, stint, track_status,
                   deleted, deleted_reason, position
            FROM laps
            WHERE session_id = ?
        """
        result = self.execute_query(query, (session_id_int,))
        if not result:
            logger.warning(f"No lap times found for session ID {session_id_int}")
        return result

  

# Helper function to initialize the database handler
def get_db_handler():
    """Returns an instance of the DatabaseConnectionHandler"""
    return DatabaseConnectionHandler()