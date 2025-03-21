import streamlit as st
import pandas as pd
from datetime import datetime

from backend.data_service import F1DataService
from backend.weather import get_weather_for_location
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def event_schedule():
    """Displays the session schedule and weather information for a selected event."""
    st.title("📅 Event Schedule")

    # Ensure an event is selected
    if "selected_event" not in st.session_state:
        st.warning("No event selected!")
        return

    event_id = st.session_state["selected_event"]

    try:
        # Fetch event details
        event_info = data_service.get_event_by_id(event_id)
        if event_info is None:
            st.error("⚠️ Event not found.")
            return

        event_name = event_info["event_name"]
        event_location = event_info["location"]  # Fix incorrect assignment

        # Display event title
        st.subheader(f"📅 Event Schedule - {event_name}")

        # Fetch event sessions
        sessions_df = data_service.get_sessions(event_id)
        if not sessions_df or (isinstance(sessions_df, pd.DataFrame) and sessions_df.empty):
            st.warning("No sessions available for this event.")
            return

        # Convert dates to datetime and sort them
        sessions_df["date"] = pd.to_datetime(sessions_df["date"], errors="coerce")
        sessions_df = sessions_df.sort_values(by="date")

        # Define function to format date
        def format_datetime(date_string):
            try:
                dt = datetime.fromisoformat(str(date_string))
                return dt.strftime("%d %b %Y, %H:%M")
            except Exception:
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
        for _, session in sessions_df.iterrows():
            formatted_time = format_datetime(session["date"])
            session_color = get_session_color(session["session_type"])

            # Fetch weather for the session time
            session_time = session["date"].isoformat()
            session_weather = get_weather_for_location(event_location, session_time)

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

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

event_schedule()