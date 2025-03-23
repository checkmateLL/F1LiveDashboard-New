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
    """Abstraction layer for F1 data access."""

    def __init__(self, sqlite_path: str = SQLITE_DB_PATH):
        self.sqlite_path = sqlite_path

    @staticmethod
    def _convert_id(value):
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.error(f"Invalid ID format: {value}")
            raise DatabaseError(f"Invalid ID format: {value}")

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
        session_id = self._convert_id(session_id)

        query = "SELECT * FROM laps WHERE session_id = ?"
        params = [session_id]

        if driver_id:
            driver_id = self._convert_id(driver_id)
            query += " AND driver_id = ?"
            params.append(driver_id)

        logger.debug(f"Executing SQL Query: {query} with params {params}")

        try:
            with DatabaseConnectionHandler(self.sqlite_path) as db:
                df = pd.read_sql_query(query, db.conn, params=params)
                if df.empty:
                    logger.warning(f"No lap times found for session_id={session_id}, driver_id={driver_id}")
                return df
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            logger.error(f"Database error during lap time retrieval: {e}")
            raise DatabaseError("Error retrieving lap times")

    def get_telemetry(self, session_id: int, driver_id: int, lap_number: int) -> pd.DataFrame:
        session_id = self._convert_id(session_id)
        driver_id = self._convert_id(driver_id)
        lap_number = self._convert_id(lap_number)

        query = """
            SELECT * FROM telemetry
            WHERE session_id = ? AND driver_id = ? AND lap_number = ?
            ORDER BY time
        """
        params = (session_id, driver_id, lap_number)

        logger.debug(f"Executing SQL Query: {query} with params {params}")

        try:
            with DatabaseConnectionHandler(self.sqlite_path) as db:
                df = pd.read_sql_query(query, db.conn, params=params)
                if df.empty:
                    logger.warning(f"No telemetry data found for session_id={session_id}, driver_id={driver_id}, lap_number={lap_number}")
                return df
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            logger.error(f"Database error during telemetry data retrieval: {e}")
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

    def get_race_sessions(self, event_id):
        """
        Fetches race sessions for an event.
        
        Parameters:
        - event_id: The ID of the event
        
        Returns:
        - List of race session dictionaries
        """
        event_id = self._convert_id(event_id)
        query = """
            SELECT id, name, date, session_type, total_laps
            FROM sessions
            WHERE event_id = ? AND session_type = 'race'
            ORDER BY date
        """
        try:
            with DatabaseConnectionHandler() as db:
                return db.execute_query(query, (event_id,))
        except DatabaseError as e:
            logger.error(f"Error retrieving race sessions for event {event_id}: {e}")
            return []

    def get_event_by_id(self, event_id):
        """
        Fetches an event by its ID.
        
        Parameters:
        - event_id: The ID of the event
        
        Returns:
        - Event dictionary or None if not found
        """
        event_id = self._convert_id(event_id)
        query = """
            SELECT id, year, round_number, country, location, official_event_name,
                event_name, event_date, event_format, f1_api_support
            FROM events
            WHERE id = ?
        """
        try:
            with DatabaseConnectionHandler() as db:
                results = db.execute_query(query, (event_id,))
            if results:
                return results[0]
            return None
        except DatabaseError as e:
            logger.error(f"Error retrieving event {event_id}: {e}")
            return None

    def get_track_performance(self, event_id):
        """
        Fetches track-specific performance data.
        
        Parameters:
        - event_id: The ID of the event
        
        Returns:
        - DataFrame with track performance data
        """
        event_id = self._convert_id(event_id)
        # First get the sessions for this event
        sessions = self.get_sessions(event_id)
        if not sessions:
            return pd.DataFrame()
        
        session_ids = [session["id"] for session in sessions]
        
        # Create an empty DataFrame to store results
        track_df = pd.DataFrame()
        
        # Get lap time data for each session
        for session_id in session_ids:
            lap_data = self.get_lap_times(session_id)
            if not lap_data.empty:
                # Add session info
                for session in sessions:
                    if session["id"] == session_id:
                        lap_data["session_name"] = session["name"]
                        lap_data["session_type"] = session["session_type"]
                        break
                
                # Append to main DataFrame
                track_df = pd.concat([track_df, lap_data], ignore_index=True)
        
        # Add weather data if available
        try:
            for session_id in session_ids:
                weather_data = self.get_weather(session_id)
                if weather_data and not isinstance(weather_data, dict):
                    # Extract relevant weather data and join with lap data
                    for weather in weather_data:
                        time = weather.get("time")
                        # Find laps that occurred around this weather measurement
                        # This is a simplification - in a real implementation, you'd match times more precisely
                        mask = (track_df["session_id"] == session_id)
                        if mask.any():
                            track_df.loc[mask, "air_temp"] = weather.get("air_temp")
                            track_df.loc[mask, "track_temp"] = weather.get("track_temp")
                            track_df.loc[mask, "wind_speed"] = weather.get("wind_speed")
                            track_df.loc[mask, "humidity"] = weather.get("humidity")
                            track_df.loc[mask, "rainfall"] = weather.get("rainfall", 0)
        except Exception as e:
            logger.error(f"Error adding weather data to track performance: {e}")
        
        return track_df

    def get_laps(self, session_id):
        """
        Fetches lap data including position information.
        
        Parameters:
        - session_id: The ID of the session
        
        Returns:
        - DataFrame with lap data
        """
        session_id = self._convert_id(session_id)
        
        # Get basic lap data
        lap_data = self.get_lap_times(session_id)
        
        if lap_data.empty:
            return pd.DataFrame()
        
        # For race replay, we need track position data
        # This would come from telemetry, so we'll fetch that and merge
        try:
            # Get all drivers in this session
            drivers = set(lap_data["driver_id"].unique())
            
            # This will store position data
            position_data = []
            
            # For each driver, get a sample of positions for visualization
            for driver_id in drivers:
                driver_laps = lap_data[lap_data["driver_id"] == driver_id]
                
                for _, lap in driver_laps.iterrows():
                    lap_number = lap["lap_number"]
                    
                    # Get telemetry data for this lap
                    try:
                        telemetry = self.get_telemetry(session_id, driver_id, lap_number)
                        if not telemetry.empty:
                            # Sample points for visualization (e.g., every 10th point)
                            telem_sample = telemetry.iloc[::10].copy()
                            telem_sample["lap_number"] = lap_number
                            telem_sample["driver_id"] = driver_id
                            telem_sample["driver_name"] = lap["driver_name"]
                            telem_sample["team_name"] = lap["team_name"]
                            telem_sample["team_color"] = lap["team_color"]
                            telem_sample["compound"] = lap["compound"]
                            telem_sample["position"] = lap["position"]
                            
                            position_data.append(telem_sample)
                    except Exception as e:
                        logger.warning(f"Error getting telemetry for driver {driver_id}, lap {lap_number}: {e}")
                        continue
            
            # Combine all position data
            if position_data:
                positions_df = pd.concat(position_data, ignore_index=True)
                return positions_df
            
            # If we couldn't get position data, just return the lap data
            return lap_data
            
        except Exception as e:
            logger.error(f"Error getting position data for session {session_id}: {e}")
            return lap_data

    def get_lap_numbers(self, session_id, driver_id):
        """
        Fetches available lap numbers for a driver in a session.
        
        Parameters:
        - session_id: The ID of the session
        - driver_id: The ID of the driver
        
        Returns:
        - DataFrame with lap numbers
        """
        session_id = self._convert_id(session_id)
        driver_id = self._convert_id(driver_id)
        
        query = """
            SELECT DISTINCT lap_number
            FROM laps
            WHERE session_id = ? AND driver_id = ?
            ORDER BY lap_number
        """
        
        try:
            conn = sqlite3.connect(self.sqlite_path)
            df = pd.read_sql_query(query, conn, params=(session_id, driver_id))
            conn.close()
            return df
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            logger.error(f"Error retrieving lap numbers for session {session_id}, driver {driver_id}: {e}")
            return pd.DataFrame()

    def get_drivers(self, session_id):
        """
        Fetches drivers who participated in a specific session.
        
        Parameters:
        - session_id: The ID of the session
        
        Returns:
        - List of driver dictionaries
        """
        session_id = self._convert_id(session_id)
        
        query = """
            SELECT DISTINCT d.id, d.driver_number, d.broadcast_name, d.abbreviation, 
                d.first_name, d.last_name, d.full_name, d.headshot_url, d.country_code,
                t.name as team_name, t.team_color, t.id as team_id
            FROM laps l
            JOIN drivers d ON l.driver_id = d.id
            JOIN teams t ON d.team_id = t.id
            WHERE l.session_id = ?
            ORDER BY t.name, d.full_name
        """
        
        try:
            with DatabaseConnectionHandler() as db:
                return db.execute_query(query, (session_id,))
        except DatabaseError as e:
            logger.error(f"Error retrieving drivers for session {session_id}: {e}")
            return []

    def get_weather_impact_data(self, session_id):
        """
        Fetches combined lap and weather data for analysis.
        
        Parameters:
        - session_id: The ID of the session
        
        Returns:
        - DataFrame with lap and weather data
        """
        session_id = self._convert_id(session_id)
        
        # First get the lap data
        lap_data = self.get_lap_times(session_id)
        
        if lap_data.empty:
            return pd.DataFrame()
        
        # Get weather data
        weather_data = self.get_weather(session_id)
        
        # If no weather data, return just the lap data
        if not weather_data or isinstance(weather_data, dict):
            return lap_data
        
        # Convert weather data to DataFrame if it's not already
        if not isinstance(weather_data, pd.DataFrame):
            weather_df = pd.DataFrame(weather_data)
        else:
            weather_df = weather_data
        
        # Simplify by assigning the same weather conditions to groups of laps
        # This is an approximation - in a real implementation, you'd match times more precisely
        if not weather_df.empty and 'time' in weather_df.columns:
            # Sort weather data by time
            weather_df = weather_df.sort_values('time')
            
            # Add lap number column based on timing (simplified approach)
            # Divide total laps by number of weather readings
            total_laps = lap_data['lap_number'].max()
            weather_readings = len(weather_df)
            
            if weather_readings > 0:
                laps_per_reading = max(1, int(total_laps / weather_readings))
                
                # Assign lap numbers to weather readings
                weather_df['lap_start'] = [1 + i * laps_per_reading for i in range(weather_readings)]
                weather_df['lap_end'] = [(i + 1) * laps_per_reading for i in range(weather_readings)]
                weather_df.loc[weather_df.index[-1], 'lap_end'] = total_laps  # Ensure last entry covers all remaining laps
                
                # Merge weather data with lap data
                result_df = lap_data.copy()
                
                # For each lap, find the corresponding weather data
                for idx, row in weather_df.iterrows():
                    lap_start = row['lap_start']
                    lap_end = row['lap_end']
                    
                    # Apply weather data to laps in this range
                    mask = (result_df['lap_number'] >= lap_start) & (result_df['lap_number'] <= lap_end)
                    
                    if mask.any():
                        for col in ['air_temp', 'track_temp', 'humidity', 'pressure', 'wind_speed', 'wind_direction']:
                            if col in weather_df.columns:
                                result_df.loc[mask, col] = row.get(col)
                        
                        # Handle rainfall as a boolean
                        if 'rainfall' in weather_df.columns:
                            result_df.loc[mask, 'rainfall'] = bool(row.get('rainfall', 0))
                
                return result_df
        
        return lap_data
    
    def get_dnf_data(self, session_id: int) -> pd.DataFrame:
        """
        Fetches drivers who did not finish (DNF) in a given session.
        
        Parameters:
        - session_id: The session ID
        
        Returns:
        - DataFrame containing DNF information
        """
        session_id = self._convert_id(session_id)

        query = """
            SELECT 
                r.driver_id, d.full_name AS driver_name, d.abbreviation, 
                t.name AS team_name, t.team_color, 
                r.classified_position, r.status, r.race_time
            FROM results r
            JOIN drivers d ON r.driver_id = d.id
            JOIN teams t ON d.team_id = t.id
            WHERE r.session_id = ? 
                AND (r.status NOT IN ('Finished', 'Running') OR r.status IS NULL)
            ORDER BY r.classified_position
        """

        try:
            with DatabaseConnectionHandler() as db:
                df = pd.read_sql_query(query, db.conn, params=(session_id,))
                
                if df.empty:
                    logger.warning(f"No DNF data found for session {session_id}")
                    return pd.DataFrame()  # Return an empty DataFrame
                
                return df
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            logger.error(f"Database error retrieving DNF data for session {session_id}: {e}")
            raise DatabaseError("Error retrieving DNF data")

