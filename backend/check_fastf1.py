import fastf1
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Enable cache
try:
    fastf1.Cache.enable_cache("./.fastf1_cache")
except Exception as e:
    logger.warning(f"Could not enable cache: {e}")

# Check for data availability
def check_session(year, round_num, session_name):
    logger.info(f"Checking data for {year} R{round_num} {session_name}")
    
    try:
        # Get the session
        session = fastf1.get_session(year, round_num, session_name)
        logger.info(f"Session found: {session.name}, Date: {session.date}")
        
        # Try to load data
        logger.info("Loading session data (this may take a moment)...")
        try:
            session.load(laps=True, telemetry=False, weather=True)
            logger.info("Session data loaded successfully")
            
            # Check what's available
            if hasattr(session, 'results') and session.results is not None and not session.results.empty:
                logger.info(f"Results available for {len(session.results)} drivers")
            else:
                logger.warning("Results not available")
                
            if hasattr(session, 'laps') and session.laps is not None and not session.laps.empty:
                logger.info(f"Lap data available - {len(session.laps)} laps")
                
                # Get fastest lap as a sample
                try:
                    fastest = session.laps.pick_fastest()
                    logger.info(f"Fastest lap: {fastest['Driver']} - {fastest['LapTime']}")
                except Exception as e:
                    logger.warning(f"Could not get fastest lap: {e}")
            else:
                logger.warning("Lap data not available")
                
            if hasattr(session, 'weather_data') and session.weather_data is not None and not session.weather_data.empty:
                logger.info(f"Weather data available - {len(session.weather_data)} data points")
            else:
                logger.warning("Weather data not available")
                
        except Exception as e:
            logger.error(f"Could not load session data: {e}")
            
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        
    logger.info("-" * 50)

if __name__ == "__main__":
    # Check today's Sprint
    check_session(2025, 3, "Race")
    
    # Also check the Sprint Qualifying for comparison
    check_session(2025, 2, "Sprint Qualifying")
    
    # And check the qualifying session that did work
    check_session(2025, 3, "Race")