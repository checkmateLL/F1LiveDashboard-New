import os
import logging
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Get database path, handling both absolute and relative paths
db_path = os.getenv("SQLITE_DB_PATH")
if db_path and not os.path.isabs(db_path):
    SQLITE_DB_PATH = os.path.join(BASE_DIR, db_path)
else:
    SQLITE_DB_PATH = db_path

print(f"Using database at: {SQLITE_DB_PATH}")

# Required environment variables
REQUIRED_ENV_VARS = [
    "SQLITE_DB_PATH",
    "FASTF1_CACHE_DIR"
]

# Optional environment variables with defaults
OPTIONAL_ENV_VARS = {
    "OPENWEATHER_API_KEY": None,  # Required for weather features
    "REDIS_HOST": None,
    "REDIS_PORT": "13016",
    "REDIS_DB": "0",
    "REDIS_DECODE_RESPONSES": "True",
    "REDIS_PASSWORD": None,
    "REDIS_URL_CORS": None,
    "WEATHER_LATITUDE": "45.620",
    "WEATHER_LONGITUDE": "9.281",
    "WEATHER_SERVICE_URL": "https://api.open-meteo.com/v1/forecast"
}

# Check for missing required environment variables
missing_vars = [var for var in REQUIRED_ENV_VARS if os.getenv(var) is None]

if missing_vars:
    missing_str = ", ".join(missing_vars)
    raise EnvironmentError(f"Missing required environment variables: {missing_str}")

# Resolve path relative to base if not absolute
def resolve_path(env_var: str) -> str:
    path = os.getenv(env_var)
    if path and not os.path.isabs(path):
        return os.path.join(BASE_DIR, path)
    return path

SQLITE_DB_PATH = resolve_path("SQLITE_DB_PATH")
FASTF1_CACHE_DIR = resolve_path("FASTF1_CACHE_DIR")

# Load optional environment variables with defaults
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", OPTIONAL_ENV_VARS["OPENWEATHER_API_KEY"])
REDIS_HOST = os.getenv("REDIS_HOST", OPTIONAL_ENV_VARS["REDIS_HOST"])
REDIS_PORT = int(os.getenv("REDIS_PORT", OPTIONAL_ENV_VARS["REDIS_PORT"]))
REDIS_DB = int(os.getenv("REDIS_DB", OPTIONAL_ENV_VARS["REDIS_DB"]))
REDIS_DECODE_RESPONSES = os.getenv("REDIS_DECODE_RESPONSES", OPTIONAL_ENV_VARS["REDIS_DECODE_RESPONSES"]) == "True"
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", OPTIONAL_ENV_VARS["REDIS_PASSWORD"])
REDIS_URL_CORS = os.getenv("REDIS_URL_CORS", OPTIONAL_ENV_VARS["REDIS_URL_CORS"])
WEATHER_LATITUDE = os.getenv("WEATHER_LATITUDE", OPTIONAL_ENV_VARS["WEATHER_LATITUDE"])
WEATHER_LONGITUDE = os.getenv("WEATHER_LONGITUDE", OPTIONAL_ENV_VARS["WEATHER_LONGITUDE"])
WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", OPTIONAL_ENV_VARS["WEATHER_SERVICE_URL"])

# Log the configuration (excluding sensitive values)
logger.info(f"Configuration Loaded: SQLITE_DB_PATH={SQLITE_DB_PATH}, FASTF1_CACHE_DIR={FASTF1_CACHE_DIR}")
logger.info(f"Weather Service: {WEATHER_SERVICE_URL}, Latitude: {WEATHER_LATITUDE}, Longitude: {WEATHER_LONGITUDE}")

if OPENWEATHER_API_KEY:
    logger.info("Weather API key detected.")
else:
    logger.warning("No OpenWeather API key provided. Weather features may be limited.")

if REDIS_HOST:
    logger.info(f"Using Redis at {REDIS_HOST}:{REDIS_PORT}")
else:
    logger.warning("Redis is not configured. Session state will use local storage.")
