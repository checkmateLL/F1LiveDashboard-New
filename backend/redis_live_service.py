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

    def _update_race_status(self):
        """Update the race status data (flags, safety car, etc.)"""
        if not self._current_session:
            return
        
        status_options = ["GREEN", "YELLOW", "SAFETY CAR", "RED", "VIRTUAL SAFETY CAR"]
        weights = [0.7, 0.15, 0.1, 0.03, 0.02]  # Probabilities of each status
        
        # Either keep the current status or generate a new one
        if self._race_status and random.random() < 0.9:  # 90% chance to keep current status
            status = self._race_status.get("status")
        else:
            status = random.choices(status_options, weights=weights)[0]
            
            # If yellow flag, determine which sector
            sector = None
            if status == "YELLOW":
                sector = random.randint(1, 3)
                status = f"YELLOW - Sector {sector}"
                
        # DRS status - enabled only if track status is GREEN
        drs_enabled = (status == "GREEN" and random.random() < 0.9)
        
        self._race_status = {
            "status": status,
            "drs_enabled": drs_enabled,
            "timestamp": time.time()
        }
        
        # Store in Redis
        self.redis_client.set("track_status", json.dumps(self._race_status))

    def _update_session_data(self):
        """Update session-specific data."""
        if not self._current_session:
            return
            
        # Update current lap for races
        if self._current_session.get("session_type") == "race":
            current_lap = self._current_session.get("current_lap", 1)
            total_laps = self._current_session.get("total_laps", 78)
            
            # Increment lap counter with 30% probability (to simulate slow updates)
            if random.random() < 0.3 and current_lap < total_laps:
                current_lap += 1
                
            self._current_session["current_lap"] = current_lap
            self._current_session["remaining_laps"] = total_laps - current_lap
            
            # Store updated session
            self.redis_client.set("live_session", json.dumps(self._current_session))
            
            # Generate events
            if random.random() < 0.2:  # 20% chance of new event
                self._generate_race_event(current_lap)

    def _generate_race_event(self, current_lap):
        """Generate a random race event (pit stop, fastest lap, etc.)"""
        # Driver codes
        drivers = ["HAM", "VER", "BOT", "PER", "LEC", "SAI", "NOR", "RIC", "ALO", "OCO"]
        
        # Event types
        event_types = [
            "PIT_STOP", "FASTEST_LAP", "INCIDENT", "TEAM_RADIO", "PENALTY", "OFF_TRACK"
        ]
        
        event_type = random.choice(event_types)
        driver = random.choice(drivers)
        
        event = {
            "type": event_type,
            "driver": driver,
            "lap": current_lap,
            "timestamp": time.time(),
            "text": self._generate_event_text(event_type, driver, current_lap)
        }
        
        # Store in a Redis list
        self.redis_client.lpush("race_events", json.dumps(event))
        # Keep only the latest 20 events
        self.redis_client.ltrim("race_events", 0, 19)

    def _generate_event_text(self, event_type, driver, lap):
        """Generate descriptive text for race events."""
        if event_type == "PIT_STOP":
            compound = random.choice(["Soft", "Medium", "Hard"])
            pit_time = round(random.uniform(1.8, 4.5), 1)
            return f"{driver} pits for {compound} tires - {pit_time}s stop"
        
        elif event_type == "FASTEST_LAP":
            minutes = 1
            seconds = round(random.uniform(10, 45), 3)
            return f"{driver} sets fastest lap - {minutes}:{seconds:.3f}"
        
        elif event_type == "INCIDENT":
            other_driver = "VER" if driver != "VER" else "HAM"
            incident = random.choice(["contact with", "battling with", "overtakes"])
            return f"{driver} {incident} {other_driver}"
        
        elif event_type == "TEAM_RADIO":
            messages = [
                f"{driver}: 'Tires are gone'",
                f"{driver}: 'Car feels good'",
                f"Engineer to {driver}: 'Push now'",
                f"{driver}: 'Blue flags!'",
                f"Engineer to {driver}: 'Box this lap, box this lap'"
            ]
            return random.choice(messages)
        
        elif event_type == "PENALTY":
            penalty = random.choice(["5 second", "10 second", "drive-through"])
            reason = random.choice(["track limits", "unsafe release", "causing a collision"])
            return f"{driver} receives {penalty} penalty for {reason}"
        
        elif event_type == "OFF_TRACK":
            return f"{driver} goes off track at Turn {random.randint(1, 20)}"
        
        return f"{driver} - Event on lap {lap}"

    def _update_live_timing(self):
        """Generate and update live timing data."""
        if not self._current_session:
            return
            
        # Team and driver data
        teams = {
            "Mercedes": {"color": "#00D2BE", "drivers": ["HAM", "RUS"]},
            "Red Bull": {"color": "#0600EF", "drivers": ["VER", "PER"]},
            "Ferrari": {"color": "#DC0000", "drivers": ["LEC", "SAI"]},
            "McLaren": {"color": "#FF8700", "drivers": ["NOR", "PIA"]},
            "Aston Martin": {"color": "#006F62", "drivers": ["ALO", "STR"]},
            "Alpine": {"color": "#0090FF", "drivers": ["GAS", "OCO"]},
            "Williams": {"color": "#005AFF", "drivers": ["ALB", "SAR"]},
            "RB": {"color": "#2B4562", "drivers": ["TSU", "RIC"]},
            "Stake F1": {"color": "#900000", "drivers": ["BOT", "ZHO"]},
            "Haas": {"color": "#FFFFFF", "drivers": ["HUL", "BEA"]}
        }
        
        # Create timing data
        timing_data = []
        
        # Create a shuffled list of positions, but favor top teams
        position_order = []
        top_drivers = ["VER", "HAM", "LEC", "NOR"]
        
        # 70% chance top drivers are in top positions
        if random.random() < 0.7:
            random.shuffle(top_drivers)
            position_order.extend(top_drivers)
        
        # Add remaining drivers
        all_drivers = []
        for team_data in teams.values():
            all_drivers.extend(team_data["drivers"])
            
        remaining_drivers = [d for d in all_drivers if d not in position_order]
        random.shuffle(remaining_drivers)
        position_order.extend(remaining_drivers)
        
        # Generate timing data for each driver
        for position, driver_code in enumerate(position_order, 1):
            # Find team for this driver
            team_name = None
            team_color = None
            for team, data in teams.items():
                if driver_code in data["drivers"]:
                    team_name = team
                    team_color = data["color"]
                    break
            
            # Create timing entry
            gap = f"+{round(random.uniform(0, 60), 3)}s" if position > 1 else "Leader"
            interval = f"+{round(random.uniform(0, 5), 3)}s" if position > 1 else "-"
            
            # Last lap time
            minutes = 1
            seconds = round(random.uniform(10, 45), 3)
            last_lap = f"{minutes}:{seconds:.3f}"
            
            # Determine driver status
            status_options = ["On Track", "In Pit", "Out", "Retired"]
            status_weights = [0.9, 0.05, 0.03, 0.02]
            status = random.choices(status_options, status_weights)[0]
            
            # Tire compound
            tire_options = ["S", "M", "H", "I", "W"]
            tire_weights = [0.3, 0.4, 0.2, 0.05, 0.05]
            tire = random.choices(tire_options, tire_weights)[0]
            
            # Tire age
            tire_age = random.randint(1, 30) if status == "On Track" else "-"
            
            timing_data.append({
                "Position": position,
                "DriverCode": driver_code,
                "Team": team_name,
                "Gap": gap,
                "Interval": interval,
                "LastLap": last_lap,
                "Status": status,
                "Tire": tire,
                "TireAge": tire_age,
                "TeamColor": team_color
            })
        
        # Store timing data in Redis
        self.redis_client.set("live_timing", json.dumps(timing_data))

    def _update_live_standings(self):
        """Generate and update live championship standings."""
        if not self._current_session:
            return
            
        # Team and driver data
        teams = {
            "Mercedes": {"color": "#00D2BE", "drivers": [
                {"code": "HAM", "name": "Lewis Hamilton"},
                {"code": "RUS", "name": "George Russell"}
            ]},
            "Red Bull": {"color": "#0600EF", "drivers": [
                {"code": "VER", "name": "Max Verstappen"},
                {"code": "PER", "name": "Sergio Pérez"}
            ]},
            "Ferrari": {"color": "#DC0000", "drivers": [
                {"code": "LEC", "name": "Charles Leclerc"},
                {"code": "SAI", "name": "Carlos Sainz"}
            ]},
            "McLaren": {"color": "#FF8700", "drivers": [
                {"code": "NOR", "name": "Lando Norris"},
                {"code": "PIA", "name": "Oscar Piastri"}
            ]},
            "Aston Martin": {"color": "#006F62", "drivers": [
                {"code": "ALO", "name": "Fernando Alonso"},
                {"code": "STR", "name": "Lance Stroll"}
            ]},
            "Alpine": {"color": "#0090FF", "drivers": [
                {"code": "GAS", "name": "Pierre Gasly"},
                {"code": "OCO", "name": "Esteban Ocon"}
            ]},
            "Williams": {"color": "#005AFF", "drivers": [
                {"code": "ALB", "name": "Alexander Albon"},
                {"code": "SAR", "name": "Logan Sargeant"}
            ]},
            "RB": {"color": "#2B4562", "drivers": [
                {"code": "TSU", "name": "Yuki Tsunoda"},
                {"code": "RIC", "name": "Daniel Ricciardo"}
            ]},
            "Stake F1": {"color": "#900000", "drivers": [
                {"code": "BOT", "name": "Valtteri Bottas"},
                {"code": "ZHO", "name": "Zhou Guanyu"}
            ]},
            "Haas": {"color": "#FFFFFF", "drivers": [
                {"code": "HUL", "name": "Nico Hülkenberg"},
                {"code": "BEA", "name": "Oliver Bearman"}
            ]}
        }
        
        # Generate standings data
        driver_standings = []
        team_standings = []
        
        # Base points distribution with some randomness
        base_points = [300, 280, 250, 220, 190, 160, 130, 100, 80, 60, 50, 40, 30, 20, 15, 10, 5, 3, 2, 1]
        
        # Shuffle team performance rankings
        performance_order = list(teams.keys())
        random.shuffle(performance_order)
        
        # Team standings
        for i, team_name in enumerate(performance_order):
            team_data = teams[team_name]
            points_base = base_points[min(i, len(base_points)-1)]
            points = points_base + random.randint(-20, 20)  # Add some randomness
            points = max(0, points)  # Ensure non-negative
            
            team_standings.append({
                "position": i + 1,
                "team_name": team_name,
                "team_color": team_data["color"],
                "points": points
            })
        
        # Driver standings - based on team performance with some individual variation
        driver_list = []
        for team_name, team_data in teams.items():
            team_position = next(i for i, team in enumerate(team_standings) if team["team_name"] == team_name)
            team_points = team_standings[team_position]["points"]
            
            # Split points between drivers (not exactly even)
            for driver in team_data["drivers"]:
                # Base on team points but add individual variation
                driver_points = (team_points / 2) + random.randint(-30, 30)
                driver_points = max(0, round(driver_points))
                
                driver_list.append({
                    "driver_code": driver["code"],
                    "driver_name": driver["name"],
                    "team": team_name,
                    "team_color": team_data["color"],
                    "points": driver_points
                })
        
        # Sort drivers by points
        driver_list.sort(key=lambda x: x["points"], reverse=True)
        
        # Add position
        for i, driver in enumerate(driver_list):
            driver["position"] = i + 1
            driver_standings.append(driver)
        
        # Store standings in Redis
        self.redis_client.set("live_driver_standings", json.dumps(driver_standings))
        self.redis_client.set("live_team_standings", json.dumps(team_standings))    

    def _update_tire_data(self):
        """Generate and update tire usage data."""
        if not self._current_session:
            return
            
        # Driver codes
        drivers = ["HAM", "VER", "BOT", "PER", "LEC", "SAI", "NOR", "RIC", "ALO", "OCO"]
        
        # Tire compounds
        compounds = ["S", "M", "H", "I", "W"]
        
        tire_data = {}
        
        for driver in drivers:
            # Generate a plausible tire strategy
            available_tires = ["S", "M", "H"]  # Normal race conditions
            
            # 20% chance of rain affecting tire choices
            if random.random() < 0.2:
                available_tires.extend(["I", "W"])
            
            # Random strategy with 1-3 different compounds
            num_compounds = random.randint(1, min(3, len(available_tires)))
            strategy = random.sample(available_tires, num_compounds)
            
            # Generate stint lengths for each compound
            stints = []
            for compound in strategy:
                stint_length = random.randint(10, 30)
                stints.append({
                    "compound": compound,
                    "laps": stint_length
                })
            
            tire_data[driver] = {
                "stints": stints,
                "current_compound": stints[-1]["compound"] if stints else "M",
                "current_age": random.randint(1, stints[-1]["laps"]) if stints else 1
            }
        
        # Store tire data in Redis
        self.redis_client.set("live_tires", json.dumps(tire_data))

    def _update_weather_data(self):
        """Update weather data."""
        try:
            # Try to fetch real weather data from Open-Meteo
            response = requests.get(
                WEATHER_SERVICE_URL,
                params={
                    "latitude": WEATHER_LATITUDE,
                    "longitude": WEATHER_LONGITUDE,
                    "current_weather": "true"
                },
                timeout=5
            )
            
            if response.status_code == 200:
                current_weather = response.json().get("current_weather", {})
                self.redis_client.set("live_weather", json.dumps(current_weather))
            else:
                # Fallback to simulated weather
                self._generate_simulated_weather()
        
        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")
            # Fallback to simulated weather
            self._generate_simulated_weather()

    def _generate_simulated_weather(self):
        """Generate simulated weather data."""
        weather_data = {
            "temperature": round(random.uniform(15, 35), 1),
            "wind_speed": round(random.uniform(0, 30), 1),
            "wind_direction": random.randint(0, 359),
            "weather_code": random.choice([0, 1, 2, 3, 45, 51, 53, 55, 61, 63, 65]),
            "is_day": 1,
            "time": datetime.now().strftime("%Y-%m-%dT%H:%M")
        }
        
        # Additional track data
        weather_data.update({
            "track_temperature": round(weather_data["temperature"] + random.uniform(5, 15), 1),
            "humidity": random.randint(30, 95),
            "rainfall": random.random() < 0.2,  # 20% chance of rain
            "cloud_cover": random.randint(0, 100)
        })
        
        self.redis_client.set("live_weather", json.dumps(weather_data))

    def _clear_live_data(self):
        """Clear all live session data."""
        self._current_event = None
        self._current_session = None
        self._race_status = None
        
        # Update Redis to reflect no live session
        self.redis_client.set("live_session", json.dumps({"is_live": False}))
        
        # Don't clear standings or weather - those persist between sessions    

    def get_live_session(self):
        """Get the current live session data."""
        try:
            data = self.redis_client.get("live_session")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error retrieving live session: {e}")
        return None

    def get_live_standings(self):
        """Get the current championship standings."""
        try:
            data = self.redis_client.get("live_driver_standings")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error retrieving live standings: {e}")
        return None

    def get_live_team_standings(self):
        """Get the current constructor standings."""
        try:
            data = self.redis_client.get("live_team_standings")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error retrieving team standings: {e}")
        return None

    def get_live_weather(self):
        """Get the current weather data."""
        try:
            data = self.redis_client.get("live_weather")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error retrieving live weather: {e}")
        return None

    def get_live_timing(self):
        """Get the current timing data."""
        try:
            data = self.redis_client.get("live_timing")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error retrieving live timing: {e}")
        return []

    def get_live_tires(self):
        """Get the current tire usage data."""
        try:
            data = self.redis_client.get("live_tires")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error retrieving live tires: {e}")
        return {}

    def get_track_status(self):
        """Get the current track status."""
        try:
            data = self.redis_client.get("track_status")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error retrieving track status: {e}")
        return None

    def get_race_events(self, limit=10):
        """Get the most recent race events."""
        try:
            events = self.redis_client.lrange("race_events", 0, limit-1)
            return [json.loads(event) for event in events]
        except Exception as e:
            logger.error(f"Error retrieving race events: {e}")
        return []