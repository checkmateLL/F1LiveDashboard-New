import os
import sys
import time
import argparse
import logging
from typing import Optional
import pandas as pd
from tqdm import tqdm

import fastf1
from dotenv import load_dotenv

from config import FASTF1_CACHE_DIR, SQLITE_DB_PATH

load_dotenv()

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

fastf1.Cache.enable_cache(FASTF1_CACHE_DIR)
fastf1.set_log_level(logging.INFO)

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
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        migration_logger.info(f"Connected to SQLite database: {self.db_path}")

    def close(self):
        if self.conn:
            self.conn.close()
            migration_logger.info("Closed SQLite connection")

    def commit(self):
        if self.conn:
            self.conn.commit()

    def create_tables(self):
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
            self.commit()
            migration_logger.info("Created/verified all tables successfully.")
        except Exception as e:
            migration_logger.error(f"Error creating tables: {e}")
            raise

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

#############################
# Migrate Functions
#############################

def migrate_events(db: SQLiteF1Client, year: int) -> pd.DataFrame:
    migration_logger.info(f"Fetching event schedule for {year}")
    schedule = fastf1.get_event_schedule(year)
    for idx, ev in schedule.iterrows():
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
    return schedule

def _session_type(session_name: str) -> str:
    if "Practice" in session_name:
        return "practice"
    elif "Qualifying" in session_name:
        return "qualifying"
    elif "Sprint" in session_name:
        if "Shootout" in session_name:
            return "sprint_shootout"
        elif "Qualifying" in session_name:
            return "sprint_qualifying"
        else:
            return "sprint"
    elif "Race" in session_name:
        return "race"
    return "unknown"

def migrate_sessions(db: SQLiteF1Client, schedule: pd.DataFrame, year: int):
    for idx, ev in schedule.iterrows():
        event_id = db.cursor.execute("""
            SELECT id FROM events WHERE year = ? AND round_number = ?
        """, (year, int(ev["RoundNumber"]))).fetchone()
        if not event_id:
            continue
        event_id = event_id["id"]
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
            db.insert_session(s_data)

def migrate_teams_and_drivers(db: SQLiteF1Client, session_obj, year: int):
    if not hasattr(session_obj, "results") or session_obj.results is None or len(session_obj.results) == 0:
        migration_logger.warning(f"No results data for session: {session_obj.name}")
        return
        
    for _, row in session_obj.results.iterrows():
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

def migrate_results(db: SQLiteF1Client, session_obj, session_id: int, year: int):
    if not hasattr(session_obj, "results") or session_obj.results is None or len(session_obj.results) == 0:
        migration_logger.warning(f"No results data for session ID: {session_id}")
        return
        
    drivers_map = {}
    for _, row in session_obj.results.iterrows():
        abbr = row["Abbreviation"]
        db.cursor.execute("""
            SELECT id FROM drivers WHERE abbreviation = ? AND year = ?
        """, (abbr, year))
        found = db.cursor.fetchone()
        if found:
            drivers_map[abbr] = found["id"]
    
    for _, row in session_obj.results.iterrows():
        abbr = row["Abbreviation"]
        driver_id = drivers_map.get(abbr)
        if not driver_id:
            migration_logger.warning(f"No driver found for abbreviation: {abbr}")
            continue
            
        db.cursor.execute("""
            SELECT id FROM results WHERE session_id = ? AND driver_id = ?
        """, (session_id, driver_id))
        if db.cursor.fetchone():
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
            int(row["Position"]) if pd.notna(row["Position"]) else None,
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

