from pydantic import BaseModel
from typing import List, Optional

# Pydantic models for API responses.
class EventModel(BaseModel):
    id: int
    round_number: int
    country: str
    location: str
    official_event_name: str
    event_name: str
    event_date: Optional[str]
    event_format: str
    f1_api_support: bool

class SessionModel(BaseModel):
    id: int
    name: str
    date: Optional[str]
    session_type: str
    total_laps: Optional[int]
    session_start_time: Optional[str]
    t0_date: Optional[str]

class TeamModel(BaseModel):
    id: int
    name: str
    team_id: str
    team_color: str

class DriverModel(BaseModel):
    id: int
    driver_number: str
    broadcast_name: str
    abbreviation: str
    driver_id: str
    first_name: str
    last_name: str
    full_name: str
    headshot_url: Optional[str]
    country_code: str
    team_id: int
    team_name: str
    team_color: str

class StandingModel(BaseModel):
    position: int
    driver_id: int
    driver_name: str
    abbreviation: str
    team: str
    team_color: str
    points: float

class TeamStandingModel(BaseModel):
    position: int
    team_id: int
    team_name: str
    team_color: str
    points: float

class ResultModel(BaseModel):
    position: int
    driver_name: str
    abbreviation: str
    driver_number: str
    team_name: str
    team_color: str
    grid_position: Optional[int]
    points: Optional[float]
    status: Optional[str]
    race_time: Optional[str]

# Weather model
class WeatherModel(BaseModel):
    temperature: Optional[float]
    track_temperature: Optional[float]
    wind_speed: Optional[float]
    wind_direction: Optional[int]
    humidity: Optional[float]
    rainfall: Optional[bool]
    cloud_cover: Optional[int]
    time: Optional[str]