from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import logging

from backend.data_service import F1DataService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI(
    title="F1 Data API",
    description="API for accessing Formula 1 data (both historical and live)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup: create a global data service instance and start live polling.
@app.on_event("startup")
async def startup_event():
    app.state.data_service = F1DataService()
    app.state.data_service.start_live_polling()
    logger.info("Startup: Data service initialized and live polling started.")

# Shutdown: cleanly close connections.
@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "data_service"):
        app.state.data_service.close()
        logger.info("Shutdown: Data service closed.")

def get_data_service() -> F1DataService:
    return app.state.data_service

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

@app.get("/")
async def root():
    return {"message": "Welcome to the F1 Data API"}

@app.get("/years", response_model=List[int])
async def get_years(data_service: F1DataService = Depends(get_data_service)):
    return data_service.get_available_years()

@app.get("/events/{year}", response_model=List[EventModel])
async def get_events(year: int, data_service: F1DataService = Depends(get_data_service)):
    return data_service.get_events(year)

@app.get("/event/{year}/{round_number}", response_model=EventModel)
async def get_event(year: int, round_number: int, data_service: F1DataService = Depends(get_data_service)):
    event = data_service.get_event(year, round_number)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.get("/sessions/{event_id}", response_model=List[SessionModel])
async def get_sessions(event_id: int, data_service: F1DataService = Depends(get_data_service)):
    return data_service.get_sessions(event_id)

@app.get("/teams/{year}", response_model=List[TeamModel])
async def get_teams(year: int, data_service: F1DataService = Depends(get_data_service)):
    return data_service.get_teams(year)

@app.get("/drivers/{year}", response_model=List[DriverModel])
async def get_drivers(
    year: int,
    team_id: Optional[int] = None,
    data_service: F1DataService = Depends(get_data_service)
):
    return data_service.get_drivers(year, team_id)

@app.get("/standings/drivers/{year}", response_model=List[StandingModel])
async def get_driver_standings(year: int, data_service: F1DataService = Depends(get_data_service)):
    return data_service.get_driver_standings(year)

@app.get("/standings/constructors/{year}", response_model=List[TeamStandingModel])
async def get_constructor_standings(year: int, data_service: F1DataService = Depends(get_data_service)):
    return data_service.get_constructor_standings(year)

@app.get("/results/{session_id}", response_model=List[ResultModel])
async def get_race_results(session_id: int, data_service: F1DataService = Depends(get_data_service)):
    return data_service.get_race_results(session_id)

@app.get("/laps/{session_id}")
async def get_lap_times(
    session_id: int, 
    driver_id: Optional[int] = None,
    data_service: F1DataService = Depends(get_data_service)
):
    df = data_service.get_lap_times(session_id, driver_id)
    if df.empty:
        return []
    return df.to_dict(orient="records")

@app.get("/telemetry/{session_id}/{driver_id}/{lap_number}")
async def get_telemetry(
    session_id: int,
    driver_id: int,
    lap_number: int,
    data_service: F1DataService = Depends(get_data_service)
):
    df = data_service.get_telemetry(session_id, driver_id, lap_number)
    if df.empty:
        return []
    return df.to_dict(orient="records")

# Live data endpoints
@app.get("/live/session", response_model=Optional[LiveSessionModel])
async def get_live_session(data_service: F1DataService = Depends(get_data_service)):
    return data_service.get_current_session()

@app.get("/live/timing", response_model=List[LiveTimingEntryModel])
async def get_live_timing(data_service: F1DataService = Depends(get_data_service)):
    if data_service.redis_service:
        return data_service.redis_service.get_live_timing()
    return []

@app.get("/live/weather", response_model=Optional[WeatherModel])
async def get_live_weather(data_service: F1DataService = Depends(get_data_service)):
    if data_service.redis_service:
        return data_service.redis_service.get_live_weather()
    return None

@app.get("/live/track-status", response_model=Optional[TrackStatusModel])
async def get_track_status(data_service: F1DataService = Depends(get_data_service)):
    if data_service.redis_service:
        return data_service.redis_service.get_track_status()
    return None

@app.get("/live/events", response_model=List[RaceEventModel])
async def get_race_events(
    limit: int = Query(10, ge=1, le=50),
    data_service: F1DataService = Depends(get_data_service)
):
    if data_service.redis_service:
        return data_service.redis_service.get_race_events(limit)
    return []

@app.get("/live/tires")
async def get_tire_data(data_service: F1DataService = Depends(get_data_service)):
    if data_service.redis_service:
        return data_service.redis_service.get_live_tires()
    return {}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)