import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from frontend.components.common_visualizations import create_line_chart
from frontend.components.telemetry_visuals import show_track_map
from backend.data_service import F1DataService
from backend.error_handling import DatabaseError, ResourceNotFoundError

# Initialize data service
data_service = F1DataService()

def is_data_empty(data):
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def telemetry():
    """Telemetry Analysis Dashboard."""
    st.title("📡 Telemetry Analysis")

    try:
        # Get available years
        years = data_service.get_available_years()
        year = st.selectbox("Select Season", options=years, index=years.index(st.session_state.get("selected_year", years[0])))
        st.session_state["selected_year"] = year

        # Get events
        events = data_service.get_events(year)
        if not events:
            st.warning("No events available.")
            return

        event_options = {event["event_name"]: event["id"] for event in events}
        selected_event = st.selectbox("Select Event", event_options.keys(), index=list(event_options.values()).index(st.session_state.get("selected_event", next(iter(event_options.values())))))
        event_id = event_options[selected_event]
        st.session_state["selected_event"] = event_id

        # Get sessions
        sessions = data_service.get_sessions(event_id)
        if not sessions:
            st.warning("No sessions available.")
            return

        session_options = {session["name"]: session["id"] for session in sessions}
        selected_session = st.selectbox("Select Session", session_options.keys(), index=list(session_options.values()).index(st.session_state.get("selected_session", next(iter(session_options.values())))))
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        # Get drivers
        drivers = data_service.get_drivers(session_id)
        if not drivers:
            st.warning("No drivers found.")
            return

        driver_options = {driver["full_name"]: driver for driver in drivers}
        selected_driver = st.selectbox("Select Driver", driver_options.keys())
        driver = driver_options[selected_driver]
        driver_id = driver["id"]

        # Get lap numbers
        laps_df = data_service.get_lap_numbers(session_id, driver_id)
        if is_data_empty(laps_df):
            st.warning("No lap data available.")
            return pd.DataFrame()

        selected_lap = st.selectbox("Select Lap", sorted(laps_df["lap_number"].tolist()))

        # Fetch telemetry data
        telemetry_df = data_service.get_telemetry(session_id, driver_id, selected_lap, use_distance=True)
        if is_data_empty(telemetry_df):
            st.warning("No telemetry available.")
            return pd.DataFrame()

        # Driver comparison
        st.subheader("Driver Comparison")
        compare_enabled = st.checkbox("Compare with another driver")
        comparison_df = None

        if compare_enabled:
            other_drivers = {name: d["id"] for name, d in driver_options.items() if d["id"] != driver_id}
            if other_drivers:
                comparison_driver = st.selectbox("Compare with", other_drivers.keys())
                comparison_driver_id = other_drivers[comparison_driver]
                comparison_df = data_service.get_telemetry(session_id, comparison_driver_id, selected_lap, use_distance=True)

        # Create telemetry tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Speed & Throttle", "Braking & DRS", "Gears", "Track Map"])

        with tab1:
            st.subheader("Speed & Throttle Analysis")
            st.plotly_chart(create_line_chart(telemetry_df, "distance", "speed", "Speed vs Distance", "Distance (m)", "Speed (km/h)", compare_df=comparison_df), use_container_width=True)
            st.plotly_chart(create_line_chart(telemetry_df, "distance", "throttle", "Throttle vs Distance", "Distance (m)", "Throttle (%)", compare_df=comparison_df), use_container_width=True)

        with tab2:
            st.subheader("Braking & DRS Analysis")
            st.plotly_chart(create_line_chart(telemetry_df, "distance", "brake", "Brake Usage vs Distance", "Distance (m)", "Brake Pressure", compare_df=comparison_df), use_container_width=True)
            st.plotly_chart(create_line_chart(telemetry_df, "distance", "drs", "DRS Activation vs Distance", "Distance (m)", "DRS Status", compare_df=comparison_df), use_container_width=True)

            # Highlight DRS Activation Points
            drs_activations = telemetry_df[telemetry_df["drs"].diff() > 0]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=telemetry_df["distance"], y=telemetry_df["speed"], mode="lines", name="Speed"))
            fig.add_trace(go.Scatter(x=drs_activations["distance"], y=drs_activations["speed"], mode="markers", marker=dict(color="green", symbol="star", size=10), name="DRS Activation"))
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.subheader("Gear & RPM Analysis")
            st.plotly_chart(create_line_chart(telemetry_df, "distance", "gear", "Gear Shifts vs Distance", "Distance (m)", "Gear", compare_df=comparison_df), use_container_width=True)
            st.plotly_chart(create_line_chart(telemetry_df, "distance", "rpm", "Engine RPM vs Distance", "Distance (m)", "RPM", compare_df=comparison_df), use_container_width=True)

            # Gear Shift Stats
            gear_shifts = telemetry_df["gear"].diff().ne(0).sum()
            gear_usage = telemetry_df["gear"].value_counts(normalize=True) * 100
            most_used_gear = gear_usage.idxmax()

            col1, col2 = st.columns(2)
            col1.metric("Total Gear Shifts", gear_shifts)
            col2.metric("Most Used Gear", most_used_gear)

            # Gear Usage Distribution
            gear_data = gear_usage.reset_index().rename(columns={"gear": "Percentage", "index": "Gear"})
            fig = px.bar(gear_data, x="Gear", y="Percentage", title="Gear Usage (%)", color="Gear")
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            st.subheader("Track Map & Braking Points")
            braking_points = telemetry_df[telemetry_df["brake"] > 0][["x", "y"]]
            show_track_map(telemetry_df, braking_points.values.tolist())

            # Summary Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Maximum Speed", f"{telemetry_df['speed'].max():.1f} km/h")
            col2.metric("Average Speed", f"{telemetry_df['speed'].mean():.1f} km/h")
            col3.metric("Braking Points", braking_points.shape[0])

    except (DatabaseError, ResourceNotFoundError) as e:
        st.error(f"Database error: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")

telemetry()