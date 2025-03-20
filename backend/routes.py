from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging
import requests
import fastf1

from backend.models import (
    EventModel, SessionModel, TeamModel, DriverModel, StandingModel,
    TeamStandingModel, ResultModel, WeatherModel
)
from backend.data_service import F1DataService
from backend.error_handling import ValidationError, ResourceNotFoundError, DatabaseError, ExternalServiceError
from backend.weather import get_track_weather, get_weather_for_location

# Get logger
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# Define dependency
def get_data_service() -> F1DataService:
    # This will be replaced by a proper dependency in main.py
    pass

@router.get("/")
async def root():
    return {"message": "Welcome to the F1 Data API"}

@router.get("/years", response_model=List[int])
async def get_years(data_service: F1DataService = Depends(get_data_service)):
    try:
        years = data_service.get_available_years()
        if not years:
            logger.warning("No years available in the database")
        return years
    except Exception as e:
        logger.error(f"Error retrieving years: {e}")
        raise DatabaseError(f"Failed to retrieve years: {str(e)}")

@router.get("/events/{year}", response_model=List[EventModel])
async def get_events(year: int, data_service: F1DataService = Depends(get_data_service)):
    if year <= 0:
        raise ValidationError("Year must be a positive integer")
        
    try:
        events = data_service.get_events(year)
        if not events:
            logger.warning(f"No events found for year {year}")
        return events
    except Exception as e:
        logger.error(f"Error retrieving events for year {year}: {e}")
        raise DatabaseError(f"Failed to retrieve events for year {year}: {str(e)}")

@router.get("/event/{year}/{round_number}", response_model=EventModel)
async def get_event(year: int, round_number: int, data_service: F1DataService = Depends(get_data_service)):
    # Input validation
    if year <= 0:
        raise ValidationError("Year must be a positive integer")
    if round_number <= 0:
        raise ValidationError("Round number must be a positive integer")
        
    event = data_service.get_event(year, round_number)
    if not event:
        raise ResourceNotFoundError(
            resource_type="Event", 
            identifier=f"year={year}, round={round_number}"
        )
    return event

@router.get("/api/event_schedule/{event_id}")
def get_event_schedule(event_id: int):
    if event_id <= 0:
        raise ValidationError("Event ID must be a positive integer")
        
    try:
        event = fastf1.get_event(2025, event_id)
        schedule = [
            {"id": i+1, "name": event[f"Session{i+1}"], "start_time": event[f"Session{i+1}DateUtc"], "type": event[f"Session{i+1}"]}
            for i in range(5) if event[f"Session{i+1}"]
        ]
        return {"sessions": schedule}
    except Exception as e:
        logger.error(f"Error retrieving event schedule for event ID {event_id}: {e}")
        raise DatabaseError(f"Failed to retrieve event schedule: {str(e)}")

@router.get("/api/weather/{event_name}/{session_time}")
def get_weather(event_name: str, session_time: str):
    if not event_name:
        raise ValidationError("Event name must not be empty")
    if not session_time:
        raise ValidationError("Session time must not be empty")
        
    try:
        weather_data = get_weather_for_location(event_name, session_time)
        if not weather_data:
            raise ResourceNotFoundError(resource_type="Weather data", identifier=f"event={event_name}")
        return weather_data
    except Exception as e:
        logger.error(f"Error retrieving weather for event {event_name}: {e}")
        raise DatabaseError(f"Failed to retrieve weather: {str(e)}")

@router.get("/sessions/{event_id}", response_model=List[SessionModel])
async def get_sessions(event_id: int, data_service: F1DataService = Depends(get_data_service)):
    if event_id <= 0:
        raise ValidationError("Event ID must be a positive integer")
        
    try:
        sessions = data_service.get_sessions(event_id)
        if not sessions:
            logger.warning(f"No sessions found for event ID {event_id}")
        return sessions
    except Exception as e:
        logger.error(f"Error retrieving sessions for event ID {event_id}: {e}")
        raise DatabaseError(f"Failed to retrieve sessions: {str(e)}")

@router.get("/teams/{year}", response_model=List[TeamModel])
async def get_teams(year: int, data_service: F1DataService = Depends(get_data_service)):
    if year <= 0:
        raise ValidationError("Year must be a positive integer")
        
    try:
        teams = data_service.get_teams(year)
        if not teams:
            logger.warning(f"No teams found for year {year}")
        return teams
    except Exception as e:
        logger.error(f"Error retrieving teams for year {year}: {e}")
        raise DatabaseError(f"Failed to retrieve teams: {str(e)}")

@router.get("/drivers/{year}", response_model=List[DriverModel])
async def get_drivers(
    year: int,
    team_id: Optional[int] = None,
    data_service: F1DataService = Depends(get_data_service)
):
    if year <= 0:
        raise ValidationError("Year must be a positive integer")
    if team_id is not None and team_id <= 0:
        raise ValidationError("Team ID must be a positive integer")
        
    try:
        drivers = data_service.get_drivers(year, team_id)
        if not drivers:
            logger.warning(f"No drivers found for year {year}" + (f" and team ID {team_id}" if team_id else ""))
        return drivers
    except Exception as e:
        logger.error(f"Error retrieving drivers for year {year}: {e}")
        raise DatabaseError(f"Failed to retrieve drivers: {str(e)}")

