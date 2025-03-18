import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from backend.db_connection import get_db_handler
from backend.weather import get_weather_for_location, get_track_weather

def event_schedule():
    st.title("📅 Event Schedule")

    if "selected_event" not in st.session_state:
        st.warning("No event selected!")
        return

    event_id = st.session_state["selected_event"]

    with get_db_handler() as db:
        # Fetch event details (Make sure event exists before using it)
        event_info = db.execute_query("SELECT event_name, country FROM events WHERE id = ?", (event_id,))

        if event_info.empty:
            st.error("⚠️ Event not found.")
            return

        event_name = event_info.iloc[0]["event_name"]
        event_location = event_info.iloc[0]["event_name"]

    # Display the event title
    st.title(f"📅 Event Schedule - {event_name}")    

    # Fetch sessions
    with get_db_handler() as db:
        sessions = db.execute_query("SELECT name, date, session_type FROM sessions WHERE event_id = ?", (event_id,))

    if sessions.empty:
        st.info("No sessions available for this event.")
        return

    # Convert dates to datetime and sort them
    sessions['date'] = pd.to_datetime(sessions['date'], errors='coerce')
    sessions = sessions.sort_values(by='date')

    # Define function to format date
    def format_datetime(date_string):
        try:
            dt = datetime.fromisoformat(str(date_string))
            return dt.strftime("%d %b %Y, %H:%M")
        except:
            return date_string  # Fallback

    # Define colors for different session types
    def get_session_color(session_type):
        colors = {
            "Practice": "#1e90ff",       # Blue
            "Qualifying": "#ff4500",    # Red-Orange
            "Race": "#228b22",          # Green
            "Sprint": "#8a2be2",        # Purple
            "Sprint Qualifying": "#ff8c00"  # Dark Orange
        }
        return colors.get(session_type, "#444")
    

    # Display session schedule
    st.subheader("Sessions")
    for _, session in sessions.iterrows():
        formatted_time = format_datetime(session['date'])
        session_color = get_session_color(session['session_type'])

        # Fetch weather for the specific session time
        session_time = session['date'].isoformat()  # Convert Timestamp to ISO format string
        session_weather = get_weather_for_location(event_name, session_time)

        #st.write(f"Debug: {session['name']} at {session['date']}: {session_weather}")

        # Ensure weather data is formatted correctly
        if session_weather:
            st.markdown(
                f"""
                <div class="session-card" 
                    style="border-left: 6px solid {session_color}; padding: 10px; border-radius: 8px; margin-bottom: 8px; background-color: #222;">
                    <h3>{session['name']}</h3>
                    <p>📅 {formatted_time}</p>
                    <div style="display: flex; gap: 20px; font-size: 16px;">
                        <span>🌡️ <b>{session_weather['temperature']}°C</b></span>
                        <span>🔥 <b>{session_weather['track_temperature']}°C</b></span>
                        <span>💨 <b>{session_weather['wind_speed']} km/h</b></span>
                        <span>☁️ <b>{session_weather['cloud_cover']}%</b></span>
                        <span>🌧️ <b>{'Yes' if session_weather['rainfall'] else 'No'}</b></span>
                    </div>
                </div>
                """, unsafe_allow_html=True
            )
        else:
            st.markdown(f"""
            <div class="session-card" 
                style="border-left: 6px solid {session_color}; padding: 10px; border-radius: 8px; margin-bottom: 8px; background-color: #222;">
                <h3>{session['name']}</h3>
                <p>📅 {formatted_time}</p>
                <p>⚠️ Weather data unavailable.</p>
            </div>
            """, unsafe_allow_html=True)