def migrate_laps(db: SQLiteF1Client, session_obj, session_id: int, year: int):
    if not hasattr(session_obj, "laps") or session_obj.laps is None or len(session_obj.laps) == 0:
        migration_logger.warning(f"No lap data for session ID: {session_id}")
        return
        
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
    for _, lap in tqdm(laps_df.iterrows(), total=len(laps_df), desc="Migrating laps"):
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
        except Exception as e:
            migration_logger.error(f"Error inserting lap {lap_number} for driver {abbr}: {e}")
            continue

        # Insert telemetry data
        try:
            tel = lap.get_telemetry()
            if tel is not None and not tel.empty:
                # Use a batch insert approach for better performance
                telemetry_batch = []
                for _, tel_row in tel.iterrows():
                    # Create a unique key for this telemetry point
                    time_str = str(tel_row["Time"]) if pd.notna(tel_row["Time"]) else None
                    
                    # Check if this record already exists - use a more efficient approach
                    # by building a batch instead of checking one by one
                    tel_data = (
                        driver_id,
                        lap_number,
                        session_id,
                        time_str,
                        str(tel_row["SessionTime"]) if ("SessionTime" in tel_row.index and pd.notna(tel_row["SessionTime"])) else None,
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
                    telemetry_batch.append(tel_data)
                
                # Execute in batches of 1000 for better performance
                batch_size = 1000
                for i in range(0, len(telemetry_batch), batch_size):
                    batch = telemetry_batch[i:i+batch_size]
                    
                    # Use INSERT OR IGNORE to avoid duplicates
                    db.cursor.executemany("""
                        INSERT OR IGNORE INTO telemetry (
                            driver_id, lap_number, session_id, time, session_time,
                            date, speed, rpm, gear, throttle, brake, drs, x, y, z, source, year
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch)
                db.commit()
        except Exception as e:
            migration_logger.error(f"Telemetry error lap {lap_number}, driver {abbr}: {e}")

def migrate_weather(db: SQLiteF1Client, session_obj, session_id: int):
    if not hasattr(session_obj, "weather_data") or session_obj.weather_data is None or session_obj.weather_data.empty:
        migration_logger.warning(f"No weather data for session ID: {session_id}")
        return
        
    wdf = session_obj.weather_data
    weather_batch = []
    
    for _, wrow in wdf.iterrows():
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
    
    # Execute batch insert
    if weather_batch:
        db.cursor.executemany("""
            INSERT OR IGNORE INTO weather (
                session_id, time, air_temp, humidity, pressure, rainfall,
                track_temp, wind_direction, wind_speed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, weather_batch)
        db.commit()

def migrate_session_details(db: SQLiteF1Client, schedule, year: int):
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
                        SELECT id FROM sessions 
                        WHERE event_id = ? AND name = ?
                    """, (event_id, session_name))
                    session_row = db.cursor.fetchone()
                    
                    if session_row:
                        session_id = session_row["id"]
                        migration_logger.info(f"Processing existing session: {session_name} for event {ev['EventName']}")
                    else:
                        # If session doesn't exist in the database yet, let's initialize it
                        migration_logger.info(f"Initializing session: {session_name} for event {ev['EventName']}")
                        try:
                            session_obj = fastf1.get_session(year, ev["RoundNumber"], session_name)
                            session_obj.load(laps=False, telemetry=False, weather=False, messages=False)
                            
                            s_data = {
                                "event_id": event_id,
                                "name": session_name,
                                "date": session_obj.date.isoformat() if hasattr(session_obj, "date") and session_obj.date else None,
                                "session_type": _session_type(session_name),
                                "total_laps": None,
                                "session_start_time": None,
                                "t0_date": None
                            }
                            session_id = db.insert_session(s_data)
                        except Exception as e:
                            migration_logger.error(f"Failed to initialize session '{session_name}' for {ev['EventName']}: {e}")
                            continue
                    
                    # Now we have a session_id, let's load the full session data and migrate it
                    try:
                        migration_logger.info(f"Loading full data for session: {session_name}")
                        session_obj = fastf1.get_session(year, ev["RoundNumber"], session_name)
                        session_obj.load(laps=True, telemetry=True, weather=True, messages=True)
                        
                        # Update the session with any additional data we now have
                        if hasattr(session_obj, "laps_from_session") and session_obj.laps_from_session:
                            db.cursor.execute("""
                                UPDATE sessions 
                                SET total_laps = ?, session_start_time = ?, t0_date = ?
                                WHERE id = ?
                            """, (
                                session_obj.total_laps if hasattr(session_obj, "total_laps") else None,
                                str(session_obj.session_start_time) if hasattr(session_obj, "session_start_time") else None,
                                session_obj.t0_date.isoformat() if hasattr(session_obj, "t0_date") and session_obj.t0_date else None,
                                session_id
                            ))
                            db.commit()
                        
                        # Run migrations
                        migration_logger.info(f"Migrating teams and drivers for session: {session_name}")
                        migrate_teams_and_drivers(db, session_obj, year)
                        
                        migration_logger.info(f"Migrating results for session: {session_name}")
                        migrate_results(db, session_obj, session_id, year)
                        
                        migration_logger.info(f"Migrating laps for session: {session_name}")
                        migrate_laps(db, session_obj, session_id, year)
                        
                        migration_logger.info(f"Migrating weather for session: {session_name}")
                        migrate_weather(db, session_obj, session_id)
                        
                        migration_logger.info(f"Completed migration for session: {session_name}")
                        
                    except Exception as e:
                        migration_logger.error(f"Error processing session '{session_name}' for {ev['EventName']}: {e}")
                        continue
                        
                except Exception as e:
                    migration_logger.error(f"Error in session processing loop for '{session_name}': {e}")
            
        except Exception as e:
            migration_logger.error(f"Error processing event {ev['EventName'] if 'EventName' in ev else 'unknown'}: {e}")
            continue