@router.get("/standings/drivers/{year}", response_model=List[StandingModel])
async def get_driver_standings(year: int, data_service: F1DataService = Depends(get_data_service)):
    if year <= 0:
        raise ValidationError("Year must be a positive integer")
        
    try:
        standings = data_service.get_driver_standings(year)
        if not standings:
            logger.warning(f"No driver standings found for year {year}")
        return standings
    except Exception as e:
        logger.error(f"Error retrieving driver standings for year {year}: {e}")
        raise DatabaseError(f"Failed to retrieve driver standings: {str(e)}")

@router.get("/standings/constructors/{year}", response_model=List[TeamStandingModel])
async def get_constructor_standings(year: int, data_service: F1DataService = Depends(get_data_service)):
    if year <= 0:
        raise ValidationError("Year must be a positive integer")
        
    try:
        standings = data_service.get_constructor_standings(year)
        if not standings:
            logger.warning(f"No constructor standings found for year {year}")
        return standings
    except Exception as e:
        logger.error(f"Error retrieving constructor standings for year {year}: {e}")
        raise DatabaseError(f"Failed to retrieve constructor standings: {str(e)}")

@router.get("/results/{session_id}", response_model=List[ResultModel])
async def get_race_results(session_id: int, data_service: F1DataService = Depends(get_data_service)):
    if session_id <= 0:
        raise ValidationError("Session ID must be a positive integer")
        
    try:
        results = data_service.get_race_results(session_id)
        if not results:
            logger.warning(f"No race results found for session ID {session_id}")
        return results
    except Exception as e:
        logger.error(f"Error retrieving race results for session ID {session_id}: {e}")
        raise DatabaseError(f"Failed to retrieve race results: {str(e)}")

@router.get("/laps/{session_id}")
async def get_lap_times(
    session_id: int, 
    driver_id: Optional[int] = None,
    data_service: F1DataService = Depends(get_data_service)
):
    if session_id <= 0:
        raise ValidationError("Session ID must be a positive integer")
    if driver_id is not None and driver_id <= 0:
        raise ValidationError("Driver ID must be a positive integer")
        
    try:
        df = data_service.get_lap_times(session_id, driver_id)
        if df.empty:
            logger.warning(f"No lap times found for session ID {session_id}" + (f" and driver ID {driver_id}" if driver_id else ""))
            return []
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error retrieving lap times for session ID {session_id}: {e}")
        raise DatabaseError(f"Failed to retrieve lap times: {str(e)}")

@router.get("/telemetry/{session_id}/{driver_id}/{lap_number}")
async def get_telemetry(
    session_id: int,
    driver_id: int,
    lap_number: int,
    data_service: F1DataService = Depends(get_data_service)
):
    if session_id <= 0:
        raise ValidationError("Session ID must be a positive integer")
    if driver_id <= 0:
        raise ValidationError("Driver ID must be a positive integer")
    if lap_number <= 0:
        raise ValidationError("Lap number must be a positive integer")
        
    try:
        df = data_service.get_telemetry(session_id, driver_id, lap_number)
        if df.empty:
            logger.warning(f"No telemetry data found for session ID {session_id}, driver ID {driver_id}, lap number {lap_number}")
            return []
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error retrieving telemetry for session ID {session_id}, driver ID {driver_id}, lap number {lap_number}: {e}")
        raise DatabaseError(f"Failed to retrieve telemetry data: {str(e)}")
    
@router.get("/weather/current", response_model=dict)
async def fetch_current_weather():
    """
    Get real-time weather data for the default track location.
    Uses caching to avoid excessive API calls.
    """
    try:
        return get_track_weather()
    except ExternalServiceError as e:
        logger.error(f"External weather service error: {e}")
        raise HTTPException(status_code=502, detail=e.to_dict())
    except DatabaseError as e:
        logger.error(f"Database error while fetching weather: {e}")
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Unexpected error fetching weather: {e}")
        raise HTTPException(status_code=500, detail={"error": "Internal server error"})

# ✅ New endpoint: Fetch weather for a specific event & session time
@router.get("/weather/{event_name}/{session_time}", response_model=dict)
async def fetch_weather_for_event(event_name: str, session_time: str):
    """
    Fetch weather data for a specific race event and session time.
    :param event_name: Name of the event (e.g., "Monza GP").
    :param session_time: Timestamp in ISO format (e.g., "2025-06-15T14:00:00Z").
    :return: Weather data.
    """
    try:
        return get_weather_for_location(event_name, session_time)
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=e.to_dict())
    except ExternalServiceError as e:
        logger.error(f"Weather API error: {e}")
        raise HTTPException(status_code=502, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Unexpected error fetching event weather: {e}")
        raise HTTPException(status_code=500, detail={"error": "Internal server error"})    