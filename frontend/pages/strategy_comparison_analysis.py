import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def strategy_comparison_analysis():
    """Race Strategy & Performance Analysis Dashboard."""
    st.title("🏎️ Strategy Comparison & Effectiveness Analysis")

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
        if not sessions or len(sessions) == 0:
            st.warning("No sessions available.")
            return
        # Then filter for race sessions only
        race_sessions = [s for s in sessions if s.get("session_type") == "race"]
        if not race_sessions:
            st.warning("No race sessions available.")
            return

        session_options = {session["name"]: session["id"] for session in sessions}
        selected_session = st.selectbox("Select Session", session_options.keys(), index=list(session_options.values()).index(st.session_state.get("selected_session", next(iter(session_options.values())))))
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        # Fetch race results
        results_df = data_service.get_race_results(session_id)
        if results_df.empty:
            st.warning("No race results available.")
            return

        # Fetch lap data (used to derive pit stops & strategy)
        laps_df = data_service.get_lap_times(session_id)
        if laps_df.empty:
            st.warning("No lap data available.")
            return

        # Derive pit stops by detecting compound changes
        results_df["total_stops"] = results_df["driver_id"].map(lambda driver: calculate_pit_stops(laps_df, driver))

        # Merge data for strategy analysis
        strategy_df = results_df[["driver_name", "team_name", "grid_position", "position", "total_stops", "race_time"]]
        strategy_df["race_time_sec"] = strategy_df["race_time"].apply(convert_time_to_seconds)

        # Create visualization tabs
        tab1, tab2, tab3 = st.tabs(["Pit Stops & Position", "Tire Compound Usage", "Race Time vs Pit Stops"])

        with tab1:
            plot_strategy_vs_position(strategy_df)

        with tab2:
            plot_tire_compound_vs_performance(laps_df, results_df)

        with tab3:
            plot_pit_stops_vs_race_time(strategy_df)

        # Display full dataset
        st.subheader("📊 Strategy Effectiveness Data")
        st.dataframe(strategy_df.drop(columns=["race_time"]), use_container_width=True)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def calculate_pit_stops(laps_df, driver_id):
    """
    Detects pit stops based on tire compound changes.
    """
    driver_laps = laps_df[laps_df["driver_id"] == driver_id].sort_values("lap_number")
    if driver_laps.empty or "compound" not in driver_laps.columns:
        return 0

    # Count compound changes as pit stops
    return driver_laps["compound"].nunique() - 1

def convert_time_to_seconds(time_str):
    """
    Converts race time format to total seconds.
    """
    if pd.isna(time_str) or time_str is None:
        return None
    try:
        parts = time_str.split(" ")
        time_part = parts[-1]
        h, m, s = map(float, time_part.split(":"))
        return h * 3600 + m * 60 + s
    except Exception:
        return None

def plot_strategy_vs_position(df):
    """
    Compares pit stop strategy vs final position.
    """
    fig = px.box(df, x="total_stops", y="position", color="team_name", title="Effectiveness of Pit Stop Strategies")
    fig.update_layout(xaxis_title="Total Pit Stops", yaxis_title="Final Position")
    st.plotly_chart(fig, use_container_width=True)

def plot_tire_compound_vs_performance(laps_df, results_df):
    """
    Evaluates performance of tire compounds used in different strategies.
    """
    merged_df = laps_df.merge(results_df, on="driver_id", how="inner")

    fig = px.box(merged_df, x="compound", y="position", color="team_name", title="Tire Compound Performance Comparison")
    fig.update_layout(xaxis_title="Tire Compound", yaxis_title="Final Position")
    st.plotly_chart(fig, use_container_width=True)

def plot_pit_stops_vs_race_time(df):
    """
    Analyzes how pit stop count affects race time.
    """
    fig = px.scatter(df, x="total_stops", y="race_time_sec", color="team_name", title="Impact of Pit Stop Count on Race Time")
    fig.update_layout(xaxis_title="Total Pit Stops", yaxis_title="Total Race Time (s)")
    st.plotly_chart(fig, use_container_width=True)

strategy_comparison_analysis()