import sqlite3
import pandas as pd
import numpy as np

def get_session_data(conn, session_id):
    """
    Retrieves session data from the database ensuring proper session ID type conversion.
    
    Parameters:
    - conn: SQLite connection
    - session_id: The session ID (will be properly converted to integer)
    
    Returns:
    - Session data as a dictionary
    """
    try:
        # Convert session_id to integer if it's not already
        session_id_int = int(session_id)
        
        # Query the database with the properly converted ID
        query = """
            SELECT id, name, date, session_type, total_laps, event_id
            FROM sessions
            WHERE id = ?
        """
        
        # Use the parameter as a tuple
        df = pd.read_sql_query(query, conn, params=(session_id_int,))
        
        if df.empty:
            return None
        
        return df.iloc[0].to_dict()
    except (ValueError, TypeError) as e:
        # Handle conversion errors
        print(f"Error converting session_id: {e}")
        return None
    except Exception as e:
        print(f"Database error: {e}")
        return None

def get_lap_times_with_id_fix(conn, session_id, driver_id=None):
    """
    Retrieves lap times with proper ID conversion.
    
    Parameters:
    - conn: SQLite connection
    - session_id: The session ID (will be properly converted)
    - driver_id: Optional driver ID filter
    
    Returns:
    - DataFrame with lap times
    """
    try:
        # Convert IDs to integers
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
        
        # Execute the query
        df = pd.read_sql_query(query, conn, params=params)
        return df
    
    except (ValueError, TypeError) as e:
        print(f"Error converting IDs: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Database error: {e}")
        return pd.DataFrame()

def get_telemetry_with_id_fix(conn, session_id, driver_id, lap_number):
    """
    Retrieves telemetry data with proper ID conversion.
    
    Parameters:
    - conn: SQLite connection
    - session_id: The session ID
    - driver_id: The driver ID
    - lap_number: The lap number
    
    Returns:
    - DataFrame with telemetry data
    """
    try:
        # Convert IDs to integers
        session_id_int = int(session_id)
        driver_id_int = int(driver_id)
        lap_number_int = int(lap_number)
        
        query = """
            SELECT time, session_time, speed, rpm, gear, throttle, brake, drs,
                   x, y, z, d.full_name as driver_name, t.team_color
            FROM telemetry tel
            JOIN drivers d ON tel.driver_id = d.id
            JOIN teams t ON d.team_id = t.id
            WHERE tel.session_id = ? AND tel.driver_id = ? AND tel.lap_number = ?
            ORDER BY tel.time
        """
        
        # Execute the query with properly converted parameters
        df = pd.read_sql_query(query, conn, params=(session_id_int, driver_id_int, lap_number_int))
        return df
        
    except (ValueError, TypeError) as e:
        print(f"Error converting IDs: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Database error: {e}")
        return pd.DataFrame()

# Patch function for data_service.py to fix session ID type conversion
def patch_data_service():
    """
    Apply monkey patch to fix session ID conversion issues in the data service.
    This should be called at application startup.
    """
    from backend.data_service import F1DataService
    
    # Original method
    original_get_sessions = F1DataService.get_sessions
    
    # Patched method with proper ID conversion
    def patched_get_sessions(self, event_id):
        """Patched method to ensure event_id is properly converted to int"""
        try:
            event_id_int = int(event_id)
            return original_get_sessions(self, event_id_int)
        except (ValueError, TypeError):
            print(f"Error converting event_id: {event_id}")
            return []
    
    # Apply the patch
    F1DataService.get_sessions = patched_get_sessions
    
    # Patch other methods with similar issues
    # ... (additional patches as needed)
    
    print("Data service patched for ID type conversion")