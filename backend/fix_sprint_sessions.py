import os
import sys
import time
import argparse
import logging
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd
import fastf1
from tqdm import tqdm

###########################
#       Script usage
# python updated-sprint-fixer.py --list                      # List all sessions in the database
# python updated-sprint-fixer.py --year 2025                 # Fix all sprint sessions for 2025
# python updated-sprint-fixer.py --session-id 11             # Fix a specific session (ID 11)
# python updated-sprint-fixer.py --force-reload              # Fix all sprints with forced data reload
# python updated-sprint-fixer.py --verbose                   # Fix with verbose logging
# python updated-sprint-fixer.py --db-path "path/to/db.db"   # Use a different database path

# Common combinations:
# python updated-sprint-fixer.py --session-id 11 --force-reload
# python updated-sprint-fixer.py --year 2025 --force-reload --verbose

# Configure root logger first
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sprint_fix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = "D:/Dev/F1LiveDashboard/f1_data_full_2025.db"

# Setup FastF1 Cache
cache_dir = Path.home() / ".fastf1_cache"
cache_dir.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(cache_dir))

def setup_logging(verbose=False):
    """Set up logging with appropriate verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Reset logger level
    logger.setLevel(level)
    
    # Set FastF1 log level
    if verbose:
        fastf1.set_log_level(logging.DEBUG)
    else:
        fastf1.set_log_level(logging.INFO)
    
    logger.debug("Debug logging enabled")

def get_session_info(db_path: str, session_id: int = None, event_round: int = None, year: int = None, session_name: str = None) -> Dict:
    """Get session information from database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if session_id is not None:
        cursor.execute("""
            SELECT s.*, e.year, e.round_number, e.event_name
            FROM sessions s
            JOIN events e ON s.event_id = e.id
            WHERE s.id = ?
        """, (session_id,))
    elif all([event_round, year, session_name]):
        cursor.execute("""
            SELECT s.*, e.year, e.round_number, e.event_name
            FROM sessions s
            JOIN events e ON s.event_id = e.id
            WHERE e.year = ? AND e.round_number = ? AND s.name = ?
        """, (year, event_round, session_name))
    else:
        raise ValueError("Either session_id or (event_round, year, session_name) must be provided")
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return dict(row)

def get_all_sprint_sessions(db_path: str, year: int) -> List[Dict]:
    """Get all sprint sessions for a given year."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.*, e.year, e.round_number, e.event_name
        FROM sessions s
        JOIN events e ON s.event_id = e.id
        WHERE e.year = ? AND (s.session_type = 'sprint' OR s.session_type = 'sprint_qualifying' OR s.session_type = 'sprint_shootout')
        ORDER BY e.round_number, s.id
    """, (year,))
    
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return sessions

def delete_session_data(db_path: str, session_id: int) -> None:
    """Delete existing data for a session to allow clean reimport."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Delete from dependent tables
    for table in ['laps', 'results', 'weather', 'telemetry', 'messages']:
        try:
            cursor.execute(f"DELETE FROM {table} WHERE session_id = ?", (session_id,))
        except sqlite3.OperationalError:
            logger.warning(f"Table '{table}' doesn't exist, skipping")
    
    conn.commit()
    conn.close()
    logger.info(f"Deleted existing data for session ID {session_id}")

def get_driver_ids(conn: sqlite3.Connection, year: int) -> Dict[str, int]:
    """Get mapping of driver abbreviations to database IDs."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, abbreviation FROM drivers WHERE year = ?", (year,))
    
    driver_map = {}
    for row in cursor.fetchall():
        driver_map[row[1]] = row[0]
    
    return driver_map

