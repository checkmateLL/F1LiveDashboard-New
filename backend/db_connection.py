import sqlite3
import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from contextlib import contextmanager

from backend.error_handling import DatabaseError, ResourceNotFoundError, ValidationError, handle_exception

logger = logging.getLogger(__name__)

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
            self.conn = sqlite3.connect(self.db_path)
            
            # Enable row factory for named column access
            self.conn.row_factory = sqlite3.Row
            
            # Create custom converter for IDs to ensure they're integers
            sqlite3.register_converter("ID", lambda v: int(v.decode()))
            
            logger.info(f"Connected to SQLite database: {self.db_path}")
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
    
    def get_session(self, session_id: Union[int, str]) -> Dict[str, Any]:
        """Get session by ID with proper type conversion"""
        try:
            session_id_int = int(session_id)
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, name, date, session_type, total_laps, event_id
                FROM sessions WHERE id = ?
            """, (session_id_int,))
            row = cursor.fetchone()
            
            if not row:
                raise ResourceNotFoundError(
                    resource_type="Session",
                    identifier=session_id
                )
                
            return dict(row)
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid session ID format: {session_id}. Error: {str(e)}")
        except ResourceNotFoundError:
            # Re-raise resource not found errors
            raise
        except sqlite3.Error as e:
            raise DatabaseError(f"Database error in get_session: {str(e)}")
        except Exception as e:
            error = handle_exception("get_session", e)
            raise error
    
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
    
    def get_lap_times(self, session_id: Union[int, str], driver_id: Optional[Union[int, str]] = None) -> pd.DataFrame:
        """Get lap times with proper ID conversion"""
        try:
            session_id_int = int(session_id)
            driver_id_int = int(driver_id) if driver_id is not None else None
            
            # Build the query
            query = """
                SELECT l.lap_number, l.lap_time, l.sector1_time, l.sector2_time, l.sector3_time,
                       l.compound, l.tyre_life, l.is_personal_best, l.stint, l.track_status,
                       l.deleted, l.deleted_reason, l.position,
                       d.full_name as driver_name, d.abbreviation, d.driver_number,
                       t.name as team_name, t.team_color
                FROM laps l
                JOIN drivers d ON l.driver_id = d.id
                JOIN teams t ON d.team_id = t.id
                WHERE l.session_id = ?
            """
            
            params = [session_id_int]
            
            if driver_id_int is not None:
                query += " AND l.driver_id = ?"
                params.append(driver_id_int)
            
            query += " ORDER BY l.lap_number, l.position"
            
            # Return as DataFrame for easier manipulation
            df = pd.read_sql_query(query, self.conn, params=params)
            return df
        
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid ID format: {str(e)}")
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            raise DatabaseError(f"Database error in get_lap_times: {str(e)}")
        except Exception as e:
            error = handle_exception("get_lap_times", e)
            raise error
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """
        Execute a custom SQL query with automatic ID conversion.
        Returns a pandas DataFrame for consistency and easier manipulation.
        """
        try:
            # Convert any ID parameters to integers if they are strings
            if params and isinstance(params, tuple):
                processed_params = []
                for param in params:
                    if isinstance(param, str) and param.isdigit():
                        processed_params.append(int(param))
                    else:
                        processed_params.append(param)
                params = tuple(processed_params)
            
            # Execute query and return as DataFrame
            df = pd.read_sql_query(query, self.conn, params=params)
            return df
                
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            raise DatabaseError(f"Database error in execute_query: {str(e)}")
        except Exception as e:
            error = handle_exception("execute_query", e)
            raise error

# Helper function to initialize the database handler
def get_db_handler():
    """Returns an instance of the DatabaseConnectionHandler"""
    return DatabaseConnectionHandler()