import sqlite3
import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from contextlib import contextmanager

from backend.database import get_db_connection
from backend.error_handling import DatabaseError, ResourceNotFoundError, ValidationError, handle_exception

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DatabaseConnectionHandler:
    """
    Wrapper for SQLite database connections that handles ID type conversion
    and provides a consistent interface for database operations.
    """
    
    def __init__(self, db_path="f1_data_full_2025.db"):
        """Initialize with database path"""
        self.db_path = db_path
        self.conn = None
    
    def __enter__(self):
        """Context manager entry - opens connection"""
        try:
            logger.info(f"Attempting to connect to database at: {self.db_path}")
            
            # Check if file exists
            import os
            if not os.path.exists(self.db_path):
                logger.error(f"Database file does not exist: {self.db_path}")
                raise DatabaseError(f"Database file not found: {self.db_path}")
                
            self.conn = sqlite3.connect(self.db_path)
            
            # Enable row factory for named column access
            self.conn.row_factory = sqlite3.Row
            
            # Create custom converter for IDs to ensure they're integers
            sqlite3.register_converter("ID", lambda v: int(v.decode()))
            
            logger.info(f"Successfully connected to SQLite database: {self.db_path}")
            return self
        except sqlite3.Error as e:
            error_msg = f"Error connecting to database: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("Database connection closed")
    
    def get_event(self, event_id: Union[int, str]) -> Dict[str, Any]:
        """Get event by ID with proper type conversion"""
        try:
            event_id_int = int(event_id)
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, round_number, country, location, official_event_name,
                       event_name, event_date, event_format, year
                FROM events WHERE id = ?
            """, (event_id_int,))
            row = cursor.fetchone()
            
            if not row:
                raise ResourceNotFoundError(
                    resource_type="Event",
                    identifier=event_id
                )
                
            return dict(row)
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid event ID format: {event_id}. Error: {str(e)}")
        except ResourceNotFoundError:
            # Re-raise resource not found errors
            raise
        except sqlite3.Error as e:
            raise DatabaseError(f"Database error in get_event: {str(e)}")
        except Exception as e:
            error = handle_exception("get_event", e)
            raise error
    
    def get_session(session_id: int):
        """
        Retrieves a session from the database.

        :param session_id: ID of the session
        :return: Session data as a dictionary
        """
        query = """
            SELECT id, name, date, session_type, total_laps, event_id
            FROM sessions
            WHERE id = ?
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (session_id,))
                session = cursor.fetchone()
                if session is None:
                    return None
                return dict(session)
        except sqlite3.Error as e:
            logger.error(f"Database error while retrieving session {session_id}: {e}")
            raise DatabaseError("Error retrieving session data")
    
    def get_sessions_for_event(self, event_id: Union[int, str]) -> List[Dict[str, Any]]:
        """Get all sessions for an event with proper ID conversion"""
        try:
            event_id_int = int(event_id)
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, name, date, session_type, total_laps, event_id
                FROM sessions WHERE event_id = ?
                ORDER BY date
            """, (event_id_int,))
            
            sessions = [dict(row) for row in cursor.fetchall()]
            
            if not sessions:
                logger.info(f"No sessions found for event ID {event_id}")
                
            return sessions
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid event ID format: {event_id}. Error: {str(e)}")
        except sqlite3.Error as e:
            raise DatabaseError(f"Database error in get_sessions_for_event: {str(e)}")
        except Exception as e:
            error = handle_exception("get_sessions_for_event", e)
            raise error
    
    def get_lap_times(session_id: int):
        """
        Retrieves lap times for a given session.

        :param session_id: Session ID
        :return: List of lap times
        """
        query = """
            SELECT lap_number, lap_time, sector1_time, sector2_time, sector3_time,
                compound, tyre_life, is_personal_best, stint, track_status,
                deleted, deleted_reason, position
            FROM laps
            WHERE session_id = ?
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (session_id,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Database error retrieving lap times for session {session_id}: {e}")
            raise DatabaseError("Error retrieving lap time data")
    
    def execute_query(self, query, params=()):
        """
        Executes a given SQL query with optional parameters.
        
        :param query: SQL query string
        :param params: Tuple of query parameters (optional)
        :return: Query result as a list of dictionaries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            result = [dict(row) for row in cursor.fetchall()]
            return result
        except sqlite3.Error as e:
            error_msg = f"Database query execution error: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)

# Helper function to initialize the database handler
def get_db_handler():
    """Returns an instance of the DatabaseConnectionHandler"""
    return DatabaseConnectionHandler()