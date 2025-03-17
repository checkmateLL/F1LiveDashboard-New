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