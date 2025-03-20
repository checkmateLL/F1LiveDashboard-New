import streamlit as st
import pandas as pd

from frontend.components.race_visuals import (
    show_race_pace_analysis, 
    show_tire_strategy_analysis, 
    show_driver_performance,
    show_overtake_analysis,
    show_telemetry_analysis
)
from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def race_analysis():
    """Race Analysis Dashboard."""
    st.title("📊 Race Analysis")

    try:
        # Store selected year in session state
        available_years = data_service.get_available_years()
        default_year = st.session_state.get("selected_year", available_years[0])
        selected_year = st.selectbox("Select Season", available_years, index=available_years.index(default_year))
        st.session_state["selected_year"] = selected_year

        # Fetch all events for the selected season
        events_df = data_service.get_events(selected_year)
        if events_df.empty:
            st.warning("No events available for this season.")
            return

        # Default to first available event
        event_options = {event["event_name"]: event["id"] for event in events_df}
        default_event_id = st.session_state.get("selected_event", next(iter(event_options.values())))
        selected_event = st.selectbox("Select Event", event_options.keys(), index=list(event_options.values()).index(default_event_id))
        event_id = event_options[selected_event]
        st.session_state["selected_event"] = event_id

        # Get race sessions for the selected event
        sessions_df = data_service.get_race_sessions(event_id)
        if sessions_df.empty:
            st.warning("No race sessions available for this event.")
            return

        # Default to first race session
        session_options = {session["name"]: session["id"] for session in sessions_df}
        default_session_id = st.session_state.get("selected_session", next(iter(session_options.values())))
        selected_session = st.selectbox("Select Session", session_options.keys(), index=list(session_options.values()).index(default_session_id))
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        # Get lap times data
        laps_df = data_service.get_lap_times(session_id)
        if laps_df.empty:
            st.warning("No lap data available for this session.")
            return

        # Convert lap times to seconds
        laps_df["lap_time_sec"] = laps_df["lap_time"].apply(convert_time_to_seconds)

        # Create tabs for different analysis
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Race Pace", "Tire Strategy", "Driver Performance", "Overtakes", "Telemetry"
        ])

        with tab1:
            show_race_pace_analysis(laps_df)

        with tab2:
            show_tire_strategy_analysis(laps_df)

        with tab3:
            show_driver_performance(laps_df)

        with tab4:
            show_overtake_analysis(laps_df)

        with tab5:
            show_telemetry_analysis(session_id)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def convert_time_to_seconds(time_str):
    """Convert time format (e.g., '0 days 00:01:30.123456') to total seconds."""
    if pd.isna(time_str) or time_str is None:
        return None
    try:
        parts = time_str.split(" ")
        time_part = parts[-1]
        h, m, s = map(float, time_part.split(":"))
        return h * 3600 + m * 60 + s
    except Exception:
        return None

race_analysis()