import requests
import logging
from typing import Dict, Any, Optional
import json
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_track_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Fetch live track weather using Open-Meteo API.
    
    Parameters:
    - latitude: The latitude of the track location
    - longitude: The longitude of the track location
    
    Returns:
    - Dictionary containing weather data
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": "true",
            "hourly": "temperature_2m,relativehumidity_2m,precipitation,cloudcover,windspeed_10m",
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        data = response.json()
        
        # Extract current weather
        current = data.get("current_weather", {})
        
        # Calculate track temperature (typically higher than air temperature)
        track_temp = current.get("temperature") + 8.0 if "temperature" in current else None
        
        # Get hourly data for the current hour
        hourly = data.get("hourly", {})
        current_index = 0
        
        if "time" in hourly and hourly["time"]:
            try:
                # Find index of current hour
                current_hour = current.get("time", "").split("T")[1][:2]
                for i, time in enumerate(hourly["time"]):
                    if time.endswith(f"T{current_hour}:00"):
                        current_index = i
                        break
            except (IndexError, KeyError):
                pass
        
        # Combine data
        weather_data = {
            "temperature": current.get("temperature"),
            "track_temperature": track_temp,
            "wind_speed": current.get("windspeed"),
            "wind_direction": current.get("winddirection"),
            "humidity": hourly.get("relativehumidity_2m", [])[current_index] if "relativehumidity_2m" in hourly else None,
            "rainfall": bool(hourly.get("precipitation", [])[current_index] > 0) if "precipitation" in hourly else False,
            "weather_code": current.get("weathercode"),
            "cloud_cover": hourly.get("cloudcover", [])[current_index] if "cloudcover" in hourly else None,
            "is_day": current.get("is_day"),
            "time": current.get("time")
        }
        
        return weather_data
    
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        # Return fallback weather data
        return {
            "temperature": 25.0,
            "track_temperature": 32.0,
            "wind_speed": 10.0,
            "wind_direction": 180,
            "humidity": 60.0,
            "rainfall": False,
            "weather_code": 0,  # Clear sky
            "cloud_cover": 0,
            "is_day": 1,
            "time": None
        }

def get_weather_for_location(location: str) -> Optional[Dict[str, Any]]:
    """
    Get weather for a known F1 circuit location.
    
    Parameters:
    - location: Name of the circuit location (e.g., "Melbourne", "Monaco")
    
    Returns:
    - Weather data dictionary or None if location not found
    """
    # Map of F1 locations to coordinates
    locations = {
        "Melbourne": (-37.8497, 144.9680),
        "Sakhir": (26.0325, 50.5106),
        "Jeddah": (21.6319, 39.1044),
        "Shanghai": (31.3389, 121.2198),
        "Miami": (25.9581, -80.2389),
        "Imola": (44.3439, 11.7167),
        "Monaco": (43.7347, 7.4206),
        "Montreal": (45.5017, -73.5673),
        "Barcelona": (41.5700, 2.2611),
        "Spielberg": (47.2197, 14.7647),
        "Silverstone": (52.0786, -1.0169),
        "Budapest": (47.5830, 19.2526),
        "Spa": (50.4372, 5.9719),
        "Zandvoort": (52.3888, 4.5454),
        "Monza": (45.6156, 9.2811),
        "Baku": (40.3724, 49.8533),
        "Singapore": (1.2914, 103.8647),
        "Austin": (30.1328, -97.6411),
        "Mexico City": (19.4042, -99.0907),
        "São Paulo": (-23.7014, -46.6969),
        "Las Vegas": (36.1147, -115.1728),
        "Lusail": (25.4710, 51.4549),
        "Yas Marina": (24.4672, 54.6031)
    }
    
    if location in locations:
        lat, lon = locations[location]
        return get_track_weather(lat, lon)
    
    return None