def migrate_results(conn: sqlite3.Connection, session_obj, session_id: int, year: int, enable_position_fix=True) -> None:
    """Migrate results data for the session."""
    if not hasattr(session_obj, "results") or session_obj.results is None or len(session_obj.results) == 0:
        logger.warning(f"No results data available for session ID {session_id}")
        return
    
    logger.info(f"Migrating results for {len(session_obj.results)} drivers")
    
    cursor = conn.cursor()
    driver_map = get_driver_ids(conn, year)
    
    # Calculate positions from laps if needed
    position_map = {}
    if enable_position_fix and hasattr(session_obj, "laps") and not session_obj.laps.empty:
        try:
            logger.info("Calculating positions from lap data...")
            fastest_laps = session_obj.laps.groupby('Driver')['LapTime'].min().reset_index()
            fastest_laps = fastest_laps.sort_values('LapTime')
            
            for i, (_, row) in enumerate(fastest_laps.iterrows(), 1):
                position_map[row['Driver']] = i
                
            logger.info(f"Calculated positions for {len(position_map)} drivers")
        except Exception as e:
            logger.error(f"Error calculating positions: {e}")
    
    for _, row in session_obj.results.iterrows():
        abbr = row["Abbreviation"]
        driver_id = driver_map.get(abbr)
        
        if not driver_id:
            logger.warning(f"No driver found with abbreviation {abbr}")
            continue
        
        cursor.execute("""
            SELECT id FROM results WHERE session_id = ? AND driver_id = ?
        """, (session_id, driver_id))
        
        record = cursor.fetchone()
        if record:
            # Update existing record if positions are missing
            if enable_position_fix:
                position = int(row["Position"]) if pd.notna(row["Position"]) else (position_map.get(abbr) if abbr in position_map else None)
                if position:
                    cursor.execute("""
                        UPDATE results SET position = ? WHERE id = ?
                    """, (position, record[0]))
                    conn.commit()
            continue
        
        try:
            # Use calculated position if available and original is NULL
            position = int(row["Position"]) if pd.notna(row["Position"]) else (position_map.get(abbr) if abbr in position_map else None)
            
            # Insert results record
            cursor.execute("""
                INSERT INTO results (
                    session_id, driver_id, position, classified_position,
                    grid_position, q1_time, q2_time, q3_time, race_time,
                    status, points
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                driver_id,
                position,
                row["ClassifiedPosition"] if pd.notna(row["ClassifiedPosition"]) else None,
                int(row["GridPosition"]) if pd.notna(row["GridPosition"]) else None,
                str(row["Q1"]) if pd.notna(row["Q1"]) else None,
                str(row["Q2"]) if pd.notna(row["Q2"]) else None,
                str(row["Q3"]) if pd.notna(row["Q3"]) else None,
                str(row["Time"]) if pd.notna(row["Time"]) else None,
                row["Status"] if pd.notna(row["Status"]) else None,
                float(row["Points"]) if pd.notna(row["Points"]) else None
            ))
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error inserting results for driver {abbr}: {e}")
            continue

def migrate_laps(conn: sqlite3.Connection, session_obj, session_id: int, year: int) -> None:
    """Migrate lap data for the session."""
    if not hasattr(session_obj, "laps") or session_obj.laps is None or len(session_obj.laps) == 0:
        logger.warning(f"No lap data available for session ID {session_id}")
        return
    
    logger.info(f"Migrating {len(session_obj.laps)} laps")
    
    cursor = conn.cursor()
    driver_map = get_driver_ids(conn, year)
    
    # Process each lap
    for _, lap in tqdm(session_obj.laps.iterrows(), total=len(session_obj.laps), desc="Migrating laps"):
        abbr = lap["Driver"]
        driver_id = driver_map.get(abbr)
        
        if not driver_id:
            logger.warning(f"No driver found with abbreviation {abbr}")
            continue
        
        lap_number = int(lap["LapNumber"]) if pd.notna(lap["LapNumber"]) else None
        if not lap_number:
            continue
        
        # Check if this lap already exists
        cursor.execute("""
            SELECT id FROM laps WHERE session_id = ? AND driver_id = ? AND lap_number = ?
        """, (session_id, driver_id, lap_number))
        
        if cursor.fetchone():
            continue
        
        try:
            # Insert lap data
            cursor.execute("""
                INSERT INTO laps (
                    session_id, driver_id, lap_time, lap_number, stint,
                    pit_out_time, pit_in_time, sector1_time, sector2_time, sector3_time,
                    sector1_session_time, sector2_session_time, sector3_session_time,
                    speed_i1, speed_i2, speed_fl, speed_st, is_personal_best,
                    compound, tyre_life, fresh_tyre, lap_start_time, lap_start_date,
                    track_status, position, deleted, deleted_reason,
                    fast_f1_generated, is_accurate, time, session_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                driver_id,
                str(lap["LapTime"]) if pd.notna(lap["LapTime"]) else None,
                lap_number,
                int(lap["Stint"]) if pd.notna(lap["Stint"]) else None,
                str(lap["PitOutTime"]) if pd.notna(lap["PitOutTime"]) else None,
                str(lap["PitInTime"]) if pd.notna(lap["PitInTime"]) else None,
                str(lap["Sector1Time"]) if pd.notna(lap["Sector1Time"]) else None,
                str(lap["Sector2Time"]) if pd.notna(lap["Sector2Time"]) else None,
                str(lap["Sector3Time"]) if pd.notna(lap["Sector3Time"]) else None,
                str(lap["Sector1SessionTime"]) if pd.notna(lap["Sector1SessionTime"]) else None,
                str(lap["Sector2SessionTime"]) if pd.notna(lap["Sector2SessionTime"]) else None,
                str(lap["Sector3SessionTime"]) if pd.notna(lap["Sector3SessionTime"]) else None,
                float(lap["SpeedI1"]) if pd.notna(lap["SpeedI1"]) else None,
                float(lap["SpeedI2"]) if pd.notna(lap["SpeedI2"]) else None,
                float(lap["SpeedFL"]) if pd.notna(lap["SpeedFL"]) else None,
                float(lap["SpeedST"]) if pd.notna(lap["SpeedST"]) else None,
                1 if (pd.notna(lap["IsPersonalBest"]) and lap["IsPersonalBest"]) else 0,
                lap["Compound"] if pd.notna(lap["Compound"]) else None,
                float(lap["TyreLife"]) if pd.notna(lap["TyreLife"]) else None,
                1 if (pd.notna(lap["FreshTyre"]) and lap["FreshTyre"]) else 0,
                str(lap["LapStartTime"]) if pd.notna(lap["LapStartTime"]) else None,
                lap["LapStartDate"].isoformat() if pd.notna(lap["LapStartDate"]) else None,
                lap["TrackStatus"] if pd.notna(lap["TrackStatus"]) else None,
                int(lap["Position"]) if pd.notna(lap["Position"]) else None,
                1 if (pd.notna(lap["Deleted"]) and lap["Deleted"]) else 0,
                lap["DeletedReason"] if pd.notna(lap["DeletedReason"]) else None,
                1 if (pd.notna(lap["FastF1Generated"]) and lap["FastF1Generated"]) else 0,
                1 if (pd.notna(lap["IsAccurate"]) and lap["IsAccurate"]) else 0,
                str(lap["Time"]) if pd.notna(lap["Time"]) else None,
                str(lap["SessionTime"]) if "SessionTime" in lap.index and pd.notna(lap["SessionTime"]) else None
            ))
            conn.commit()
            
            # Process telemetry for this lap
            try:
                tel = lap.get_telemetry()
                if tel is not None and not tel.empty:
                    migrate_lap_telemetry(conn, tel, session_id, driver_id, lap_number, year)
            except Exception as e:
                logger.error(f"Error processing telemetry for lap {lap_number}, driver {abbr}: {e}")
            
        except Exception as e:
            logger.error(f"Error inserting lap {lap_number} for driver {abbr}: {e}")
            continue

