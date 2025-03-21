import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from numpy.polynomial.polynomial import Polynomial

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def is_data_empty(data):
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def race_pace_analysis():
    """Race Pace Analysis Dashboard."""
    st.title("📊 Race Pace & Lap Time Predictions")

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

        # Fetch lap times including sector times
        lap_data = data_service.get_lap_times(session_id, include_sectors=True)
        if is_data_empty(lap_data):
            st.warning("No lap data available for this session.")
            return pd.DataFrame()

        # Convert lap times to seconds
        lap_data["lap_time_sec"] = lap_data["lap_time"].apply(convert_time_to_seconds)
        lap_data["sector_1_sec"] = lap_data["sector_1_time"].apply(convert_time_to_seconds)
        lap_data["sector_2_sec"] = lap_data["sector_2_time"].apply(convert_time_to_seconds)
        lap_data["sector_3_sec"] = lap_data["sector_3_time"].apply(convert_time_to_seconds)

        # Perform polynomial regression for lap time prediction
        lap_data = predict_lap_times(lap_data)

        # Create tabs for visualization
        tab1, tab2, tab3 = st.tabs(["Actual vs. Predicted", "Prediction Errors", "Sector Analysis"])

        with tab1:
            plot_actual_vs_predicted(lap_data)

        with tab2:
            plot_prediction_errors(lap_data)

        with tab3:
            plot_sector_analysis(lap_data)

        # Display full dataset
        st.subheader("Lap Time Data with Predictions")
        st.dataframe(lap_data.drop(columns=["sector_1_time", "sector_2_time", "sector_3_time"]), use_container_width=True)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def convert_time_to_seconds(time_str):
    """Convert lap time format to total seconds."""
    if pd.isna(time_str) or time_str is None:
        return None
    try:
        parts = time_str.split(" ")
        time_part = parts[-1]
        h, m, s = map(float, time_part.split(":"))
        return h * 3600 + m * 60 + s
    except Exception:
        return None

def predict_lap_times(df):
    """Uses polynomial regression to predict lap times for each driver."""
    predictions = {}

    for driver in df["driver_name"].unique():
        driver_df = df[df["driver_name"] == driver]
        x = driver_df["lap_number"].to_numpy()
        y = driver_df["lap_time_sec"].to_numpy()

        if len(x) > 3:  # Ensure enough data for polynomial regression
            poly = Polynomial.fit(x, y, 2)  # Quadratic regression
            y_pred = poly(x)
            predictions[driver] = y_pred
        else:
            predictions[driver] = y  # Default to actual times if not enough data

    df["predicted_lap_time_sec"] = df.apply(lambda row: predictions[row["driver_name"]][np.where(df["lap_number"] == row["lap_number"])[0][0]], axis=1)
    df["prediction_error"] = df["lap_time_sec"] - df["predicted_lap_time_sec"]
    return df

def plot_actual_vs_predicted(df):
    """Plots actual vs predicted lap times."""
    fig = px.line(df, x="lap_number", y=["lap_time_sec", "predicted_lap_time_sec"], color="driver_name", title="Actual vs Predicted Lap Times")
    fig.update_traces(line=dict(width=3))
    st.plotly_chart(fig, use_container_width=True)

def plot_prediction_errors(df):
    """Displays lap time prediction errors."""
    fig = px.histogram(df, x="prediction_error", color="driver_name", title="Lap Time Prediction Errors", nbins=20)
    st.plotly_chart(fig, use_container_width=True)

def plot_sector_analysis(df):
    """Displays sector times for analysis."""
    fig = px.line(df, x="lap_number", y=["sector_1_sec", "sector_2_sec", "sector_3_sec"], color="driver_name", title="Sector Times Analysis")
    fig.update_traces(line=dict(width=3))
    st.plotly_chart(fig, use_container_width=True)

race_pace_analysis()