import streamlit as st
import pandas as pd
import time
from datetime import datetime
import sqlite3
import json
import random  # For demo data

from frontend.components.countdown import get_next_event, display_countdown

def live():
    st.title("🔴 Live Race Data")
    
    # Connect to database and Redis for live data
    conn = sqlite3.connect("f1_data_full_2025.db")
    
    try:
        # Get current year
        current_year = datetime.now().year
        
        # Get live session data from backend
        # This would usually come from Redis service
        live_session = get_live_session_data()
        
        # If a live session is active, show live data
        if live_session and live_session.get('is_live', False):
            display_live_session(live_session)
        else:
            # If no live session, show countdown to next event
            events_df = pd.read_sql_query(
                "SELECT id, round_number, country, location, official_event_name, event_name, event_date, event_format "
                "FROM events WHERE year = ? ORDER BY event_date",
                conn,
                params=(current_year,)
            )
            
            # Get the next event
            next_event = get_next_event(events_df)
            
            if next_event:
                st.subheader("Next Session")
                # Get the next session for this event
                event_id = next_event.get('id')
                sessions = pd.read_sql_query(
                    "SELECT name, date, session_type FROM sessions WHERE event_id = ? ORDER BY date",
                    conn,
                    params=(event_id,)
                )
                
                if not sessions.empty:
                    # Convert session dates and find the next one
                    sessions['date_dt'] = pd.to_datetime(sessions['date'], errors='coerce')
                    now = datetime.now()
                    future_sessions = sessions[sessions['date_dt'] > now].sort_values(by='date_dt')
                    
                    if not future_sessions.empty:
                        next_session = future_sessions.iloc[0]
                        st.info(f"Next session: {next_session['name']} - {next_session['date_dt'].strftime('%d %b %Y, %H:%M')}")
                
                # Display countdown
                display_countdown(next_event)
                
                # Show supplementary information
                show_track_info(next_event, conn)
                
    except Exception as e:
        st.error(f"Error loading live data: {e}")
    
    finally:
        conn.close()

def get_live_session_data():
    """
    Fetch live session data from Redis or API service.
    For demo purposes, this returns mock data.
    """
    # In a real implementation, this would connect to Redis
    # For now, return mock data or None
    now = datetime.now()
    
    # Return mock data for demo (50% chance of having a live session)
    if random.random() > 0.5:
        return {
            'is_live': True,
            'session_name': 'Race',
            'event_name': 'Monaco Grand Prix',
            'lap': random.randint(1, 78),
            'total_laps': 78,
            'timestamp': now.timestamp()
        }
    else:
        return {'is_live': False}

def display_live_session(session_data):
    """Display live session data including timing, positions, etc."""
    st.subheader(f"🔴 LIVE: {session_data.get('event_name', 'Unknown Event')} - {session_data.get('session_name', 'Unknown Session')}")
    
    # Progress bar for laps
    current_lap = session_data.get('lap', 0)
    total_laps = session_data.get('total_laps', 1)
    st.progress(current_lap / total_laps)
    st.markdown(f"**Lap {current_lap}/{total_laps}**")
    
    # Create layout with two columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Live timing table
        st.subheader("Live Timing")
        timing_data = generate_mock_timing_data(20)  # Generate mock data for 20 drivers
        
        # Format timing data
        st.dataframe(
            timing_data,
            use_container_width=True,
            hide_index=True
        )
    
    with col2:
        # Weather and track info
        st.subheader("Track Conditions")
        
        # Weather metrics
        weather_data = generate_mock_weather_data()
        st.metric("Air Temperature", f"{weather_data['air_temp']}°C")
        st.metric("Track Temperature", f"{weather_data['track_temp']}°C")
        st.metric("Humidity", f"{weather_data['humidity']}%")
        st.metric("Wind Speed", f"{weather_data['wind_speed']} km/h")
        
        # Track status
        track_status = random.choice(["GREEN", "YELLOW - Sector 2", "RED", "SAFETY CAR"])
        status_color = {
            "GREEN": "green",
            "YELLOW": "yellow",
            "RED": "red",
            "SAFETY CAR": "orange"
        }.get(track_status.split(" ")[0], "green")
        
        st.markdown(f"""
        <div style="background-color: {status_color}; color: black; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;">
            Track Status: {track_status}
        </div>
        """, unsafe_allow_html=True)
    
    # DRS status
    drs_enabled = random.choice([True, False])
    st.markdown(f"""
    <div style="background-color: {'green' if drs_enabled else 'red'}; color: white; padding: 5px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 10px;">
        DRS: {'ENABLED' if drs_enabled else 'DISABLED'}
    </div>
    """, unsafe_allow_html=True)
    
    # Auto-refresh functionality
    st.markdown("""
    <meta http-equiv="refresh" content="10">
    """, unsafe_allow_html=True)
    
    # Live pit stops and other events
    st.subheader("Recent Events")
    events = [
        f"LAP {current_lap-2}: VER pits from P1 - Hard tires - 2.4s stop",
        f"LAP {current_lap-4}: Yellow flag in sector 2 - HAM off track",
        f"LAP {current_lap-7}: PER sets fastest lap - 1:13.825",
    ]
    
    for event in events:
        st.info(event)

