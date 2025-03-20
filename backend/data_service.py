import sqlite3
import logging
import os
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from backend.db_connection import DatabaseConnectionHandler
from backend.config import SQLITE_DB_PATH
from backend.error_handling import DatabaseError, ResourceNotFoundError, handle_exception
from backend.weather import get_track_weather as fetch_weather

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class F1DataService:
    """
    Abstraction layer for F1 data access.
    Provides a unified interface for accessing F1 data from SQLite.
    """
    
    def __init__(self, sqlite_path: str = SQLITE_DB_PATH):
        self.sqlite_path = sqlite_path

    @staticmethod
    def _convert_id(value):
        """Ensures IDs are converted to Python integers."""
        return int(value) if isinstance(value, (np.integer, str)) else value

    def get_available_years(self) -> List[int]:
        """Fetches distinct years from the events table."""
        query = "SELECT DISTINCT year FROM events ORDER BY year DESC"
        try:
            with DatabaseConnectionHandler() as db:
                return [row["year"] for row in db.execute_query(query)]
        except DatabaseError as e:
            logger.error(f"Error retrieving available years: {e}")
            raise

    def get_events(self, year: int) -> List[Dict[str, Any]]:
        """Fetches all events for a given year."""
        year = self._convert_id(year)
        query = """
            SELECT id, round_number, country, location, official_event_name,
                   event_name, event_date, event_format, f1_api_support
            FROM events
            WHERE year = ?
            ORDER BY round_number
        """
        try:
            with DatabaseConnectionHandler() as db:
                return db.execute_query(query, (year,))
        except DatabaseError as e:
            logger.error(f"Error retrieving events for year {year}: {e}")
            raise

    def get_event(self, year: int, round_number: int) -> Dict[str, Any]:
        """Fetches a specific event."""
        year = self._convert_id(year)
        round_number = self._convert_id(round_number)
        query = "SELECT * FROM events WHERE year = ? AND round_number = ?"
        try:
            with DatabaseConnectionHandler() as db:
                result = db.execute_query(query, (year, round_number))
            if not result:
                raise ResourceNotFoundError("Event", f"year={year}, round={round_number}")
            return result[0]
        except DatabaseError as e:
            logger.error(f"Error retrieving event {round_number} for year {year}: {e}")
            raise

    def get_sessions(self, event_id: int) -> List[Dict[str, Any]]:
        """Fetches all sessions for an event."""
        event_id = self._convert_id(event_id)
        query = """
            SELECT id, name, date, session_type, total_laps, session_start_time, t0_date
            FROM sessions
            WHERE event_id = ?
            ORDER BY date ASC
        """
        try:
            with DatabaseConnectionHandler() as db: 
                return db.execute_query(query, (event_id,))
        except DatabaseError as e:
            logger.error(f"Error retrieving sessions for event {event_id}: {e}")
            raise

    def get_teams(self, year: int) -> List[Dict[str, Any]]:
        """Fetches all teams for a given year."""
        year = self._convert_id(year)
        query = """
            SELECT id, name, team_id, team_color
            FROM teams
            WHERE year = ?
            ORDER BY name
        """
        try:
            with DatabaseConnectionHandler() as db: 
                return db.execute_query(query, (year,))
        except DatabaseError as e:
            logger.error(f"Error retrieving teams for year {year}: {e}")
            raise

    def get_drivers(self, year: int, team_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetches all drivers for a given year, optionally filtering by team."""
        year = self._convert_id(year)
        query = """
            SELECT id, driver_number, broadcast_name, abbreviation, driver_id, 
                   first_name, last_name, full_name, headshot_url, country_code, team_id
            FROM drivers
            WHERE year = ?
        """
        params = [year]
        if team_id:
            team_id = self._convert_id(team_id)
            query += " AND team_id = ?"
            params.append(team_id)

        query += " ORDER BY team_id, driver_number"
        try:
            with DatabaseConnectionHandler() as db: 
                return db.execute_query(query, tuple(params))
        except DatabaseError as e:
            logger.error(f"Error retrieving drivers for year {year}, team {team_id}: {e}")
            raise

    def get_driver_standings(self, year: int) -> List[Dict[str, Any]]:
        """Fetches driver standings for a given year based on race results."""
        year = self._convert_id(year)
        query = """
            SELECT d.id AS driver_id, d.full_name, d.abbreviation, 
                   t.name AS team_name, t.team_color, SUM(r.points) AS total_points
            FROM drivers d
            JOIN teams t ON d.team_id = t.id
            JOIN results r ON d.id = r.driver_id
            JOIN sessions s ON r.session_id = s.id
            JOIN events e ON s.event_id = e.id
            WHERE e.year = ?
            GROUP BY d.id
            ORDER BY total_points DESC
        """
        try:
            with DatabaseConnectionHandler() as db: 
                return db.execute_query(query, (year,))
        except DatabaseError as e:
            logger.error(f"Error retrieving driver standings for year {year}: {e}")
            raise

    def get_constructor_standings(self, year: int) -> List[Dict[str, Any]]:
        """Fetches constructor standings for a given year based on race results."""
        year = self._convert_id(year)
        query = """
            SELECT t.id AS team_id, t.name AS team_name, t.team_color, 
                   SUM(r.points) AS total_points
            FROM teams t
            JOIN drivers d ON t.id = d.team_id
            JOIN results r ON d.id = r.driver_id
            JOIN sessions s ON r.session_id = s.id
            JOIN events e ON s.event_id = e.id
            WHERE e.year = ?
            GROUP BY t.id
            ORDER BY total_points DESC
        """
        try:
            with DatabaseConnectionHandler() as db: 
                return db.execute_query(query, (year,))
        except DatabaseError as e:
            logger.error(f"Error retrieving constructor standings for year {year}: {e}")
            raise

    def get_race_results(self, session_id: int) -> List[Dict[str, Any]]:
        """Fetches race results for a given session."""
        session_id = self._convert_id(session_id)
        query = """
            SELECT r.position, r.grid_position, r.points, r.status, r.race_time,
                   d.full_name AS driver_name, d.abbreviation, d.driver_number,
                   t.name AS team_name, t.team_color
            FROM results r
            JOIN drivers d ON r.driver_id = d.id
            JOIN teams t ON d.team_id = t.id
            WHERE r.session_id = ?
            ORDER BY r.position
        """
        try:
            with DatabaseConnectionHandler() as db: 
                return db.execute_query(query, (session_id,))
        except DatabaseError as e:
            logger.error(f"Error retrieving race results for session {session_id}: {e}")
            raise

    def get_lap_times(self, session_id: int, driver_id: Optional[int] = None) -> pd.DataFrame:
        """Fetches lap times for a given session, optionally filtering by driver."""
        session_id = self._convert_id(session_id)
        query = "SELECT * FROM laps WHERE session_id = ?"
        params = [session_id]

        if driver_id:
            driver_id = self._convert_id(driver_id)
            query += " AND driver_id = ?"
            params.append(driver_id)

        try:
            df = pd.read_sql_query(query, sqlite3.connect(self.sqlite_path), params=params)
            return df
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            logger.error(f"Error retrieving lap times for session {session_id}: {e}")
            raise DatabaseError("Error retrieving lap times")

    def get_telemetry(self, session_id: int, driver_id: int, lap_number: int) -> pd.DataFrame:
        """Fetches telemetry data for a given session, driver, and lap number."""
        session_id = self._convert_id(session_id)
        driver_id = self._convert_id(driver_id)
        lap_number = self._convert_id(lap_number)

        query = """
            SELECT * FROM telemetry
            WHERE session_id = ? AND driver_id = ? AND lap_number = ?
            ORDER BY time
        """
        try:
            df = pd.read_sql_query(query, sqlite3.connect(self.sqlite_path), params=(session_id, driver_id, lap_number))
            return df
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            logger.error(f"Error retrieving telemetry data for session {session_id}, driver {driver_id}: {e}")
            raise DatabaseError("Error retrieving telemetry data")

    def get_weather(self, session_id: int) -> Dict[str, Any]:
        """Fetches weather data for a given session."""
        session_id = self._convert_id(session_id)
        query = """
            SELECT * FROM weather WHERE session_id = ?
            ORDER BY time ASC
        """
        try:
            with DatabaseConnectionHandler() as db: 
                result = db.execute_query(query, (session_id,))
            if not result:
                return {"error": "No weather data available"}
            return result
        except DatabaseError as e:
            logger.error(f"Error retrieving weather data for session {session_id}: {e}")
            raise

    def get_track_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch track weather from Open-Meteo API."""
        try:
            return fetch_weather(latitude, longitude)
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            raise DatabaseError("Error fetching weather data")
        """Fetch track weather using Open-Meteo API."""
        from backend.weather import get_track_weather as fetch_weather
        
        try:
            return fetch_weather(latitude, longitude)
        except Exception as e:
            error_msg = f"Error fetching weather data: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)