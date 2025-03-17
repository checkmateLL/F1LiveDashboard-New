import threading
import time
import logging
import redis
import json
import requests
import random  # For demo data
from datetime import datetime

from backend.config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_DECODE_RESPONSES,
    REDIS_PASSWORD,
    WEATHER_SERVICE_URL,
    WEATHER_LATITUDE,
    WEATHER_LONGITUDE
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class RedisLiveDataService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=REDIS_DECODE_RESPONSES,
            ssl=True  # using 'rediss'
        )
        self._polling_thread = None
        self._stop_event = threading.Event()
        self._current_event = None
        self._current_session = None
        self._race_status = None

    def start_polling(self):
        if self._polling_thread is None or not self._polling_thread.is_alive():
            self._stop_event.clear()
            self._polling_thread = threading.Thread(target=self._poll, daemon=True)
            self._polling_thread.start()
            logger.info("Started live data polling thread.")

    def stop_polling(self):
        self._stop_event.set()
        if self._polling_thread:
            self._polling_thread.join()
            logger.info("Stopped live data polling thread.")

    def _poll(self):
        """Poll for live data and update Redis."""
        while not self._stop_event.is_set():
            try:
                # Simulate live session (in a real implementation, this would poll from the F1 API)
                # For now, 30% chance of a live session
                is_live = random.random() < 0.3
                
                if is_live:
                    # Get current simulated event/session
                    if not self._current_event:
                        self._update_current_event()
                    
                    if not self._current_session:
                        self._update_current_session()
                    
                    # Update race status
                    self._update_race_status()
                    
                    # Update and store live data
                    self._update_session_data()
                    self._update_live_timing()
                    self._update_live_standings()
                    self._update_tire_data()
                else:
                    # Clear any existing live session data
                    self._clear_live_data()
                
                # Update weather data regardless of live status
                self._update_weather_data()
                
                # Sleep before next poll
                time.sleep(10)  # Poll every 10 seconds
                
            except Exception as e:
                logger.error(f"Error during live data polling: {e}")
                time.sleep(30)  # Longer delay after an error

    def _update_current_event(self):
        """Simulate selecting a current F1 event."""
        # In a real implementation, this would fetch the current event from F1 API
        # For demo, use a random event from a predefined list
        current_year = datetime.now().year
        events = [
            {"id": 1, "round_number": random.randint(1, 24), "year": current_year, 
            "event_name": "Monaco Grand Prix", "country": "Monaco", "location": "Monte Carlo"},
            {"id": 2, "round_number": random.randint(1, 24), "year": current_year,
            "event_name": "British Grand Prix", "country": "United Kingdom", "location": "Silverstone"},
            {"id": 3, "round_number": random.randint(1, 24), "year": current_year,
            "event_name": "Italian Grand Prix", "country": "Italy", "location": "Monza"},
            {"id": 4, "round_number": random.randint(1, 24), "year": current_year,
            "event_name": "Singapore Grand Prix", "country": "Singapore", "location": "Marina Bay"},
            {"id": 5, "round_number": random.randint(1, 24), "year": current_year,
            "event_name": "United States Grand Prix", "country": "United States", "location": "Austin"}
        ]
        self._current_event = random.choice(events)
        
        # Store in Redis
        self.redis_client.set("current_event", json.dumps(self._current_event))
        logger.info(f"Updated current event: {self._current_event['event_name']}")

    def _update_current_session(self):
        """Simulate selecting a current F1 session."""
        # In a real implementation, this would fetch the current session from F1 API
        session_types = ["Practice 1", "Practice 2", "Practice 3", "Qualifying", "Race"]
        session_type = random.choice(session_types)
        
        self._current_session = {
            "id": random.randint(100, 999),
            "name": session_type,
            "event_id": self._current_event["id"] if self._current_event else None,
            "event_name": self._current_event["event_name"] if self._current_event else "Unknown Event",
            "is_live": True,
            "session_type": session_type.lower().replace(" ", "_"),
            "year": datetime.now().year
        }
        
        # Add race-specific fields
        if session_type == "Race":
            self._current_session.update({
                "total_laps": random.randint(50, 78),
                "current_lap": random.randint(1, 50),
                "remaining_laps": random.randint(1, 30)
            })
        
        # Store in Redis
        self.redis_client.set("live_session", json.dumps(self._current_session))
        logger.info(f"Updated current session: {self._current_session['name']}")