def generate_mock_timing_data(num_drivers):
    """Generate mock timing data for demo purposes."""
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
    
    # Create a dataframe for the timing data
    timing_data = []
    
    # Create a shuffled list of positions
    positions = list(range(1, num_drivers + 1))
    random.shuffle(positions)
    
    # Add drivers
    i = 0
    for team, data in teams.items():
        for driver in data["drivers"]:
            if i < num_drivers:
                position = positions[i]
                gap = f"+{round(random.uniform(0, 60), 3)}s" if position > 1 else "Leader"
                interval = f"+{round(random.uniform(0, 5), 3)}s" if position > 1 else "-"
                
                # Last lap time
                last_lap = f"1:{random.randint(10, 20)}.{random.randint(100, 999)}"
                
                # Determine driver status
                status_options = ["On Track", "In Pit", "Out", "Retired"]
                status_weights = [0.8, 0.1, 0.05, 0.05]
                status = random.choices(status_options, status_weights)[0]
                
                # Tire compound
                tire_options = ["S", "M", "H", "I", "W"]
                tire_weights = [0.3, 0.4, 0.2, 0.05, 0.05]
                tire = random.choices(tire_options, tire_weights)[0]
                
                # Tire age
                tire_age = random.randint(1, 30) if status == "On Track" else "-"
                
                timing_data.append({
                    "Pos": position,
                    "Driver": driver,
                    "Team": team,
                    "Gap": gap,
                    "Interval": interval,
                    "LastLap": last_lap,
                    "Status": status,
                    "Tire": tire,
                    "Age": tire_age,
                    "TeamColor": data["color"]
                })
                i += 1
    
    # Sort by position
    timing_df = pd.DataFrame(timing_data)
    timing_df = timing_df.sort_values("Pos")
    
    return timing_df

def generate_mock_weather_data():
    """Generate mock weather data for demo purposes."""
    return {
        "air_temp": round(random.uniform(18, 32), 1),
        "track_temp": round(random.uniform(25, 45), 1),
        "humidity": random.randint(30, 90),
        "wind_speed": random.randint(0, 25),
        "wind_direction": random.randint(0, 359),
        "rainfall": random.random() < 0.2  # 20% chance of rain
    }

def show_track_info(event, conn):
    """Display track information for the selected event."""
    st.subheader(f"🏁 {event.get('event_name', 'Event')} - Track Information")
    
    # In a real implementation, you would fetch this from a database
    # For now, show mock data
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        - **Location**: {event.get('location', 'Unknown')}
        - **Country**: {event.get('country', 'Unknown')}
        - **Circuit Length**: 5.2 km
        - **Lap Record**: 1:12.909 (Lewis Hamilton, 2020)
        - **DRS Zones**: 2
        """)
    
    with col2:
        # Display a map or track layout
        st.image("https://via.placeholder.com/400x200?text=Track+Layout", 
                 caption=f"{event.get('event_name', 'Track')} Layout")