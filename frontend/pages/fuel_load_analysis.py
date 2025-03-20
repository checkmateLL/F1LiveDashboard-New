import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def fuel_load_analysis():
    """Fuel Load & Degradation Impact Analysis."""
    st.title("⛽ Fuel Load Analysis & Performance Impact")

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

        # Fetch lap data
        laps_df = data_service.get_lap_times(session_id)
        if laps_df.empty:
            st.warning("No lap data available.")
            return

        # Estimate fuel load based on lap number
        laps_df["estimated_fuel_load"] = estimate_fuel_load(laps_df)

        # Normalize lap times based on fuel load
        laps_df["corrected_lap_time"] = normalize_lap_time(laps_df)

        # Create visualization tabs
        tab1, tab2 = st.tabs(["Fuel Load vs Lap Time", "Actual vs Corrected Lap Time"])

        with tab1:
            plot_fuel_load_vs_lap_time(laps_df)

        with tab2:
            plot_actual_vs_corrected_lap_time(laps_df)

        # Display dataset
        st.subheader("📊 Fuel Load Analysis Data")
        st.dataframe(laps_df, use_container_width=True)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def estimate_fuel_load(df):
    """Estimates fuel load dynamically based on lap number and degradation trends."""
    df["estimated_fuel_load"] = np.exp(-df["lap_number"] / 30) * 110  # 110kg start estimate
    return df["estimated_fuel_load"]

def normalize_lap_time(df):
    """Applies a fuel correction model to normalize lap times."""
    fuel_correction_factor = 0.035  # Estimated lap time loss per kg of fuel
    df["corrected_lap_time"] = df["lap_time"] - (df["estimated_fuel_load"] * fuel_correction_factor)
    return df["corrected_lap_time"]

def plot_fuel_load_vs_lap_time(df):
    """Visualizes the effect of fuel load on lap times."""
    fig = px.scatter(
        df,
        x="estimated_fuel_load",
        y="lap_time",
        color="driver_name",
        title="⛽ Fuel Load vs. Lap Time",
        labels={"estimated_fuel_load": "Fuel Load (kg)", "lap_time": "Lap Time (s)"},
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_actual_vs_corrected_lap_time(df):
    """Compares actual lap times vs. fuel-corrected lap times."""
    fig = px.line(
        df,
        x="lap_number",
        y=["lap_time", "corrected_lap_time"],
        color="driver_name",
        title="📈 Actual vs. Fuel-Corrected Lap Time",
        labels={"lap_number": "Lap Number", "lap_time": "Lap Time (s)"},
    )
    st.plotly_chart(fig, use_container_width=True)

fuel_load_analysis()