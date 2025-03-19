import sqlite3
import logging
import os
from typing import List, Dict, Any, Optional
import pandas as pd

from backend.config import SQLITE_DB_PATH
from archive.redis_live_service import RedisLiveDataService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class F1DataService:
    """
    Abstraction layer for F1 data access.
    Provides a unified interface for accessing historical (SQLite)
    and live (Redis) data.
    """
    def __init__(self, sqlite_path: str = SQLITE_DB_PATH):
        self.sqlite_path = sqlite_path
        self.sqlite_conn: Optional[sqlite3.Connection] = None
        self.redis_service: Optional[RedisLiveDataService] = None
        self._init_sqlite()
        try:
            self.redis_service = RedisLiveDataService()
            logger.info("Redis live data service initialized")
        except Exception as e:
            logger.warning(f"Redis live data service not available: {e}")
            self.redis_service = None

    def _init_sqlite(self) -> None:
        try:
            if os.path.exists(self.sqlite_path):
                self.sqlite_conn = sqlite3.connect(self.sqlite_path)
                self.sqlite_conn.row_factory = sqlite3.Row
                logger.info(f"Connected to SQLite database: {self.sqlite_path}")
            else:
                logger.warning(f"SQLite database does not exist: {self.sqlite_path}")
                self.sqlite_conn = None
        except sqlite3.Error as e:
            logger.error(f"Error connecting to SQLite database: {e}")
            self.sqlite_conn = None

    def _get_sqlite_cursor(self) -> Optional[sqlite3.Cursor]:
        if not self.sqlite_conn:
            self._init_sqlite()
        if self.sqlite_conn:
            return self.sqlite_conn.cursor()
        return None

    def close(self) -> None:
        if self.sqlite_conn:
            self.sqlite_conn.close()
            logger.info("Closed SQLite connection")
        if self.redis_service:
            self.redis_service.stop_polling()
            logger.info("Stopped Redis polling")

    def get_available_years(self) -> List[int]:
        cursor = self._get_sqlite_cursor()
        if not cursor:
            return []
        try:
            cursor.execute("SELECT DISTINCT year FROM events ORDER BY year DESC")
            return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting available years: {e}")
            return []

    def get_current_session(self) -> Optional[Dict[str, Any]]:
        if self.redis_service:
            return self.redis_service.get_live_session()
        return None

    def start_live_polling(self) -> bool:
        if self.redis_service:
            self.redis_service.start_polling()
            return True
        return False

    def get_events(self, year: int) -> List[Dict[str, Any]]:
        cursor = self._get_sqlite_cursor()
        if not cursor:
            return []
        try:
            cursor.execute("""
                SELECT id, round_number, country, location, official_event_name,
                       event_name, event_date, event_format, f1_api_support
                FROM events
                WHERE year = ?
                ORDER BY round_number
            """, (year,))
            events = []
            for row in cursor.fetchall():
                events.append({
                    'id': row['id'],
                    'round_number': row['round_number'],
                    'country': row['country'],
                    'location': row['location'],
                    'official_event_name': row['official_event_name'],
                    'event_name': row['event_name'],
                    'event_date': row['event_date'],
                    'event_format': row['event_format'],
                    'f1_api_support': bool(row['f1_api_support'])
                })
            return events
        except sqlite3.Error as e:
            logger.error(f"Error getting events: {e}")
            return []

    def get_event(self, year: int, round_number: int) -> Optional[Dict[str, Any]]:
        cursor = self._get_sqlite_cursor()
        if not cursor:
            return None
        try:
            cursor.execute("""
                SELECT id, round_number, country, location, official_event_name,
                       event_name, event_date, event_format, f1_api_support
                FROM events
                WHERE year = ? AND round_number = ?
            """, (year, round_number))
            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'round_number': row['round_number'],
                    'country': row['country'],
                    'location': row['location'],
                    'official_event_name': row['official_event_name'],
                    'event_name': row['event_name'],
                    'event_date': row['event_date'],
                    'event_format': row['event_format'],
                    'f1_api_support': bool(row['f1_api_support'])
                }
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting event: {e}")
            return None

    def get_sessions(self, event_id: int) -> List[Dict[str, Any]]:
        cursor = self._get_sqlite_cursor()
        if not cursor:
            return []
        try:
            cursor.execute("""
                SELECT id, name, date, session_type, total_laps, session_start_time, t0_date
                FROM sessions
                WHERE event_id = ?
                ORDER BY CASE 
                    WHEN session_type = 'practice' THEN 1
                    WHEN session_type = 'qualifying' THEN 2
                    WHEN session_type = 'sprint_shootout' THEN 3
                    WHEN session_type = 'sprint_qualifying' THEN 4
                    WHEN session_type = 'sprint' THEN 5
                    WHEN session_type = 'race' THEN 6
                    ELSE 7
                END
            """, (event_id,))
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'id': row['id'],
                    'name': row['name'],
                    'date': row['date'],
                    'session_type': row['session_type'],
                    'total_laps': row['total_laps'],
                    'session_start_time': row['session_start_time'],
                    't0_date': row['t0_date']
                })
            return sessions
        except sqlite3.Error as e:
            logger.error(f"Error getting sessions: {e}")
            return []

    def get_teams(self, year: int) -> List[Dict[str, Any]]:
        cursor = self._get_sqlite_cursor()
        if not cursor:
            return []
        try:
            cursor.execute("""
                SELECT id, name, team_id, team_color
                FROM teams
                WHERE year = ?
                ORDER BY name
            """, (year,))
            teams = []
            for row in cursor.fetchall():
                teams.append({
                    'id': row['id'],
                    'name': row['name'],
                    'team_id': row['team_id'],
                    'team_color': row['team_color']
                })
            return teams
        except sqlite3.Error as e:
            logger.error(f"Error getting teams: {e}")
            return []

    def get_drivers(self, year: int, team_id: Optional[int] = None) -> List[Dict[str, Any]]:
        cursor = self._get_sqlite_cursor()
        if not cursor:
            return []
        try:
            query = """
                SELECT d.id, d.driver_number, d.broadcast_name, d.abbreviation,
                       d.driver_id, d.first_name, d.last_name, d.full_name,
                       d.headshot_url, d.country_code, d.team_id, t.name as team_name,
                       t.team_color
                FROM drivers d
                JOIN teams t ON d.team_id = t.id
                WHERE d.year = ?
            """
            params = [year]
            if team_id is not None:
                query += " AND d.team_id = ?"
                params.append(team_id)
            query += " ORDER BY t.name, d.full_name"
            cursor.execute(query, tuple(params))
            drivers = []
            for row in cursor.fetchall():
                drivers.append({
                    'id': row['id'],
                    'driver_number': row['driver_number'],
                    'broadcast_name': row['broadcast_name'],
                    'abbreviation': row['abbreviation'],
                    'driver_id': row['driver_id'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'full_name': row['full_name'],
                    'headshot_url': row['headshot_url'],
                    'country_code': row['country_code'],
                    'team_id': row['team_id'],
                    'team_name': row['team_name'],
                    'team_color': row['team_color']
                })
            return drivers
        except sqlite3.Error as e:
            logger.error(f"Error getting drivers: {e}")
            return []

    def get_driver_standings(self, year: int) -> List[Dict[str, Any]]:
        cursor = self._get_sqlite_cursor()
        if not cursor:
            return []
        # Check if live standings are available (via Redis)
        current_session = self.get_current_session()
        if current_session and current_session.get('year') == year and self.redis_service:
            live_standings = self.redis_service.get_live_standings()
            if live_standings:
                return live_standings
        try:
            cursor.execute("""
                SELECT d.id, d.full_name, d.abbreviation, t.name as team_name, t.team_color,
                       SUM(r.points) as total_points
                FROM drivers d
                JOIN teams t ON d.team_id = t.id
                JOIN results r ON d.id = r.driver_id
                JOIN sessions s ON r.session_id = s.id
                JOIN events e ON s.event_id = e.id
                WHERE e.year = ? AND (s.session_type = 'race' OR s.session_type = 'sprint')
                GROUP BY d.id
                ORDER BY total_points DESC
            """, (year,))
            standings = []
            for i, row in enumerate(cursor.fetchall()):
                standings.append({
                    'position': i + 1,
                    'driver_id': row['id'],
                    'driver_name': row['full_name'],
                    'abbreviation': row['abbreviation'],
                    'team': row['team_name'],
                    'team_color': row['team_color'],
                    'points': row['total_points']
                })
            return standings
        except sqlite3.Error as e:
            logger.error(f"Error getting driver standings: {e}")
            return []

    def get_constructor_standings(self, year: int) -> List[Dict[str, Any]]:
        cursor = self._get_sqlite_cursor()
        if not cursor:
            return []
        try:
            cursor.execute("""
                SELECT t.id, t.name as team_name, t.team_color,
                       SUM(r.points) as total_points
                FROM teams t
                JOIN drivers d ON t.id = d.team_id
                JOIN results r ON d.id = r.driver_id
                JOIN sessions s ON r.session_id = s.id
                JOIN events e ON s.event_id = e.id
                WHERE e.year = ? AND (s.session_type = 'race' OR s.session_type = 'sprint')
                GROUP BY t.id
                ORDER BY total_points DESC
            """, (year,))
            standings = []
            for i, row in enumerate(cursor.fetchall()):
                standings.append({
                    'position': i + 1,
                    'team_id': row['id'],
                    'team_name': row['team_name'],
                    'team_color': row['team_color'],
                    'points': row['total_points']
                })
            return standings
        except sqlite3.Error as e:
            logger.error(f"Error getting constructor standings: {e}")
            return []

    def get_race_results(self, session_id: int) -> List[Dict[str, Any]]:
        cursor = self._get_sqlite_cursor()
        if not cursor:
            return []
        try:
            cursor.execute("""
                SELECT r.position, r.grid_position, r.points, r.status, r.race_time,
                       d.full_name as driver_name, d.abbreviation, d.driver_number,
                       t.name as team_name, t.team_color
                FROM results r
                JOIN drivers d ON r.driver_id = d.id
                JOIN teams t ON d.team_id = t.id
                WHERE r.session_id = ?
                ORDER BY r.position
            """, (session_id,))
            results = []
            for row in cursor.fetchall():
                results.append({
                    'position': row['position'],
                    'driver_name': row['driver_name'],
                    'abbreviation': row['abbreviation'],
                    'driver_number': row['driver_number'],
                    'team_name': row['team_name'],
                    'team_color': row['team_color'],
                    'grid_position': row['grid_position'],
                    'points': row['points'],
                    'status': row['status'],
                    'race_time': row['race_time']
                })
            return results
        except sqlite3.Error as e:
            logger.error(f"Error getting race results: {e}")
            return []

    def get_lap_times(self, session_id: int, driver_id: Optional[int] = None) -> pd.DataFrame:
        cursor = self._get_sqlite_cursor()
        if not cursor:
            return pd.DataFrame()
        
        try:
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
            params = [session_id]
            
            if driver_id:
                query += " AND l.driver_id = ?"
                params.append(driver_id)
                
            query += " ORDER BY l.lap_number, l.position"
            
            df = pd.read_sql_query(query, self.sqlite_conn, params=params)
            return df
            
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            logger.error(f"Error getting lap times: {e}")
            return pd.DataFrame()

    def get_telemetry(self, session_id: int, driver_id: int, lap_number: int) -> pd.DataFrame:
        cursor = self._get_sqlite_cursor()
        if not cursor:
            return pd.DataFrame()
        
        try:
            query = """
                SELECT time, session_time, speed, rpm, gear, throttle, brake, drs,
                       x, y, z, d.full_name as driver_name, t.team_color
                FROM telemetry tel
                JOIN drivers d ON tel.driver_id = d.id
                JOIN teams t ON d.team_id = t.id
                WHERE tel.session_id = ? AND tel.driver_id = ? AND tel.lap_number = ?
                ORDER BY tel.time
            """
            
            df = pd.read_sql_query(query, self.sqlite_conn, params=(session_id, driver_id, lap_number))
            return df
            
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            logger.error(f"Error getting telemetry data: {e}")
            return pd.DataFrame()

    def get_track_weather(self, latitude: float, longitude: float):
        """Fetch live track weather using Open-Meteo API or from Redis for current session."""
        if self.redis_service:
            live_weather = self.redis_service.get_live_weather()
            if live_weather:
                return live_weather
        
        # Fall back to the weather service if no Redis data
        from backend.weather import get_track_weather as fetch_weather
        return fetch_weather(latitude, longitude)

    # Add other methods for telemetry, lap times, etc.