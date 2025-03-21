import streamlit as st
import pandas as pd
from datetime import datetime

from backend.data_service import F1DataService
from backend.weather import get_weather_for_location
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def is_data_empty(data):
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def event_schedule():
    """Displays the session schedule and weather information for a selected event."""
    st.title("📅 Event Schedule")

    # Ensure an event is selected
    if "selected_event" not in st.session_state:
        st.warning("No event selected!")
        # Show available events to select
        try:
            available_years = data_service.get_available_years()
            if available_years:
                # Make sure available_years is a list
                if not isinstance(available_years, list):
                    try:
                        available_years = [row['year'] for row in available_years]
                    except:
                        st.warning("Could not process available years data.")
                        return
                        
                year = available_years[0]
                events = data_service.get_events(year)
                
                if not is_data_empty(events):
                    # Convert to DataFrame if needed
                    if not isinstance(events, pd.DataFrame):
                        try:
                            events = pd.DataFrame(events)
                        except:
                            st.warning("Could not process events data.")
                            return
                            
                    # Create a dropdown to select an event
                    event_list = events['event_name'].tolist()
                    selected_event_name = st.selectbox("Select an event", event_list)
                    
                    # Get the event ID
                    event_id = events[events['event_name'] == selected_event_name]['id'].iloc[0]
                    
                    # Store in session state
                    st.session_state["selected_event"] = event_id
                    
                    # Rerun to reload page with selected event
                    st.rerun()
        except Exception as e:
            st.error(f"Error loading events: {e}")
        return

    event_id = st.session_state["selected_event"]

    try:
        # Fetch event details
        event_info = data_service.get_event_by_id(event_id)
        if event_info is None:
            st.error("⚠️ Event not found.")
            return

        # Check if event_info is a dict or DataFrame row
        if isinstance(event_info, pd.DataFrame):
            event_info = event_info.iloc[0].to_dict()
        elif not isinstance(event_info, dict):
            st.error("⚠️ Invalid event data format.")
            return

        event_name = event_info.get("event_name", "Unknown Event")
        event_location = event_info.get("location", "Unknown Location")

        # Display event title
        st.subheader(f"📅 Event Schedule - {event_name}")

        # Fetch event sessions
        sessions_df = data_service.get_sessions(event_id)

        # Process sessions data
        if is_data_empty(sessions_df):
            st.warning("No sessions available for this event.")
            return
            
        # Convert to DataFrame if needed
        if not isinstance(sessions_df, pd.DataFrame):
            try:
                sessions_df = pd.DataFrame(sessions_df)
            except:
                st.warning("Could not process sessions data.")
                return

        # Convert dates to datetime and sort them
        if 'date' in sessions_df.columns:
            sessions_df["date"] = pd.to_datetime(sessions_df["date"], errors="coerce")
            sessions_df = sessions_df.sort_values(by="date")

        # Define function to format date
        def format_datetime(date_string):
            try:
                dt = datetime.fromisoformat(str(date_string).replace('Z', '+00:00'))
                return dt.strftime("%d %b %Y, %H:%M")
            except Exception:
                return str(date_string)  # Fallback

        # Define colors for different session types
        def get_session_color(session_type):
            if not isinstance(session_type, str):
                return "#444"
                
            session_type = session_type.lower()
            colors = {
                "practice": "#1e90ff",       # Blue
                "qualifying": "#ff4500",    # Red-Orange
                "race": "#228b22",          # Green
                "sprint": "#8a2be2",        # Purple
                "sprint_qualifying": "#ff8c00",  # Dark Orange
                "sprint_shootout": "#ff8c00"  # Dark Orange
            }
            return colors.get(session_type, "#444")

        # Separate past and future sessions
        today = datetime.now()
        past_sessions = []
        future_sessions = []
        
        for _, session in sessions_df.iterrows():
            session_date = session["date"] if pd.notna(session["date"]) else None
            session_dict = session.to_dict()
            
            if session_date and session_date < today:
                past_sessions.append(session_dict)
            else:
                future_sessions.append(session_dict)
        
        # Display past sessions
        if past_sessions:
            st.subheader("Past Sessions")
            for session in past_sessions:
                formatted_time = format_datetime(session["date"])
                session_color = get_session_color(session.get("session_type", ""))

                # Display session card with basic info
                st.markdown(
                    f"""
                    <div class="session-card" 
                        style="border-left: 6px solid {session_color}; padding: 10px; border-radius: 8px; margin-bottom: 8px; background-color: #222;">
                        <h3>{session['name']}</h3>
                        <p>📅 {formatted_time}</p>
                        <p>Completed</p>
                    </div>
                    """, unsafe_allow_html=True
                )
        
        # Display future sessions
        if future_sessions:
            st.subheader("Upcoming Sessions")
            for session in future_sessions:
                formatted_time = format_datetime(session["date"])
                session_color = get_session_color(session.get("session_type", ""))

                # Fetch weather for the session time
                session_time = session["date"].isoformat() if pd.notna(session["date"]) else None
                session_weather = None
                if session_time:
                    try:
                        session_weather = get_weather_for_location(event_location, session_time)
                    except Exception as weather_e:
                        st.warning(f"Unable to fetch weather data: {weather_e}")

                # Display session card with weather info if available
                if session_weather:
                    st.markdown(
                        f"""
                        <div class="session-card" 
                            style="border-left: 6px solid {session_color}; padding: 10px; border-radius: 8px; margin-bottom: 8px; background-color: #222;">
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

        # If no past or future sessions
        if not past_sessions and not future_sessions:
            st.info("No session schedule information available.")

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

event_schedule()