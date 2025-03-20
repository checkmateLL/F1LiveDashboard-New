import requests
import logging
from typing import Dict, Any, Optional
import json
import os
from datetime import datetime, timedelta
import pytz
import sqlite3

from backend.error_handling import DatabaseError, ResourceNotFoundError, ValidationError, ExternalServiceError
from backend.config import SQLITE_DB_PATH, WEATHER_SERVICE_URL, WEATHER_LATITUDE, WEATHER_LONGITUDE, OPENWEATHER_API_KEY

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Database connection helper
def get_db_connection():
    try:
        return sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise DatabaseError("Failed to connect to SQLite database")

# Create table for weather caching
def initialize_weather_cache():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS weather_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    latitude REAL,
                    longitude REAL,
                    request_time TEXT,
                    response_data TEXT
                )
            """)
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error creating weather_cache table: {e}")
        raise DatabaseError("Error initializing weather cache")

# Function to fetch weather data
def get_track_weather(latitude: float = WEATHER_LATITUDE, longitude: float = WEATHER_LONGITUDE) -> dict:
    """
    Retrieves weather data for the track location.
    Uses SQLite caching to reduce unnecessary API calls.
    
    :param latitude: Latitude of the track.
    :param longitude: Longitude of the track.
    :return: Weather data dictionary.
    """
    try:
        initialize_weather_cache()

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if we have cached data within the last 60 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=60)
            cursor.execute("""
                SELECT response_data FROM weather_cache 
                WHERE latitude = ? AND longitude = ? 
                AND request_time > ? 
                ORDER BY request_time DESC LIMIT 1
            """, (latitude, longitude, cutoff_time.isoformat()))

            cached_data = cursor.fetchone()
            if cached_data:
                logger.info("Returning cached weather data")
                return eval(cached_data[0])  # Convert string back to dict

    except sqlite3.Error as e:
        logger.error(f"Error querying weather cache: {e}")
        raise DatabaseError("Error retrieving weather data from cache")

    # If no cached data, fetch from API
    try:
        logger.info("Fetching new weather data from API")
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,cloudcover,wind_speed_10m",
            "timezone": "UTC"
        }

        response = requests.get(WEATHER_SERVICE_URL, params=params, timeout=10)
        response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses

        weather_data = response.json()

        # Cache the new weather data
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO weather_cache (latitude, longitude, request_time, response_data)
                    VALUES (?, ?, ?, ?)
                """, (latitude, longitude, datetime.utcnow().isoformat(), str(weather_data)))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error storing weather data in cache: {e}")
            raise DatabaseError("Failed to cache weather data")

        return weather_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Weather API request failed: {e}")
        raise ExternalServiceError("Weather API", "Failed to fetch weather data")

    except Exception as e:
        logger.error(f"Unexpected error retrieving weather data: {e}")
        raise ExternalServiceError("Weather API", "Unexpected error occurred while fetching weather data")

# Function to fetch weather for a specific location and time
def get_weather_for_location(event_name: str, session_time: str) -> dict:
    """
    Retrieves weather for a specific event and session time.
    
    :param event_name: Name of the event (e.g., "Monza GP").
    :param session_time: Timestamp for the session in ISO format.
    :return: Weather data dictionary.
    """
    if not event_name:
        raise ValidationError("Event name must not be empty")

    if not session_time:
        raise ValidationError("Session time must be a valid ISO timestamp")

    try:
        # Convert session time to datetime
        session_datetime = datetime.fromisoformat(session_time)

        logger.info(f"Fetching weather for {event_name} at {session_datetime}")

        params = {
            "latitude": WEATHER_LATITUDE,
            "longitude": WEATHER_LONGITUDE,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,cloudcover,wind_speed_10m",
            "timezone": "UTC",
            "start": session_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": (session_datetime + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        response = requests.get(WEATHER_SERVICE_URL, params=params, timeout=10)
        response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses

        weather_data = response.json()

        return weather_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Weather API request failed: {e}")
        raise ExternalServiceError("Weather API", "Failed to fetch weather data for event")

    except Exception as e:
        logger.error(f"Unexpected error retrieving weather data: {e}")
        raise ExternalServiceError("Weather API", "Unexpected error occurred while fetching weather data for event")
