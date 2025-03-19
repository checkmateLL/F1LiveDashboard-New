import requests
import logging
from typing import Dict, Any, Optional
import json
import os
from datetime import datetime
import pytz

from backend.error_handling import DatabaseError, ResourceNotFoundError, ValidationError, ExternalServiceError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_track_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Fetch track weather using Open-Meteo API.
    
    Parameters:
    - latitude: The latitude of the track location
    - longitude: The longitude of the track location
    
    Returns:
    - Dictionary containing weather data
    
    Raises:
    - ValidationError: If coordinates are invalid
    - ExternalServiceError: If there's an issue with the weather API
    - DatabaseError: For any other error
    """
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValidationError("Latitude and longitude must be numeric values")
    
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,relativehumidity_2m,precipitation,cloudcover,windspeed_10m",
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        hourly = data.get("hourly", {})

        if "time" not in hourly or not hourly["time"]:
            raise ResourceNotFoundError(
                resource_type="Weather data", 
                identifier=f"lat={latitude}, lon={longitude}"
            )
        
        # Get current time
        current_time = datetime.now().strftime("%Y-%m-%dT%H:00")
        closest_index = 0
        
        # Find closest time to current time
        for i, time in enumerate(hourly["time"]):
            if time >= current_time:
                closest_index = i
                break
        
        # Extract relevant weather data
        weather_data = {
            "temperature": hourly["temperature_2m"][closest_index] if "temperature_2m" in hourly else None,
            "track_temperature": hourly["temperature_2m"][closest_index] + 8 if "temperature_2m" in hourly else None,
            "wind_speed": hourly["windspeed_10m"][closest_index] if "windspeed_10m" in hourly else None,
            "cloud_cover": hourly["cloudcover"][closest_index] if "cloudcover" in hourly else None,
            "rainfall": hourly["precipitation"][closest_index] > 0 if "precipitation" in hourly else False,
            "humidity": hourly["relativehumidity_2m"][closest_index] if "relativehumidity_2m" in hourly else None,
            "time": hourly["time"][closest_index] if "time" in hourly else None
        }
        
        logger.info(f"Weather data retrieved for coordinates: {latitude}, {longitude}")
        return weather_data
    
    except ResourceNotFoundError:
        # Re-raise resource not found errors
        raise
    except requests.RequestException as e:
        logger.error(f"Error connecting to weather service: {str(e)}")
        raise ExternalServiceError(
            service_name="Open-Meteo",
            message=f"Failed to retrieve weather data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error fetching weather data: {str(e)}")
        raise DatabaseError(f"Error processing weather data: {str(e)}")

def get_weather_for_location(event_name: str, session_time: str) -> Optional[Dict[str, Any]]:
    """
    Get weather for a known F1 circuit location and a specific session time, converting from UTC to local time.

    Parameters:
    - event_name: Name of the F1 Grand Prix (e.g., "United States Grand Prix")
    - session_time: Exact session time in ISO format (YYYY-MM-DDTHH:MM:SS) in UTC.

    Returns:
    - Weather data dictionary or None if location not found
    
    Raises:
    - ValidationError: If event_name or session_time is invalid
    - ResourceNotFoundError: If the event location is not found
    - ExternalServiceError: If there's an issue with the weather API
    - DatabaseError: For any other error
    """
    if not event_name:
        raise ValidationError("Event name cannot be empty")
    if not session_time:
        raise ValidationError("Session time cannot be empty")
    
    try:
        locations = {
            "Australian Grand Prix": {"coords": (-37.8497, 144.9680), "timezone": "Australia/Melbourne"},
            "Bahrain Grand Prix": {"coords": (26.0325, 50.5106), "timezone": "Asia/Bahrain"},
            "Saudi Arabian Grand Prix": {"coords": (21.6319, 39.1044), "timezone": "Asia/Riyadh"},
            "Chinese Grand Prix": {"coords": (31.3389, 121.2198), "timezone": "Asia/Shanghai"},
            "Miami Grand Prix": {"coords": (25.9581, -80.2389), "timezone": "America/New_York"},
            "United States Grand Prix": {"coords": (30.1328, -97.6411), "timezone": "America/Chicago"},
            "Las Vegas Grand Prix": {"coords": (36.1147, -115.1728), "timezone": "America/Los_Angeles"},
            "Emilia Romagna Grand Prix": {"coords": (44.3439, 11.7167), "timezone": "Europe/Rome"},
            "Monaco Grand Prix": {"coords": (43.7347, 7.4206), "timezone": "Europe/Monaco"},
            "Canadian Grand Prix": {"coords": (45.5017, -73.5673), "timezone": "America/Toronto"},
            "Spanish Grand Prix": {"coords": (41.5700, 2.2611), "timezone": "Europe/Madrid"},
            "Austrian Grand Prix": {"coords": (47.2197, 14.7647), "timezone": "Europe/Vienna"},
            "British Grand Prix": {"coords": (52.0786, -1.0169), "timezone": "Europe/London"},
            "Hungarian Grand Prix": {"coords": (47.5830, 19.2526), "timezone": "Europe/Budapest"},
            "Belgian Grand Prix": {"coords": (50.4372, 5.9719), "timezone": "Europe/Brussels"},
            "Dutch Grand Prix": {"coords": (52.3888, 4.5454), "timezone": "Europe/Amsterdam"},
            "Azerbaijan Grand Prix": {"coords": (40.3724, 49.8533), "timezone": "Asia/Baku"},
            "Singapore Grand Prix": {"coords": (1.2914, 103.8647), "timezone": "Asia/Singapore"},
            "Mexican Grand Prix": {"coords": (19.4042, -99.0907), "timezone": "America/Mexico_City"},
            "São Paulo Grand Prix": {"coords": (-23.7014, -46.6969), "timezone": "America/Sao_Paulo"},
            "Abu Dhabi Grand Prix": {"coords": (24.4672, 54.6031), "timezone": "Asia/Dubai"},
            "Qatar Grand Prix": {"coords": (25.4710, 51.4549), "timezone": "Asia/Qatar"},
        }

        if event_name not in locations:
            logger.warning(f"Event '{event_name}' not found in predefined locations.")
            raise ResourceNotFoundError(
                resource_type="Event location", 
                identifier=event_name
            )

        lat, lon = locations[event_name]["coords"]
        local_timezone = locations[event_name]["timezone"]

        # Convert session_time (UTC) to local track time
        try:
            utc_time = datetime.fromisoformat(session_time.replace('Z', '+00:00')).replace(tzinfo=pytz.utc)
            local_time = utc_time.astimezone(pytz.timezone(local_timezone))

            # Convert local time back to ISO format string for weather API
            local_session_time = local_time.isoformat()
        except ValueError as e:
            raise ValidationError(f"Invalid session time format: {str(e)}")

        logger.info(f"Fetching weather for {event_name} at {local_session_time} (Local Time) [Lat: {lat}, Lon: {lon}]")

        return get_track_weather(lat, lon)
    
    except (ValidationError, ResourceNotFoundError, ExternalServiceError):
        # Re-raise these specific errors
        raise
    except Exception as e:
        logger.error(f"Error in get_weather_for_location: {str(e)}")
        raise DatabaseError(f"Error processing location weather data: {str(e)}")