def migrate_lap_telemetry(conn: sqlite3.Connection, telemetry_df: pd.DataFrame, session_id: int, driver_id: int, lap_number: int, year: int):
    """Migrate telemetry data for a specific lap."""
    if telemetry_df is None or telemetry_df.empty:
        return
    
    cursor = conn.cursor()
    
    # Batch insert with a reasonable batch size to avoid memory issues
    batch_size = 1000
    telemetry_batches = []
    current_batch = []
    
    for _, tel_row in telemetry_df.iterrows():
        time_str = str(tel_row["Time"]) if pd.notna(tel_row["Time"]) else None
        
        tel_tuple = (
            driver_id,
            int(lap_number),
            session_id,
            time_str,
            str(tel_row["SessionTime"]) if "SessionTime" in tel_row.index and pd.notna(tel_row["SessionTime"]) else None,
            tel_row["Date"].isoformat() if pd.notna(tel_row["Date"]) else None,
            float(tel_row["Speed"]) if pd.notna(tel_row["Speed"]) else None,
            float(tel_row["RPM"]) if pd.notna(tel_row["RPM"]) else None,
            int(tel_row["nGear"]) if pd.notna(tel_row["nGear"]) else None,
            float(tel_row["Throttle"]) if pd.notna(tel_row["Throttle"]) else None,
            1 if (pd.notna(tel_row["Brake"]) and tel_row["Brake"]) else 0,
            int(tel_row["DRS"]) if pd.notna(tel_row["DRS"]) else None,
            float(tel_row["X"]) if pd.notna(tel_row["X"]) else None,
            float(tel_row["Y"]) if pd.notna(tel_row["Y"]) else None,
            float(tel_row["Z"]) if pd.notna(tel_row["Z"]) else None,
            tel_row["Source"] if pd.notna(tel_row["Source"]) else None,
            year
        )
        
        current_batch.append(tel_tuple)
        
        if len(current_batch) >= batch_size:
            telemetry_batches.append(current_batch)
            current_batch = []
    
    if current_batch:
        telemetry_batches.append(current_batch)
    
    # Insert telemetry in batches
    total_inserted = 0
    for batch in telemetry_batches:
        try:
            cursor.executemany("""
                INSERT OR IGNORE INTO telemetry (
                    driver_id, lap_number, session_id, time, session_time,
                    date, speed, rpm, gear, throttle, brake, drs, x, y, z, source, year
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            total_inserted += len(batch)
        except Exception as e:
            logger.error(f"Error inserting telemetry batch: {e}")
    
    return total_inserted

def migrate_weather(conn: sqlite3.Connection, session_obj, session_id: int) -> None:
    """Migrate weather data for the session."""
    if not hasattr(session_obj, "weather_data") or session_obj.weather_data is None or session_obj.weather_data.empty:
        logger.warning(f"No weather data available for session ID {session_id}")
        return
    
    logger.info(f"Migrating {len(session_obj.weather_data)} weather data points")
    
    cursor = conn.cursor()
    weather_batch = []
    
    for _, wrow in session_obj.weather_data.iterrows():
        time_str = str(wrow["Time"]) if pd.notna(wrow["Time"]) else None
        
        weather_data = (
            session_id,
            time_str,
            float(wrow["AirTemp"]) if pd.notna(wrow["AirTemp"]) else None,
            float(wrow["Humidity"]) if pd.notna(wrow["Humidity"]) else None,
            float(wrow["Pressure"]) if pd.notna(wrow["Pressure"]) else None,
            1 if (pd.notna(wrow["Rainfall"]) and wrow["Rainfall"]) else 0,
            float(wrow["TrackTemp"]) if pd.notna(wrow["TrackTemp"]) else None,
            int(wrow["WindDirection"]) if pd.notna(wrow["WindDirection"]) else None,
            float(wrow["WindSpeed"]) if pd.notna(wrow["WindSpeed"]) else None
        )
        weather_batch.append(weather_data)
    
    # Execute batch insert
    if weather_batch:
        cursor.executemany("""
            INSERT OR IGNORE INTO weather (
                session_id, time, air_temp, humidity, pressure, rainfall,
                track_temp, wind_direction, wind_speed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, weather_batch)
        conn.commit()

def migrate_messages(conn: sqlite3.Connection, session_obj, session_id: int) -> None:
    """Migrate race control messages for the session."""
    if not hasattr(session_obj, "race_control_messages") or session_obj.race_control_messages is None or session_obj.race_control_messages.empty:
        logger.warning(f"No race control messages available for session ID {session_id}")
        return
    
    logger.info(f"Migrating {len(session_obj.race_control_messages)} race control messages")
    
    # Check if messages table exists, create it if needed
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                message TEXT,
                message_time TEXT,
                category TEXT,
                flag TEXT,
                driver_number TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"Error creating messages table: {e}")
        return
    
    # Process messages
    message_batch = []
    for _, msg in session_obj.race_control_messages.iterrows():
        try:
            message_data = (
                session_id,
                msg["Message"] if pd.notna(msg["Message"]) else None,
                str(msg["Time"]) if pd.notna(msg["Time"]) else None,
                msg["Category"] if pd.notna(msg["Category"]) else None,
                msg["Flag"] if pd.notna(msg["Flag"]) else None,
                str(msg["DriverNumber"]) if pd.notna(msg["DriverNumber"]) else None
            )
            message_batch.append(message_data)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    # Execute batch insert
    if message_batch:
        cursor.executemany("""
            INSERT INTO messages (
                session_id, message, message_time, category, flag, driver_number
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, message_batch)
        conn.commit()

def try_alternative_session_name(year: int, round_number: int, session_name: str):
    """Try alternative session names in case the official name varies."""
    alternatives = {
        "Sprint Qualifying": ["Sprint Shootout", "Sprint Qualifying", "Sprint Shootout Qualifying", "SQ"],
        "Sprint": ["Sprint Race", "Sprint", "F1 Sprint"],
        "Qualifying": ["Qualifying", "Q"]
    }
    
    base_name = None
    for key, options in alternatives.items():
        if session_name in options:
            base_name = key
            break
    
    if not base_name:
        return None
        
    # Try all alternatives for this session type
    for alt_name in alternatives[base_name]:
        if alt_name == session_name:
            continue
            
        logger.info(f"Trying alternative session name: {alt_name}")
        try:
            session = fastf1.get_session(year, round_number, alt_name)
            return session
        except Exception as e:
            logger.debug(f"Alternative {alt_name} failed: {e}")
    
    return None

def fix_session(session_id: int, db_path: str = DB_PATH, force_reload: bool = False, 
                verbose: bool = False) -> None:
    """Fix data for a specific session."""
    # Set up logging
    setup_logging(verbose)
    
    # Get session info
    session_info = get_session_info(db_path, session_id)
    if not session_info:
        logger.error(f"No session found with ID {session_id}")
        return
    
    logger.info(f"Fixing session: {session_info['name']} - {session_info['event_name']} (Round {session_info['round_number']})")
    
    # Delete existing data if force reload
    if force_reload:
        delete_session_data(db_path, session_id)
    
    try:
        # Get FastF1 session
        logger.info(f"Loading data from FastF1...")
        session = None
        
        try:
            session = fastf1.get_session(
                session_info['year'], 
                session_info['round_number'], 
                session_info['name']
            )
        except Exception as e:
            logger.warning(f"Error loading session with name '{session_info['name']}': {e}")
            
            # Try alternative session names
            session = try_alternative_session_name(
                session_info['year'],
                session_info['round_number'],
                session_info['name']
            )
            
            if not session:
                logger.error("Could not find session with any alternative names")
                return
        
        # Load session data
        logger.info(f"Loading detailed session data...")
        session.load(laps=True, telemetry=True, weather=True, messages=True)
        
        # Connect to database for migrations
        conn = sqlite3.connect(db_path)
        
        try:
            # Migrate data
            migrate_results(conn, session, session_id, session_info['year'], True)
            migrate_laps(conn, session, session_id, session_info['year'])
            migrate_weather(conn, session, session_id)
            migrate_messages(conn, session, session_id)
            
            logger.info(f"Successfully fixed session ID {session_id}")
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error loading session from FastF1: {e}")
        import traceback
        logger.error(traceback.format_exc())

def fix_all_sprints(year: int, db_path: str = DB_PATH, force_reload: bool = False,
                    verbose: bool = False) -> None:
    """Fix all sprint sessions for a given year."""
    # Set up logging
    setup_logging(verbose)
    
    sprint_sessions = get_all_sprint_sessions(db_path, year)
    
    if not sprint_sessions:
        logger.info(f"No sprint sessions found for {year}")
        return
    
    logger.info(f"Found {len(sprint_sessions)} sprint sessions for {year}")
    
    for session in sprint_sessions:
        logger.info("-" * 50)
        fix_session(session['id'], db_path, force_reload, verbose)

def list_sessions(db_path: str = DB_PATH, year: int = None) -> None:
    """List all sessions in the database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if messages table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='messages'
    """)
    has_messages_table = cursor.fetchone() is not None
    
    query = """
        SELECT s.id, s.name, s.session_type, e.year, e.round_number, e.event_name,
            (SELECT COUNT(*) FROM laps WHERE session_id = s.id) as lap_count,
            (SELECT COUNT(*) FROM results WHERE session_id = s.id) as result_count,
            (SELECT COUNT(*) FROM weather WHERE session_id = s.id) as weather_count,
            (SELECT COUNT(*) FROM telemetry WHERE session_id = s.id) as telemetry_count
    """
    
    if has_messages_table:
        query += ", (SELECT COUNT(*) FROM messages WHERE session_id = s.id) as message_count"
    else:
        query += ", 0 as message_count"
    
    query += """
        FROM sessions s
        JOIN events e ON s.event_id = e.id
    """
    
    params = []
    if year:
        query += " WHERE e.year = ?"
        params.append(year)
        
    query += " ORDER BY e.year, e.round_number, s.id"
    
    cursor.execute(query, params)
    
    print(f"{'ID':>4} | {'Year':>4} | {'Round':>5} | {'Event':<25} | {'Session':<20} | {'Type':<15} | {'Laps':>6} | {'Results':>7} | {'Weather':>7} | {'Telemetry':>9} | {'Messages':>8}")
    print("-" * 130)
    
    for row in cursor.fetchall():
        print(f"{row['id']:4} | {row['year']:4} | {row['round_number']:5} | {row['event_name'][:25]:<25} | {row['name'][:20]:<20} | {row['session_type']:<15} | {row['lap_count']:6} | {row['result_count']:7} | {row['weather_count']:7} | {row['telemetry_count']:9} | {row['message_count']:8}")
    
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Fix F1 sprint session data")
    parser.add_argument("--session-id", type=int, help="Specific session ID to fix")
    parser.add_argument("--year", type=int, default=2025, help="Year to fix sprint sessions for")
    parser.add_argument("--db-path", default=DB_PATH, help="Path to SQLite database")
    parser.add_argument("--force-reload", action="store_true", help="Force delete and reload all data")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")
    parser.add_argument("--list", action="store_true", help="List sessions in database")
    
    args = parser.parse_args()
    
    if args.list:
        list_sessions(args.db_path, args.year)
    elif args.session_id:
        fix_session(args.session_id, args.db_path, args.force_reload, args.verbose)
    else:
        fix_all_sprints(args.year, args.db_path, args.force_reload, args.verbose)

if __name__ == "__main__":
    main()