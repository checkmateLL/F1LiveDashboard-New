import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def overtakes_analysis():
    """Overtake Analysis & Race Progression."""
    st.title("🏎️ Overtakes Analysis")

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

        # Detect overtakes dynamically
        overtakes_df = detect_overtakes(session_id)
        if overtakes_df.empty:
            st.warning("No overtakes detected for this session.")
            return

        # Create visualization tabs
        tab1, tab2, tab3 = st.tabs(["Overtakes Timeline", "Overtakes by Sector", "DRS Usage Impact"])

        with tab1:
            plot_overtakes_timeline(overtakes_df)

        with tab2:
            plot_overtakes_by_sector(overtakes_df)

        with tab3:
            plot_drs_impact(overtakes_df)

        # Display dataset
        st.subheader("📊 Overtakes Data")
        st.dataframe(overtakes_df, use_container_width=True)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def detect_overtakes(session_id):
    """
    Detect overtakes based on position changes between consecutive laps.
    """
    laps_df = data_service.get_lap_times(session_id)
    if laps_df.empty:
        return pd.DataFrame()

    # Sort laps by lap number and driver
    laps_df = laps_df.sort_values(["driver_id", "lap_number"])

    # Shift position data to compare with previous lap
    laps_df["prev_position"] = laps_df.groupby("driver_id")["position"].shift(1)
    laps_df["overtook"] = laps_df["prev_position"] > laps_df["position"]

    # Filter overtakes
    overtakes_df = laps_df[laps_df["overtook"]].copy()
    overtakes_df["overtaken_driver"] = overtakes_df.groupby("driver_id")["driver_name"].shift(1)

    # Fetch sector & DRS usage
    telemetry_df = data_service.get_telemetry(session_id)
    if not telemetry_df.empty:
        telemetry_df["drs_used"] = telemetry_df["drs"].diff() > 0
        overtakes_df = overtakes_df.merge(telemetry_df[["driver_id", "lap_number", "sector", "drs_used"]], on=["driver_id", "lap_number"], how="left")

    return overtakes_df[["lap_number", "sector", "driver_name", "overtaken_driver", "position", "drs_used"]]

def plot_overtakes_timeline(df):
    """Visualizes overtakes over the course of the race."""
    fig = px.scatter(
        df,
        x="lap_number",
        y="driver_name",
        text="overtaken_driver",
        title="📈 Overtakes Timeline",
        color="drs_used",
        labels={"lap_number": "Lap", "driver_name": "Overtaking Driver"},
    )
    fig.update_traces(textposition="top center", marker=dict(size=10))
    st.plotly_chart(fig, use_container_width=True)

def plot_overtakes_by_sector(df):
    """Shows where most overtakes happen on the track."""
    fig = px.histogram(
        df,
        x="sector",
        color="driver_name",
        title="🔍 Overtakes Per Sector",
        labels={"sector": "Track Sector"},
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_drs_impact(df):
    """Analyzes the impact of DRS on overtakes."""
    drs_counts = df["drs_used"].value_counts()
    fig = px.pie(
        names=["With DRS", "Without DRS"],
        values=drs_counts,
        title="💨 DRS Impact on Overtakes",
    )
    st.plotly_chart(fig, use_container_width=True)

overtakes_analysis()