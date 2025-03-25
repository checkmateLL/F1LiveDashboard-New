import os
import sys
import time
import argparse
import logging
import sqlite3
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
from tqdm import tqdm

import fastf1
from fastf1.core import Session

# Handle dotenv conditionally
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, that's okay

# -----------------------------------
# Configuration - Set default paths
# -----------------------------------
# Try to get configuration from config.py, but use defaults if not available
try:
    from config import FASTF1_CACHE_DIR, SQLITE_DB_PATH
    print(f"Using configuration from config.py")
except ImportError:
    # Default paths if config module is not found
    FASTF1_CACHE_DIR = os.path.expanduser("~/.fastf1_cache")
    SQLITE_DB_PATH = os.path.join(os.getcwd(), "f1_data_full_2025.db")
    print(f"Config module not found, using defaults:")

print(f"Database path: {SQLITE_DB_PATH}")
print(f"Cache directory: {FASTF1_CACHE_DIR}")

# -----------------------------------
# Setup Logging (for migration only)
# -----------------------------------
migration_logger = logging.getLogger("migration")
migration_logger.setLevel(logging.DEBUG)

log_file_path = "migration.log"
fh = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
migration_logger.addHandler(fh)

# Also add console handler for better visibility
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
migration_logger.addHandler(ch)

# -----------------------------------
# Setup FastF1 Cache
# -----------------------------------
if not os.path.exists(FASTF1_CACHE_DIR):
    os.makedirs(FASTF1_CACHE_DIR)
    migration_logger.info(f"Created FastF1 cache directory: {FASTF1_CACHE_DIR}")

try:
    fastf1.Cache.enable_cache(FASTF1_CACHE_DIR)
    migration_logger.info(f"FastF1 cache enabled at: {FASTF1_CACHE_DIR}")
except Exception as e:
    migration_logger.warning(f"Failed to enable FastF1 cache: {e}")
    migration_logger.info(f"Setting FastF1 cache via environment variable")
    os.environ["FASTF1_CACHE_DIR"] = str(FASTF1_CACHE_DIR)
    
try:
    fastf1.set_log_level(logging.WARNING)
except Exception as e:
    migration_logger.warning(f"Failed to set FastF1 log level: {e}")

