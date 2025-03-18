import sqlite3
import pandas as pd

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
        self.conn = sqlite3.connect(self.db_path)
        
        # Enable row factory for named column access
        self.conn.row_factory = sqlite3.Row
        
        # Create custom converter for IDs to ensure they're integers
        sqlite3.register_converter("ID", lambda v: int(v.decode()))
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_event(self, event_id):
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
            return dict(row) if row else None
        except (ValueError, TypeError) as e:
            print(f"Error converting event_id: {e}")
            return None
    
    def get_session(self, session_id):
        """Get session by ID with proper type conversion"""
        try:
            session_id_int = int(session_id)
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, name, date, session_type, total_laps, event_id
                FROM sessions WHERE id = ?
            """, (session_id_int,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except (ValueError, TypeError) as e:
            print(f"Error converting session_id: {e}")
            return None
    
    def get_sessions_for_event(self, event_id):
        """Get all sessions for an event with proper ID conversion"""
        try:
            event_id_int = int(event_id)
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, name, date, session_type, total_laps, event_id
                FROM sessions WHERE event_id = ?
                ORDER BY date
            """, (event_id_int,))
            return [dict(row) for row in cursor.fetchall()]
        except (ValueError, TypeError) as e:
            print(f"Error converting event_id: {e}")
            return []
    
    def get_lap_times(self, session_id, driver_id=None):
        """Get lap times with proper ID conversion"""
        try:
            session_id_int = int(session_id)
            
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
            
            if driver_id is not None:
                driver_id_int = int(driver_id)
                query += " AND l.driver_id = ?"
                params.append(driver_id_int)
            
            query += " ORDER BY l.lap_number, l.position"
            
            # Return as DataFrame for easier manipulation
            df = pd.read_sql_query(query, self.conn, params=params)
            return df
        
        except (ValueError, TypeError) as e:
            print(f"Error converting IDs: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Database error: {e}")
            return pd.DataFrame()
    
    def execute_query(self, query, params=None):
        """
        Execute a custom SQL query with automatic ID conversion.
        Returns a pandas DataFrame for consistency and easier manipulation.
        """
        try:
            # Convert any ID parameters to integers
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
                
        except Exception as e:
            print(f"Query execution error: {e}")
            return pd.DataFrame()  # Return empty DataFrame instead of empty list

# Helper function to initialize the database handler
def get_db_handler():
    """Returns an instance of the DatabaseConnectionHandler"""
    return DatabaseConnectionHandler()