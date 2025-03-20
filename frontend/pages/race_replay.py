import streamlit as st
import pandas as pd
import plotly.express as px
import time

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def race_replay():
    """Race Replay Visualization."""
    st.title("📽️ Race Replay")

    try:
        # Get available years
        available_years = data_service.get_available_years()
        default_year = st.session_state.get("selected_year", available_years[0])
        selected_year = st.selectbox("Select Season", available_years, 
                             index=available_years.index(default_year),
                             key="replay_year")
        st.session_state["selected_year"] = selected_year

        # Get all events for the selected season
        events_df = data_service.get_events(selected_year)
        if not events_df or len(events_df) == 0:
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

        # Default to first available session
        session_options = {session["name"]: session["id"] for session in sessions_df}
        default_session_id = st.session_state.get("selected_session", next(iter(session_options.values())))
        selected_session = st.selectbox("Select Session", session_options.keys(), index=list(session_options.values()).index(default_session_id))
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        # Fetch lap data for replay
        laps_df = data_service.get_laps(session_id)
        if laps_df.empty:
            st.warning("No lap data available for this session.")
            return

        # Convert lap number to a timeline
        lap_numbers = sorted(laps_df["lap_number"].unique())
        lap = st.slider("Select Lap to Replay", min_value=min(lap_numbers), max_value=max(lap_numbers), value=min(lap_numbers))

        # Filter for the selected lap
        lap_data = laps_df[laps_df["lap_number"] == lap]

        # Plot positions for the lap
        fig = px.scatter(
            lap_data,
            x="x", y="y", 
            color="driver_name",
            text="driver_abbreviation",
            title=f"Race Replay - Lap {lap}",
            labels={"x": "Track X Position", "y": "Track Y Position"},
            hover_data=["team_name", "position", "compound"]
        )

        fig.update_traces(textposition="top center")
        fig.update_layout(height=600)

        st.plotly_chart(fig, use_container_width=True)

        # Live Replay Simulation
        if st.button("Start Replay"):
            for lap in lap_numbers:
                lap_data = laps_df[laps_df["lap_number"] == lap]

                fig = px.scatter(
                    lap_data,
                    x="x", y="y", 
                    color="driver_name",
                    text="driver_abbreviation",
                    title=f"Race Replay - Lap {lap}",
                    labels={"x": "Track X Position", "y": "Track Y Position"},
                    hover_data=["team_name", "position", "compound"]
                )

                fig.update_traces(textposition="top center")
                fig.update_layout(height=600)

                st.plotly_chart(fig, use_container_width=True)
                time.sleep(1.5)  # Simulates replay speed

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

race_replay()