# -----------------------------------
# SQLite Client
# -----------------------------------
class SQLiteF1Client:
    def __init__(self, db_path=SQLITE_DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        import sqlite3
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            migration_logger.info(f"Connected to SQLite database: {self.db_path}")
            return True
        except Exception as e:
            migration_logger.error(f"Failed to connect to database: {e}")
            return False

    def close(self):
        if self.conn:
            self.conn.close()
            migration_logger.info("Closed SQLite connection")

    def commit(self):
        if self.conn:
            self.conn.commit()

    def create_tables(self):
        if not self.conn:
            if not self.connect():
                return False
                
        try:
            # Events table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER,
                    round_number INTEGER,
                    country TEXT,
                    location TEXT,
                    official_event_name TEXT,
                    event_name TEXT,
                    event_date TEXT,
                    event_format TEXT,
                    f1_api_support INTEGER,
                    UNIQUE(year, round_number)
                )
            ''')

            # Sessions table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    name TEXT,
                    date TEXT,
                    session_type TEXT,
                    total_laps INTEGER,
                    session_start_time TEXT,
                    t0_date TEXT,
                    UNIQUE(event_id, name),
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )
            ''')

            # Teams table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    team_id TEXT,
                    team_color TEXT,
                    year INTEGER,
                    UNIQUE(name, year)
                )
            ''')

            # Drivers table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_number TEXT,
                    broadcast_name TEXT,
                    abbreviation TEXT,
                    driver_id TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    full_name TEXT,
                    headshot_url TEXT,
                    country_code TEXT,
                    team_id INTEGER,
                    year INTEGER,
                    UNIQUE(abbreviation, year),
                    FOREIGN KEY(team_id) REFERENCES teams(id)
                )
            ''')

            # Results table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    driver_id INTEGER,
                    position INTEGER,
                    classified_position TEXT,
                    grid_position INTEGER,
                    q1_time TEXT,
                    q2_time TEXT,
                    q3_time TEXT,
                    race_time TEXT,
                    status TEXT,
                    points REAL,
                    UNIQUE(session_id, driver_id),
                    FOREIGN KEY(session_id) REFERENCES sessions(id),
                    FOREIGN KEY(driver_id) REFERENCES drivers(id)
                )
            ''')

            # Laps table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS laps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    driver_id INTEGER,
                    lap_time TEXT,
                    lap_number INTEGER,
                    stint INTEGER,
                    pit_out_time TEXT,
                    pit_in_time TEXT,
                    sector1_time TEXT,
                    sector2_time TEXT,
                    sector3_time TEXT,
                    sector1_session_time TEXT,
                    sector2_session_time TEXT,
                    sector3_session_time TEXT,
                    speed_i1 REAL,
                    speed_i2 REAL,
                    speed_fl REAL,
                    speed_st REAL,
                    is_personal_best INTEGER,
                    compound TEXT,
                    tyre_life REAL,
                    fresh_tyre INTEGER,
                    lap_start_time TEXT,
                    lap_start_date TEXT,
                    track_status TEXT,
                    position INTEGER,
                    deleted INTEGER,
                    deleted_reason TEXT,
                    fast_f1_generated INTEGER,
                    is_accurate INTEGER,
                    time TEXT,
                    session_time TEXT,
                    UNIQUE(session_id, driver_id, lap_number),
                    FOREIGN KEY(session_id) REFERENCES sessions(id),
                    FOREIGN KEY(driver_id) REFERENCES drivers(id)
                )
            ''')

            # Telemetry table with unique constraint to prevent duplicates
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER,
                    lap_number INTEGER,
                    session_id INTEGER,
                    time TEXT,
                    session_time TEXT,
                    date TEXT,
                    speed REAL,
                    rpm REAL,
                    gear INTEGER,
                    throttle REAL,
                    brake INTEGER,
                    drs INTEGER,
                    x REAL,
                    y REAL,
                    z REAL,
                    source TEXT,
                    year INTEGER,
                    FOREIGN KEY(session_id) REFERENCES sessions(id),
                    FOREIGN KEY(driver_id) REFERENCES drivers(id),
                    UNIQUE(session_id, driver_id, lap_number, time)
                )
            ''')

            # Weather table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS weather (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    time TEXT,
                    air_temp REAL,
                    humidity REAL,
                    pressure REAL,
                    rainfall INTEGER,
                    track_temp REAL,
                    wind_direction INTEGER,
                    wind_speed REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            ''')
            
            # Messages table (for race control messages)
            self.cursor.execute('''
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
            ''')
            
            # Circuits table if needed
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS circuits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    circuit_name TEXT,
                    circuit_reference TEXT,
                    location TEXT,
                    country TEXT,
                    lat REAL,
                    lng REAL,
                    alt REAL,
                    url TEXT,
                    UNIQUE(circuit_reference)
                )
            ''')
            
            self.commit()
            migration_logger.info("Created/verified all tables successfully.")
            return True
        except Exception as e:
            migration_logger.error(f"Error creating tables: {e}")
            migration_logger.error(traceback.format_exc())
            return False

    def insert_event(self, event_data: dict) -> int:
        self.cursor.execute("""
            SELECT id FROM events
            WHERE year = ? AND round_number = ?
        """, (event_data['year'], event_data['round_number']))
        row = self.cursor.fetchone()
        if row:
            return row['id']
        self.cursor.execute("""
            INSERT INTO events (
                year, round_number, country, location, official_event_name,
                event_name, event_date, event_format, f1_api_support
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_data["year"],
            event_data["round_number"],
            event_data["country"],
            event_data["location"],
            event_data["official_event_name"],
            event_data["event_name"],
            event_data["event_date"],
            event_data["event_format"],
            1 if event_data["f1_api_support"] else 0
        ))
        self.commit()
        return self.cursor.lastrowid

    def insert_session(self, session_data: dict) -> int:
        self.cursor.execute("""
            SELECT id FROM sessions
            WHERE event_id = ? AND name = ?
        """, (session_data["event_id"], session_data["name"]))
        row = self.cursor.fetchone()
        if row:
            return row['id']
        
        # Add the missing fields to handle session data more completely
        self.cursor.execute("""
            INSERT INTO sessions (
                event_id, name, date, session_type,
                total_laps, session_start_time, t0_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_data["event_id"],
            session_data["name"],
            session_data["date"],
            session_data["session_type"],
            session_data.get("total_laps"),  # Handle optional fields
            session_data.get("session_start_time"),
            session_data.get("t0_date")
        ))
        self.commit()
        return self.cursor.lastrowid
    
    def delete_session_data(self, session_id: int) -> None:
        """Delete existing data for a session to allow clean reimport."""
        # Delete from dependent tables
        for table in ['laps', 'results', 'weather', 'telemetry', 'messages']:
            try:
                self.cursor.execute(f"DELETE FROM {table} WHERE session_id = ?", (session_id,))
            except Exception as e:
                migration_logger.warning(f"Error deleting from '{table}': {e}")
        
        self.commit()
        migration_logger.info(f"Deleted existing data for session ID {session_id}")

#############################
# Helper Functions
#############################

def _session_type(session_name: str) -> str:
    """Determine session type from name, with improved sprint detection."""
    if "Practice" in session_name:
        return "practice"
    elif "Sprint" in session_name or "sprint" in session_name:
        if "Shootout" in session_name or "shootout" in session_name:
            return "sprint_shootout"
        elif "Qualifying" in session_name or "qualifying" in session_name or "SQ" in session_name:
            return "sprint_qualifying"
        else:
            return "sprint"
    elif "Qualifying" in session_name or session_name == "Q":
        return "qualifying"
    elif "Race" in session_name or session_name == "R":
        return "race"
    return "unknown"

def try_alternative_session_name(year: int, round_number: int, session_name: str) -> Optional[Session]:
    """Try alternative session names in case the official name varies."""
    alternatives = {
        "Sprint Qualifying": ["Sprint Shootout", "Sprint Qualifying", "Sprint Shootout Qualifying", "SQ"],
        "Sprint": ["Sprint Race", "Sprint", "F1 Sprint"],
        "Qualifying": ["Qualifying", "Q"],
        "Race": ["Race", "R"]
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
            
        migration_logger.info(f"Trying alternative session name: {alt_name}")
        try:
            session = fastf1.get_session(year, round_number, alt_name)
            return session
        except Exception as e:
            migration_logger.debug(f"Alternative {alt_name} failed: {e}")
    
    return None

#############################
# Migrate Functions
#############################

def migrate_events(db: SQLiteF1Client, year: int) -> pd.DataFrame:
    migration_logger.info(f"Fetching event schedule for {year}")
    try:
        schedule = fastf1.get_event_schedule(year)
        migration_logger.info(f"Found {len(schedule)} events for {year}")
        
        for idx, ev in schedule.iterrows():
            try:
                event_data = {
                    "year": year,
                    "round_number": int(ev["RoundNumber"]),
                    "country": ev["Country"],
                    "location": ev["Location"],
                    "official_event_name": ev["OfficialEventName"],
                    "event_name": ev["EventName"],
                    "event_date": ev["EventDate"].isoformat() if pd.notna(ev["EventDate"]) else None,
                    "event_format": ev["EventFormat"],
                    "f1_api_support": bool(ev["F1ApiSupport"])
                }
                db.insert_event(event_data)
                migration_logger.info(f"Added/updated event: {event_data['event_name']} (Round {event_data['round_number']})")
            except Exception as e:
                migration_logger.error(f"Error processing event {ev.get('EventName', 'unknown')}: {e}")
                continue
        return schedule
    except Exception as e:
        migration_logger.error(f"Error fetching event schedule: {e}")
        migration_logger.error(traceback.format_exc())
        return pd.DataFrame()  # Return empty dataframe

def migrate_sessions(db: SQLiteF1Client, schedule: pd.DataFrame, year: int):
    if schedule.empty:
        migration_logger.warning(f"No schedule data for {year}, cannot migrate sessions")
        return
        
    for idx, ev in schedule.iterrows():
        try:
            event_id = db.cursor.execute("""
                SELECT id FROM events WHERE year = ? AND round_number = ?
            """, (year, int(ev["RoundNumber"]))).fetchone()
            if not event_id:
                migration_logger.warning(f"Event not found for round {ev['RoundNumber']}")
                continue
            event_id = event_id["id"]
            
            # Find all sessions for this event
            for i in range(1, 6):
                s_name = ev.get(f"Session{i}")
                if pd.isna(s_name):
                    continue
                s_date_utc = ev.get(f"Session{i}DateUtc")
                s_data = {
                    "event_id": event_id,
                    "name": s_name,
                    "date": s_date_utc.isoformat() if pd.notna(s_date_utc) else None,
                    "session_type": _session_type(s_name),
                    "total_laps": None,  # Will be updated later if available
                    "session_start_time": None,  # Will be updated later if available
                    "t0_date": None  # Will be updated later if available
                }
                session_id = db.insert_session(s_data)
                migration_logger.info(f"Added/updated session: {s_name} (ID: {session_id}, Type: {s_data['session_type']})")
        except Exception as e:
            migration_logger.error(f"Error processing sessions for event {ev.get('EventName', 'unknown')}: {e}")
            continue

def migrate_teams_and_drivers(db: SQLiteF1Client, session_obj, year: int):
    if not hasattr(session_obj, "results") or session_obj.results is None or len(session_obj.results) == 0:
        migration_logger.warning(f"No results data for session: {session_obj.name}")
        return
        
    for _, row in session_obj.results.iterrows():
        try:
            team_name = row["TeamName"]
            db.cursor.execute("""
                SELECT id FROM teams WHERE name = ? AND year = ?
            """, (team_name, year))
            existing_team = db.cursor.fetchone()
            if existing_team:
                team_id = existing_team["id"]
            else:
                db.cursor.execute("""
                    INSERT INTO teams (name, team_id, team_color, year)
                    VALUES (?, ?, ?, ?)
                """, (
                    team_name,
                    row["TeamId"],
                    row["TeamColor"],
                    year
                ))
                db.commit()
                team_id = db.cursor.lastrowid
            abbr = row["Abbreviation"]
            db.cursor.execute("""
                SELECT id FROM drivers WHERE abbreviation = ? AND year = ?
            """, (abbr, year))
            existing_driver = db.cursor.fetchone()
            if not existing_driver:
                db.cursor.execute("""
                    INSERT INTO drivers (
                        driver_number, broadcast_name, abbreviation, driver_id,
                        first_name, last_name, full_name, headshot_url, country_code,
                        team_id, year
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row["DriverNumber"]),
                    row["BroadcastName"],
                    abbr,
                    row["DriverId"],
                    row["FirstName"],
                    row["LastName"],
                    row["FullName"],
                    row["HeadshotUrl"],
                    row["CountryCode"],
                    team_id,
                    year
                ))
                db.commit()
        except Exception as e:
            migration_logger.error(f"Error processing driver {row.get('Abbreviation', 'unknown')}: {e}")
            continue

def migrate_results(db: SQLiteF1Client, session_obj, session_id: int, year: int, enable_position_fix=True):
    """Migrate results data with position fix option for sprint sessions."""
    if not hasattr(session_obj, "results") or session_obj.results is None or len(session_obj.results) == 0:
        migration_logger.warning(f"No results data for session ID: {session_id}")
        return
    
    # Get driver mapping
    drivers_map = {}
    for _, row in session_obj.results.iterrows():
        abbr = row["Abbreviation"]
        db.cursor.execute("""
            SELECT id FROM drivers WHERE abbreviation = ? AND year = ?
        """, (abbr, year))
        found = db.cursor.fetchone()
        if found:
            drivers_map[abbr] = found["id"]
    
    # Calculate positions from laps if needed
    position_map = {}
    if enable_position_fix and hasattr(session_obj, "laps") and not session_obj.laps.empty:
        try:
            migration_logger.info("Calculating positions from lap data...")
            fastest_laps = session_obj.laps.groupby('Driver')['LapTime'].min().reset_index()
            fastest_laps = fastest_laps.sort_values('LapTime')
            
            for i, (_, row) in enumerate(fastest_laps.iterrows(), 1):
                position_map[row['Driver']] = i
                
            migration_logger.info(f"Calculated positions for {len(position_map)} drivers")
        except Exception as e:
            migration_logger.error(f"Error calculating positions: {e}")
    
    # Process results
    for _, row in session_obj.results.iterrows():
        try:
            abbr = row["Abbreviation"]
            driver_id = drivers_map.get(abbr)
            if not driver_id:
                migration_logger.warning(f"No driver found for abbreviation: {abbr}")
                continue
                
            db.cursor.execute("""
                SELECT id FROM results WHERE session_id = ? AND driver_id = ?
            """, (session_id, driver_id))
            record = db.cursor.fetchone()
            
            # Use calculated position if available and original is missing
            position = int(row["Position"]) if pd.notna(row["Position"]) else (position_map.get(abbr) if abbr in position_map else None)
            
            if record:
                # Update existing record if positions are missing or need fixing
                if enable_position_fix and position:
                    db.cursor.execute("""
                        UPDATE results SET position = ? WHERE id = ?
                    """, (position, record["id"]))
                    db.commit()
                continue
            
            db.cursor.execute("""
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
            db.commit()
            migration_logger.info(f"Added result for driver {abbr}")
        except Exception as e:
            migration_logger.error(f"Error inserting results for driver {row.get('Abbreviation', 'unknown')}: {e}")
            continue

def migrate_laps(db: SQLiteF1Client, session_obj, session_id: int, year: int):
    """Migrate lap data for the session."""
    if not hasattr(session_obj, "laps") or session_obj.laps is None or len(session_obj.laps) == 0:
        migration_logger.warning(f"No lap data for session ID: {session_id}")
        return
    
    migration_logger.info(f"Processing {len(session_obj.laps)} laps...")
    
    # Create a mapping of drivers for this session
    drivers_map = {}
    if hasattr(session_obj, "results") and session_obj.results is not None:
        for _, row in session_obj.results.iterrows():
            abbr = row["Abbreviation"]
            db.cursor.execute("""
                SELECT id FROM drivers WHERE abbreviation = ? AND year = ?
            """, (abbr, year))
            found = db.cursor.fetchone()
            if found:
                drivers_map[abbr] = found["id"]
    
    # If we couldn't get drivers from results, try to get from drivers table directly
    if not drivers_map:
        db.cursor.execute("""
            SELECT id, abbreviation FROM drivers WHERE year = ?
        """, (year,))
        results = db.cursor.fetchall()
        for row in results:
            drivers_map[row["abbreviation"]] = row["id"]
    
    laps_df = session_obj.laps
    lap_count = 0
    telemetry_count = 0
    
    for _, lap in tqdm(laps_df.iterrows(), total=len(laps_df), desc="Migrating laps"):
        try:
            abbr = lap["Driver"]
            driver_id = drivers_map.get(abbr)
            if not driver_id:
                migration_logger.warning(f"No driver found for abbreviation: {abbr}")
                continue
                
            lap_number = int(lap["LapNumber"]) if pd.notna(lap["LapNumber"]) else None
            if not lap_number:
                continue
                
            db.cursor.execute("""
                SELECT id FROM laps WHERE session_id = ? AND driver_id = ? AND lap_number = ?
            """, (session_id, driver_id, lap_number))
            if db.cursor.fetchone():
                # Check if telemetry exists for this lap
                db.cursor.execute("""
                    SELECT COUNT(*) FROM telemetry 
                    WHERE session_id = ? AND driver_id = ? AND lap_number = ?
                """, (session_id, driver_id, lap_number))
                
                tel_count = db.cursor.fetchone()[0]
                if tel_count == 0:
                    # Lap exists but missing telemetry, get telemetry only
                    try:
                        tel = lap.get_telemetry()
                        if tel is not None and not tel.empty:
                            points = migrate_lap_telemetry(db, tel, session_id, driver_id, lap_number, year)
                            telemetry_count += points
                    except Exception as e:
                        migration_logger.error(f"Telemetry error lap {lap_number}, driver {abbr}: {e}")
                continue

            lap_data = {
                "session_id": session_id,
                "driver_id": driver_id,
                "lap_time": str(lap["LapTime"]) if pd.notna(lap["LapTime"]) else None,
                "lap_number": lap_number,
                "stint": int(lap["Stint"]) if pd.notna(lap["Stint"]) else None,
                "pit_out_time": str(lap["PitOutTime"]) if pd.notna(lap["PitOutTime"]) else None,
                "pit_in_time": str(lap["PitInTime"]) if pd.notna(lap["PitInTime"]) else None,
                "sector1_time": str(lap["Sector1Time"]) if pd.notna(lap["Sector1Time"]) else None,
                "sector2_time": str(lap["Sector2Time"]) if pd.notna(lap["Sector2Time"]) else None,
                "sector3_time": str(lap["Sector3Time"]) if pd.notna(lap["Sector3Time"]) else None,
                "sector1_session_time": str(lap["Sector1SessionTime"]) if pd.notna(lap["Sector1SessionTime"]) else None,
                "sector2_session_time": str(lap["Sector2SessionTime"]) if pd.notna(lap["Sector2SessionTime"]) else None,
                "sector3_session_time": str(lap["Sector3SessionTime"]) if pd.notna(lap["Sector3SessionTime"]) else None,
                "speed_i1": float(lap["SpeedI1"]) if pd.notna(lap["SpeedI1"]) else None,
                "speed_i2": float(lap["SpeedI2"]) if pd.notna(lap["SpeedI2"]) else None,
                "speed_fl": float(lap["SpeedFL"]) if pd.notna(lap["SpeedFL"]) else None,
                "speed_st": float(lap["SpeedST"]) if pd.notna(lap["SpeedST"]) else None,
                "is_personal_best": 1 if (pd.notna(lap["IsPersonalBest"]) and lap["IsPersonalBest"]) else 0,
                "compound": lap["Compound"] if pd.notna(lap["Compound"]) else None,
                "tyre_life": float(lap["TyreLife"]) if pd.notna(lap["TyreLife"]) else None,
                "fresh_tyre": 1 if (pd.notna(lap["FreshTyre"]) and lap["FreshTyre"]) else 0,
                "lap_start_time": str(lap["LapStartTime"]) if pd.notna(lap["LapStartTime"]) else None,
                "lap_start_date": lap["LapStartDate"].isoformat() if pd.notna(lap["LapStartDate"]) else None,
                "track_status": lap["TrackStatus"] if pd.notna(lap["TrackStatus"]) else None,
                "position": int(lap["Position"]) if pd.notna(lap["Position"]) else None,
                "deleted": 1 if (pd.notna(lap["Deleted"]) and lap["Deleted"]) else 0,
                "deleted_reason": lap["DeletedReason"] if pd.notna(lap["DeletedReason"]) else None,
                "fast_f1_generated": 1 if (pd.notna(lap["FastF1Generated"]) and lap["FastF1Generated"]) else 0,
                "is_accurate": 1 if (pd.notna(lap["IsAccurate"]) and lap["IsAccurate"]) else 0,
                "time": str(lap["Time"]) if pd.notna(lap["Time"]) else None,
                "session_time": str(lap["SessionTime"]) if "SessionTime" in lap.index and pd.notna(lap["SessionTime"]) else None
            }

            keys = ",".join(lap_data.keys())
            placeholders = ",".join(["?"] * len(lap_data))
            values = list(lap_data.values())
            
            try:
                db.cursor.execute(f"""
                    INSERT INTO laps ({keys}) VALUES ({placeholders})
                """, values)
                db.commit()
                lap_count += 1
                
                # Always process telemetry for new laps
                try:
                    tel = lap.get_telemetry()
                    if tel is not None and not tel.empty:
                        points = migrate_lap_telemetry(db, tel, session_id, driver_id, lap_number, year)
                        telemetry_count += points
                except Exception as e:
                    migration_logger.error(f"Telemetry error lap {lap_number}, driver {abbr}: {e}")
                
            except Exception as e:
                migration_logger.error(f"Error inserting lap {lap_number} for driver {abbr}: {e}")
                continue
                
        except Exception as e:
            migration_logger.error(f"Error processing lap for driver {lap.get('Driver', 'unknown')}: {e}")
            continue
    
    migration_logger.info(f"Successfully migrated {lap_count} laps and {telemetry_count} telemetry points for session ID {session_id}")

def migrate_lap_telemetry(db: SQLiteF1Client, telemetry_df: pd.DataFrame, session_id: int, driver_id: int, lap_number: int, year: int):
    """Migrate telemetry data for a specific lap with batch processing."""
    if telemetry_df is None or telemetry_df.empty:
        return
    
    migration_logger.info(f"Processing {len(telemetry_df)} telemetry points for lap {lap_number}")
    
    # Batch insert with a reasonable batch size to avoid memory issues
    batch_size = 1000
    telemetry_batches = []
    current_batch = []
    
    for _, tel_row in telemetry_df.iterrows():
        try:
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
        except Exception as e:
            migration_logger.error(f"Error processing telemetry point: {e}")
    
    if current_batch:
        telemetry_batches.append(current_batch)
    
    # Insert telemetry in batches
    total_inserted = 0
    for batch_idx, batch in enumerate(telemetry_batches, 1):
        try:
            db.cursor.executemany("""
                INSERT OR IGNORE INTO telemetry (
                    driver_id, lap_number, session_id, time, session_time,
                    date, speed, rpm, gear, throttle, brake, drs, x, y, z, source, year
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            db.commit()
            total_inserted += len(batch)
            migration_logger.info(f"Inserted batch {batch_idx}/{len(telemetry_batches)} ({len(batch)} points)")
        except Exception as e:
            migration_logger.error(f"Error inserting telemetry batch {batch_idx}: {e}")
    
    migration_logger.info(f"Successfully inserted {total_inserted}/{len(telemetry_df)} telemetry points for lap {lap_number}")
    return total_inserted

def migrate_weather(db: SQLiteF1Client, session_obj, session_id: int):
    """Migrate weather data for the session."""
    if not hasattr(session_obj, "weather_data") or session_obj.weather_data is None or session_obj.weather_data.empty:
        migration_logger.warning(f"No weather data for session ID: {session_id}")
        return
    
    migration_logger.info(f"Migrating weather data for session ID: {session_id}")
    wdf = session_obj.weather_data
    weather_batch = []
    
    for _, wrow in wdf.iterrows():
        try:
            time_str = str(wrow["Time"]) if pd.notna(wrow["Time"]) else None
            
            # Skip check for existing records for batch processing
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
        except Exception as e:
            migration_logger.error(f"Error processing weather data point: {e}")
    
    # Execute batch insert
    if weather_batch:
        try:
            db.cursor.executemany("""
                INSERT OR IGNORE INTO weather (
                    session_id, time, air_temp, humidity, pressure, rainfall,
                    track_temp, wind_direction, wind_speed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, weather_batch)
            db.commit()
            migration_logger.info(f"Migrated {len(weather_batch)} weather data points")
        except Exception as e:
            migration_logger.error(f"Error inserting weather batch: {e}")

def migrate_messages(db: SQLiteF1Client, session_obj, session_id: int):
    """Migrate race control messages for the session."""
    if not hasattr(session_obj, "race_control_messages") or session_obj.race_control_messages is None or session_obj.race_control_messages.empty:
        migration_logger.warning(f"No race control messages available for session ID {session_id}")
        return
    
    migration_logger.info(f"Migrating {len(session_obj.race_control_messages)} race control messages")
    
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
            migration_logger.error(f"Error processing message: {e}")
    
    # Execute batch insert
    if message_batch:
        try:
            db.cursor.executemany("""
                INSERT INTO messages (
                    session_id, message, message_time, category, flag, driver_number
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, message_batch)
            db.commit()
            migration_logger.info(f"Migrated {len(message_batch)} race control messages")
        except Exception as e:
            migration_logger.error(f"Error inserting message batch: {e}")

def get_sprint_sessions(db: SQLiteF1Client, year: int):
    """Get all sprint sessions for a given year."""
    db.cursor.execute("""
        SELECT s.id, s.name, s.session_type, e.year, e.round_number, e.event_name
        FROM sessions s
        JOIN events e ON s.event_id = e.id
        WHERE e.year = ? AND (
            s.session_type LIKE '%sprint%' OR 
            s.name LIKE '%Sprint%' OR 
            s.name LIKE '%sprint%'
        )
        ORDER BY e.round_number, s.id
    """, (year,))
    
    sessions = [dict(row) for row in db.cursor.fetchall()]
    
    if not sessions:
        migration_logger.info(f"No sprint sessions found for year {year}")
    else:
        migration_logger.info(f"Found {len(sessions)} sprint sessions for year {year}")
        
    return sessions

def process_session(session_info, db: SQLiteF1Client, year: int, force_reload: bool = False) -> bool:
    """Process a single session with proper error handling."""
    session_id = session_info['id']
    session_name = session_info['name']
    event_name = session_info['event_name'] 
    round_number = session_info['round_number']
    
    migration_logger.info(f"Processing session: {session_name} - {event_name} (Round {round_number})")
    
    # Delete existing data if force reload
    if force_reload:
        db.delete_session_data(session_id)
    
    # Check if session already has data
    db.cursor.execute("SELECT COUNT(*) FROM laps WHERE session_id = ?", (session_id,))
    lap_count = db.cursor.fetchone()[0]
    
    db.cursor.execute("SELECT COUNT(*) FROM results WHERE session_id = ?", (session_id,))
    result_count = db.cursor.fetchone()[0]
    
    # Check telemetry count
    db.cursor.execute("SELECT COUNT(*) FROM telemetry WHERE session_id = ?", (session_id,))
    telemetry_count = db.cursor.fetchone()[0]
    
    # Skip if already has data and not forcing reload
    if not force_reload and (lap_count > 0 or result_count > 0):
        migration_logger.info(f"Session already has data (Laps: {lap_count}, Results: {result_count}, Telemetry: {telemetry_count}). Use --force-reload to reimport.")
        return True
    
    try:
        # Get FastF1 session
        session_obj = None
        
        try:
            # Try with the original name
            session_obj = fastf1.get_session(year, round_number, session_name)
        except Exception as e:
            migration_logger.warning(f"Error loading session with name '{session_name}': {e}")
            
            # Try with alternative names
            session_obj = try_alternative_session_name(year, round_number, session_name)
            
            if not session_obj:
                migration_logger.error(f"Could not find session with any alternative names")
                return False
        
        # Load session data with telemetry
        migration_logger.info(f"Loading detailed data for session (including telemetry)...")
        session_obj.load(laps=True, telemetry=True, weather=True, messages=True)
        
        # Run migrations
        migrate_teams_and_drivers(db, session_obj, year)
        
        # Enable position fix for sprint sessions
        is_sprint_session = "sprint" in (session_info.get('session_type') or "").lower()
        migrate_results(db, session_obj, session_id, year, enable_position_fix=is_sprint_session)
        
        migrate_laps(db, session_obj, session_id, year)
        migrate_weather(db, session_obj, session_id)
        migrate_messages(db, session_obj, session_id)
        
        migration_logger.info(f"Successfully processed session ID {session_id}")
        return True
        
    except Exception as e:
        migration_logger.error(f"Error processing session: {e}")
        migration_logger.error(traceback.format_exc())
        return False
    
def fix_missing_telemetry(db: SQLiteF1Client, year: int):
    """Fix missing telemetry for sessions that already have lap data."""
    # Get all sessions for the year
    db.cursor.execute("""
        SELECT s.id, s.name, s.session_type, e.year, e.round_number, e.event_name
        FROM sessions s
        JOIN events e ON s.event_id = e.id
        WHERE e.year = ?
        ORDER BY e.round_number, s.id
    """, (year,))
    
    sessions = [dict(row) for row in db.cursor.fetchall()]
    
    if not sessions:
        print(f"No sessions found for year {year}")
        return
    
    print(f"\nChecking telemetry for {len(sessions)} sessions:")
    
    for session in sessions:
        session_id = session['id']
        
        # Check lap count
        db.cursor.execute("SELECT COUNT(*) FROM laps WHERE session_id = ?", (session_id,))
        lap_count = db.cursor.fetchone()[0]
        
        # Check telemetry count
        db.cursor.execute("SELECT COUNT(*) FROM telemetry WHERE session_id = ?", (session_id,))
        telemetry_count = db.cursor.fetchone()[0]
        
        if lap_count > 0 and telemetry_count == 0:
            print(f"\nSession {session['name']} (Round {session['round_number']}) has {lap_count} laps but no telemetry")
            
            try:
                # Load session from FastF1
                session_obj = fastf1.get_session(session['year'], session['round_number'], session['name'])
                if not session_obj:
                    session_obj = try_alternative_session_name(session['year'], session['round_number'], session['name'])
                
                if session_obj:
                    print(f"  Loading telemetry data...")
                    session_obj.load(laps=True, telemetry=True, weather=False, messages=False)
                    
                    # Process telemetry
                    migrate_laps(db, session_obj, session_id, year)
                else:
                    print(f"  Failed to load session from FastF1")
            except Exception as e:
                print(f"  Error: {e}")
        else:
            print(f"Session {session['name']} (Round {session['round_number']}) has {telemetry_count} telemetry points")
    
def fix_sprint_sessions(db: SQLiteF1Client, year: int, force_reload: bool = False) -> None:
    """Fix all sprint sessions for a given year."""
    # Find all sprint sessions
    sprint_sessions = get_sprint_sessions(db, year)
    
    if not sprint_sessions:
        print(f"No sprint sessions found for {year}")
        return
    
    print(f"\nProcessing {len(sprint_sessions)} sprint sessions:")
    
    success_count = 0
    
    for session in sprint_sessions:
        print(f"\n{'-' * 60}")
        print(f"Processing: {session['name']} (Round {session['round_number']} - {session['event_name']})")
        
        if process_session(session, db, year, force_reload):
            success_count += 1
            print(f"✓ Successfully processed session")
        else:
            print(f"✗ Failed to process session")
    
    print(f"\n{'-' * 60}")
    print(f"Completed: {success_count}/{len(sprint_sessions)} sessions processed successfully")

def migrate_session_details(db: SQLiteF1Client, schedule, year: int, force_reload=False):
    """Migrate all session details with improved sprint session handling."""
    if schedule.empty:
        migration_logger.warning(f"No schedule data for {year}, cannot migrate sessions")
        return
        
    total_sessions = 0
    successful_sessions = 0
    
    # Count total sessions first
    for idx, ev in schedule.iterrows():
        for i in range(1, 6):
            s_name = ev.get(f"Session{i}")
            if pd.notna(s_name):
                total_sessions += 1
    
    print(f"\nMigrating {total_sessions} sessions for {year}...")
    
    for idx, ev in tqdm(schedule.iterrows(), total=len(schedule), desc="Events"):
        event_id = None
        try:
            # Get the event_id from the database
            db.cursor.execute("""
                SELECT id FROM events 
                WHERE year = ? AND round_number = ?
            """, (year, int(ev["RoundNumber"])))
            ev_row = db.cursor.fetchone()
            if ev_row:
                event_id = ev_row["id"]
            else:
                migration_logger.warning(f"Event not found in database: {ev['EventName']} (Round {ev['RoundNumber']})")
                continue
                
            # Get the list of sessions for this event
            sessions = []
            for i in range(1, 6):
                s_name = ev.get(f"Session{i}")
                if pd.notna(s_name):
                    sessions.append(s_name)
                    
            if not sessions:
                migration_logger.warning(f"No sessions found for event: {ev['EventName']}")
                continue
                
            # Process each session
            for session_name in sessions:
                try:
                    # Get the session info from the database
                    db.cursor.execute("""
                        SELECT s.id, s.name, s.session_type, e.year, e.round_number, e.event_name 
                        FROM sessions s 
                        JOIN events e ON s.event_id = e.id
                        WHERE s.event_id = ? AND s.name = ?
                    """, (event_id, session_name))
                    session_row = db.cursor.fetchone()
                    
                    if session_row:
                        session_info = dict(session_row)
                        if process_session(session_info, db, year, force_reload):
                            successful_sessions += 1
                    else:
                        migration_logger.warning(f"Session '{session_name}' not found in database for event {ev['EventName']}")
                        
                except Exception as e:
                    migration_logger.error(f"Error in session processing loop for '{session_name}': {e}")
                    migration_logger.error(traceback.format_exc())
            
        except Exception as e:
            migration_logger.error(f"Error processing event {ev['EventName'] if 'EventName' in ev else 'unknown'}: {e}")
            migration_logger.error(traceback.format_exc())
    
    print(f"\nMigration completed: {successful_sessions}/{total_sessions} sessions processed successfully")

def list_sessions(db: SQLiteF1Client, year: int = None) -> None:
    """List all sessions in the database."""
    try:
        # Check if the tables exist first
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        if not db.cursor.fetchone():
            print("Sessions table doesn't exist in the database yet.")
            return

        # Build query with proper error handling
        query = """
            SELECT s.id, s.name, s.session_type, e.year, e.round_number, e.event_name,
                (SELECT COUNT(*) FROM laps WHERE session_id = s.id) as lap_count,
                (SELECT COUNT(*) FROM results WHERE session_id = s.id) as result_count
        """
        
        # Check if weather table exists
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weather'")
        has_weather = db.cursor.fetchone() is not None
        if has_weather:
            query += ", (SELECT COUNT(*) FROM weather WHERE session_id = s.id) as weather_count"
        else:
            query += ", 0 as weather_count"
            
        # Check if telemetry table exists
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='telemetry'")
        has_telemetry = db.cursor.fetchone() is not None
        if has_telemetry:
            query += ", (SELECT COUNT(*) FROM telemetry WHERE session_id = s.id) as telemetry_count"
        else:
            query += ", 0 as telemetry_count"
            
        # Check if messages table exists
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        has_messages = db.cursor.fetchone() is not None
        if has_messages:
            query += ", (SELECT COUNT(*) FROM messages WHERE session_id = s.id) as message_count"
        else:
            query += ", 0 as message_count"
        
        # Complete the query
        query += """
            FROM sessions s
            JOIN events e ON s.event_id = e.id
        """
        
        # Add filter if year is provided
        params = []
        if year:
            query += " WHERE e.year = ?"
            params.append(year)
            
        query += " ORDER BY e.year, e.round_number, s.id"
        
        # Execute query
        db.cursor.execute(query, params)
        rows = db.cursor.fetchall()
        
        if not rows:
            print(f"No sessions found for year {year}")
            return
        
        # Print header
        print(f"{'ID':>4} | {'Year':>4} | {'Round':>5} | {'Event':<25} | {'Session':<20} | {'Type':<15} | {'Laps':>6} | {'Results':>7} | {'Weather':>7} | {'Telemetry':>9} | {'Messages':>8}")
        print("-" * 130)
        
        # Print rows
        for row in rows:
            print(f"{row['id']:4} | {row['year']:4} | {row['round_number']:5} | {row['event_name'][:25]:<25} | {row['name'][:20]:<20} | {row['session_type'] or 'unknown':<15} | {row['lap_count']:6} | {row['result_count']:7} | {row['weather_count']:7} | {row.get('telemetry_count', 0):9} | {row.get('message_count', 0):8}")
    
    except Exception as e:
        migration_logger.error(f"Error listing sessions: {e}")
        migration_logger.error(traceback.format_exc())
        print(f"Error listing sessions: {e}")

def list_sessions_by_event(db: SQLiteF1Client, year: int, event_name: str):
    """List sessions for a specific event."""
    try:
        # Build query with event filter
        query = """
            SELECT s.id, s.name, s.session_type, e.year, e.round_number, e.event_name,
                (SELECT COUNT(*) FROM laps WHERE session_id = s.id) as lap_count,
                (SELECT COUNT(*) FROM results WHERE session_id = s.id) as result_count,
                (SELECT COUNT(*) FROM weather WHERE session_id = s.id) as weather_count,
                (SELECT COUNT(*) FROM telemetry WHERE session_id = s.id) as telemetry_count,
                (SELECT COUNT(*) FROM messages WHERE session_id = s.id) as message_count
            FROM sessions s
            JOIN events e ON s.event_id = e.id
            WHERE e.year = ? AND (e.event_name LIKE ? OR e.official_event_name LIKE ?)
            ORDER BY e.round_number, s.id
        """
        
        # Use wildcards for partial matching
        event_pattern = f"%{event_name}%"
        db.cursor.execute(query, (year, event_pattern, event_pattern))
        rows = db.cursor.fetchall()
        
        if not rows:
            print(f"No sessions found for event '{event_name}' in year {year}")
            return
        
        # Print header and rows
        print(f"Sessions for event '{event_name}' in year {year}:")
        print(f"{'ID':>4} | {'Round':>5} | {'Session':<20} | {'Type':<15} | {'Laps':>6} | {'Results':>7}")
        print("-" * 80)
        
        for row in rows:
            print(f"{row['id']:4} | {row['round_number']:5} | {row['name'][:20]:<20} | {row['session_type'] or 'unknown':<15} | {row['lap_count']:6} | {row['result_count']:7}")
    
    except Exception as e:
        migration_logger.error(f"Error listing sessions for event '{event_name}': {e}")
        migration_logger.error(traceback.format_exc())
        print(f"Error: {e}")

def migrate_single_event(db: SQLiteF1Client, year: int, event_name: str, force_reload: bool = False):
    """Migrate data for a specific event only."""
    try:
        # Get full schedule first
        schedule = fastf1.get_event_schedule(year)
        if schedule.empty:
            print(f"No events found for year {year}")
            return False
            
        # Filter schedule for the specified event
        event_pattern = event_name.lower()
        filtered_schedule = schedule[
            schedule['EventName'].str.lower().str.contains(event_pattern) | 
            schedule['OfficialEventName'].str.lower().str.contains(event_pattern)
        ]
        
        if filtered_schedule.empty:
            print(f"No event matching '{event_name}' found in year {year}")
            return False
            
        # Use the first matching event
        event = filtered_schedule.iloc[0]
        print(f"Found event: {event['EventName']} (Round {event['RoundNumber']})")
        
        # Create or update the event record
        event_data = {
            "year": year,
            "round_number": int(event["RoundNumber"]),
            "country": event["Country"],
            "location": event["Location"],
            "official_event_name": event["OfficialEventName"],
            "event_name": event["EventName"],
            "event_date": event["EventDate"].isoformat() if pd.notna(event["EventDate"]) else None,
            "event_format": event["EventFormat"],
            "f1_api_support": bool(event["F1ApiSupport"])
        }
        event_id = db.insert_event(event_data)
        
        # Process sessions for this event
        sessions = []
        for i in range(1, 6):
            s_name = event.get(f"Session{i}")
            if pd.notna(s_name):
                sessions.append(s_name)
                
                # Create or update session record
                s_date_utc = event.get(f"Session{i}DateUtc")
                s_data = {
                    "event_id": event_id,
                    "name": s_name,
                    "date": s_date_utc.isoformat() if pd.notna(s_date_utc) else None,
                    "session_type": _session_type(s_name),
                    "total_laps": None,
                    "session_start_time": None,
                    "t0_date": None
                }
                db.insert_session(s_data)
        
        # Get session info from database
        db.cursor.execute("""
            SELECT s.id, s.name, s.session_type, e.year, e.round_number, e.event_name 
            FROM sessions s 
            JOIN events e ON s.event_id = e.id
            WHERE e.id = ?
        """, (event_id,))
        session_rows = db.cursor.fetchall()
        
        # Process each session
        for session_row in session_rows:
            session_info = dict(session_row)
            print(f"Processing session: {session_info['name']}")
            process_session(session_info, db, year, force_reload)
            
        return True
        
    except Exception as e:
        migration_logger.error(f"Error processing event '{event_name}': {e}")
        migration_logger.error(traceback.format_exc())
        print(f"Error: {e}")
        return False

def fix_sprint_sessions_by_event(db: SQLiteF1Client, year: int, event_name: str, force_reload: bool = False):
    """Fix sprint sessions for a specific event."""
    try:
        # Get sprint sessions for the event
        db.cursor.execute("""
            SELECT s.id, s.name, s.session_type, e.year, e.round_number, e.event_name
            FROM sessions s
            JOIN events e ON s.event_id = e.id
            WHERE e.year = ? 
              AND (e.event_name LIKE ? OR e.official_event_name LIKE ?)
              AND (s.session_type LIKE '%sprint%' OR s.name LIKE '%Sprint%' OR s.name LIKE '%sprint%')
            ORDER BY e.round_number, s.id
        """, (year, f"%{event_name}%", f"%{event_name}%"))
        
        sprint_sessions = [dict(row) for row in db.cursor.fetchall()]
        
        if not sprint_sessions:
            print(f"No sprint sessions found for event '{event_name}' in year {year}")
            return
        
        print(f"\nProcessing {len(sprint_sessions)} sprint sessions for event '{event_name}':")
        
        success_count = 0
        for session in sprint_sessions:
            print(f"\nProcessing: {session['name']} (Round {session['round_number']} - {session['event_name']})")
            
            if process_session(session, db, year, force_reload):
                success_count += 1
                print(f"✓ Successfully processed session")
            else:
                print(f"✗ Failed to process session")
        
        print(f"\nCompleted: {success_count}/{len(sprint_sessions)} sessions processed successfully")
        
    except Exception as e:
        migration_logger.error(f"Error fixing sprint sessions for event '{event_name}': {e}")
        migration_logger.error(traceback.format_exc())
        print(f"Error: {e}")

# Main execution
def main():
    parser = argparse.ArgumentParser(description="Migrate F1 data to SQLite database")
    parser.add_argument("--year", type=int, default=2025, help="Year to migrate data for")
    parser.add_argument("--event", type=str, help="Specific event name to migrate (e.g., 'Chinese Grand Prix')")
    parser.add_argument("--db-path", default=SQLITE_DB_PATH, help="Path to SQLite database")
    parser.add_argument("--force-reload", action="store_true", help="Force delete and reload all data")
    parser.add_argument("--list", action="store_true", help="List sessions in database")
    parser.add_argument("--fix-sprints", action="store_true", help="Fix sprint sessions only")
    parser.add_argument("--fix-telemetry", action="store_true", help="Fix missing telemetry data for sessions")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        migration_logger.setLevel(logging.DEBUG)
        for handler in migration_logger.handlers:
            handler.setLevel(logging.DEBUG)
        try:
            fastf1.set_log_level(logging.DEBUG)
        except Exception:
            pass  # Ignore if can't set FastF1 log level
    else:
        migration_logger.setLevel(logging.INFO)
        for handler in migration_logger.handlers:
            handler.setLevel(logging.INFO)
        try:
            fastf1.set_log_level(logging.WARNING)
        except Exception:
            pass  # Ignore if can't set FastF1 log level
    
    # Print startup info
    print(f"\nF1 Data Migration Tool")
    print(f"Using database at: {args.db_path}")
    print(f"Cache directory: {FASTF1_CACHE_DIR}")
    
    # Initialize database
    db = SQLiteF1Client(db_path=args.db_path)
    
    # Connect to database
    if not db.connect():
        print("Failed to connect to database. Check your database path and permissions.")
        return 1
    
    try:
        # Create tables if they don't exist
        if not db.create_tables():
            print("Failed to create database tables. Check the migration.log for details.")
            return 1
        
        if args.fix_telemetry:
            print(f"\nFixing missing telemetry data for year {args.year}")
            fix_missing_telemetry(db, args.year)
            return 0
        
        # Execute requested command
        if args.list:
            if args.event:
                print(f"\nListing sessions for event: {args.event} (Year: {args.year})")
                list_sessions_by_event(db, args.year, args.event)
            else:
                print(f"\nListing all sessions for year: {args.year}")
                list_sessions(db, args.year)
                
        elif args.fix_sprints:
            if args.event:
                print(f"\nFixing sprint sessions for event: {args.event} (Year: {args.year})")
                fix_sprint_sessions_by_event(db, args.year, args.event, args.force_reload)
            else:
                print(f"\nFixing all sprint sessions for year: {args.year}")
                fix_sprint_sessions(db, args.year, args.force_reload)
                
        else:
            # Regular migration
            if args.event:
                print(f"\nMigrating data for specific event: {args.event} (Year: {args.year})")
                migrate_single_event(db, args.year, args.event, args.force_reload)
            else:
                print(f"\nMigrating all events for year: {args.year}")
                
                # Step 1: Get event schedule and migrate events
                schedule = migrate_events(db, args.year)
                if schedule.empty:
                    print("Failed to get event schedule. Check the migration.log for details.")
                    return 1
                    
                # Step 2: Create session records
                migrate_sessions(db, schedule, args.year)
                
                # Step 3: Migrate session details
                migrate_session_details(db, schedule, args.year, args.force_reload)
            
            print(f"\nMigration completed")
            
        # Show final status
        if args.event:
            list_sessions_by_event(db, args.year, args.event)
        else:
            list_sessions(db, args.year)
            
    except Exception as e:
        migration_logger.error(f"Error in main execution: {e}")
        migration_logger.error(traceback.format_exc())
        print(f"Error: {e}")
        return 1
    finally:
        db.close()
        
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())