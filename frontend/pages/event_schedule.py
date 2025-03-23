import streamlit as st
import pandas as pd
from datetime import datetime

from backend.data_service import F1DataService
from backend.weather import get_weather_for_location
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def is_data_empty(data):
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def event_schedule():
    st.title("📅 Event Schedule")

    if "selected_event" not in st.session_state:
        st.warning("No event selected!")
        return

    event_id = st.session_state["selected_event"]

    try:
        event_info = data_service.get_event_by_id(event_id)
        if event_info is None:
            st.error("⚠️ Event not found.")
            return

        if isinstance(event_info, pd.DataFrame):
            event_info = event_info.iloc[0].to_dict()

        event_name = event_info.get("event_name", "Unknown Event")
        event_location = event_info.get("location", "Unknown Location")

        st.subheader(f"📅 Event Schedule - {event_name}")

        sessions_df = data_service.get_sessions(event_id)

        if is_data_empty(sessions_df):
            st.warning("No sessions available for this event.")
            return

        if not isinstance(sessions_df, pd.DataFrame):
            sessions_df = pd.DataFrame(sessions_df)

        sessions_df["date"] = pd.to_datetime(sessions_df["date"], errors="coerce")
        sessions_df = sessions_df.sort_values(by="date")

        def format_datetime(date):
            if pd.isna(date):
                return "TBA"
            return date.strftime("%d %b %Y, %H:%M")

        def get_session_color(session_type):
            colors = {
                "practice": "#1e90ff",
                "qualifying": "#ff4500",
                "race": "#228b22",
                "sprint": "#8a2be2",
                "sprint_qualifying": "#ff8c00",
                "sprint_shootout": "#ff8c00"
            }
            return colors.get(session_type.lower(), "#444") if isinstance(session_type, str) else "#444"

        today = pd.Timestamp(datetime.now())
        past_sessions = []
        future_sessions = []

        for _, session in sessions_df.iterrows():
            session_date = session["date"]
            session_dict = session.to_dict()

            if pd.isna(session_date):
                future_sessions.append(session_dict)
            elif session_date < today:
                past_sessions.append(session_dict)
            else:
                future_sessions.append(session_dict)

        if past_sessions:
            st.subheader("Past Sessions")
            for session in past_sessions:
                formatted_time = format_datetime(session["date"])
                session_color = get_session_color(session.get("session_type"))

                st.markdown(f"""
                <div style="border-left: 6px solid {session_color}; padding: 10px; border-radius: 8px; margin-bottom: 8px; background-color: #222;">
                    <h3>{session['name']}</h3>
                    <p>📅 {formatted_time}</p>
                    <p>Completed</p>
                </div>
                """, unsafe_allow_html=True)

        if future_sessions:
            st.subheader("Upcoming Sessions")
            for session in future_sessions:
                formatted_time = format_datetime(session["date"])
                session_color = get_session_color(session.get("session_type"))

                session_weather = None
                if pd.notna(session["date"]):
                    try:
                        session_weather = get_weather_for_location(event_location, session["date"].isoformat())
                    except Exception as weather_e:
                        session_weather = None

                if session_weather:
                    st.markdown(f"""
                    <div style="border-left: 6px solid {session_color}; padding: 10px; border-radius: 8px; margin-bottom: 8px; background-color: #222;">
                        <h3>{session['name']}</h3>
                        <p>📅 {formatted_time}</p>
                        <div style="display: flex; gap: 20px; font-size: 16px;">
                            <span>🌡️ <b>{session_weather.get('temperature', 'N/A')}°C</b></span>
                            <span>🔥 <b>{session_weather.get('track_temperature', 'N/A')}°C</b></span>
                            <span>💨 <b>{session_weather.get('wind_speed', 'N/A')} km/h</b></span>
                            <span>☁️ <b>{session_weather.get('cloud_cover', 'N/A')}%</b></span>
                            <span>🌧️ <b>{'Yes' if session_weather.get('rainfall', False) else 'No'}</b></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="border-left: 6px solid {session_color}; padding: 10px; border-radius: 8px; margin-bottom: 8px; background-color: #222;">
                        <h3>{session['name']}</h3>
                        <p>📅 {formatted_time}</p>
                        <p>⚠️ Weather data unavailable.</p>
                    </div>
                    """, unsafe_allow_html=True)

        if not past_sessions and not future_sessions:
            st.info("No session schedule information available.")

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

event_schedule()