import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def is_data_empty(data):
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def track_position_evolution():
    """Track Position Evolution & Heatmap Visualization."""
    st.title("📍 Track Position Evolution")

    try:
        # Fetch available years
        available_years = data_service.get_available_years()
        selected_year = st.selectbox("Select Season", available_years, index=available_years.index(st.session_state.get("selected_year", available_years[0])))
        st.session_state["selected_year"] = selected_year

        # Fetch events
        events = data_service.get_events(selected_year)
        if not events:
            st.warning("No events available.")
            return

        event_options = {event["event_name"]: event["id"] for event in events}
        selected_event = st.selectbox("Select Event", event_options.keys(), index=list(event_options.values()).index(st.session_state.get("selected_event", next(iter(event_options.values())))))
        event_id = event_options[selected_event]
        st.session_state["selected_event"] = event_id

        # Fetch race sessions
        sessions = data_service.get_race_sessions(event_id)
        if not sessions:
            st.warning("No race sessions available.")
            return

        session_options = {session["name"]: session["id"] for session in sessions}
        selected_session = st.selectbox("Select Session", session_options.keys(), index=list(session_options.values()).index(st.session_state.get("selected_session", next(iter(session_options.values())))))
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        # Fetch telemetry data
        telemetry_df = data_service.get_telemetry(session_id)
        if is_data_empty(telemetry_df):
            st.warning("No telemetry data available for this session.")
            return pd.DataFrame()

        # Create heatmap
        plot_track_position_heatmap(telemetry_df)

        # Display dataset
        st.subheader("📊 Track Position Data")
        st.dataframe(telemetry_df, use_container_width=True)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def plot_track_position_heatmap(df):
    """Generates an interactive heatmap of driver positions on track."""
    fig = px.density_heatmap(
        df,
        x="x",
        y="y",
        z="speed",
        nbinsx=50,
        nbinsy=50,
        color_continuous_scale="thermal",
        title="🔥 Track Position Heatmap (Speed-Weighted)"
    )
    fig.update_layout(xaxis_title="X Position", yaxis_title="Y Position")
    st.plotly_chart(fig, use_container_width=True)

track_position_evolution()