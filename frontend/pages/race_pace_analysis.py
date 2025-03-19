# frontend/pages/race_pace_analysis.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler
from numpy.polynomial.polynomial import Polynomial

st.set_page_config(layout="wide")

st.title("Actual vs. Predicted Lap Time Analysis (Optimized Query Execution & ID Handling)")

def get_race_pace_data(session_id):
    """
    Retrieves actual lap times for race pace analysis.
    """
    session_id = int(session_id)  # Ensure session_id is integer
    query = """
        SELECT laps.lap_number, drivers.driver_name, laps.lap_time
        FROM laps
        JOIN drivers ON laps.driver_id = drivers.driver_id
        WHERE laps.session_id = ?
        ORDER BY laps.lap_number, drivers.driver_name
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (session_id,))
    
    return df

def plot_sector_analysis(df):
    """
    Plots sector times to analyze where time is gained or lost.
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    sns.lineplot(ax=axes[0], x="lap_number", y="sector_1_time", hue="driver_name", data=df)
    axes[0].set_title("Sector 1 Time Analysis")
    axes[0].set_xlabel("Lap Number")
    axes[0].set_ylabel("Time (s)")
    
    sns.lineplot(ax=axes[1], x="lap_number", y="sector_2_time", hue="driver_name", data=df)
    axes[1].set_title("Sector 2 Time Analysis")
    axes[1].set_xlabel("Lap Number")
    
    sns.lineplot(ax=axes[2], x="lap_number", y="sector_3_time", hue="driver_name", data=df)
    axes[2].set_title("Sector 3 Time Analysis")
    axes[2].set_xlabel("Lap Number")
    
    st.pyplot(fig)
    
def predict_lap_times(df):
    """
    Uses polynomial regression to predict lap times.
    """
    predicted_lap_times = {}
    for driver in df["driver_name"].unique():
        driver_df = df[df["driver_name"] == driver]
        x = driver_df["lap_number"].to_numpy()
        y = driver_df["lap_time"].to_numpy()
        
        if len(x) > 3:  # Ensure enough data for a meaningful polynomial fit
            poly = Polynomial.fit(x, y, 2)  # Quadratic regression
            y_pred = poly(x)
            predicted_lap_times[driver] = y_pred
        else:
            predicted_lap_times[driver] = y  # Default to actual times if not enough data
    
    df["predicted_lap_time"] = df.apply(lambda row: predicted_lap_times[row["driver_name"]][np.where(df["lap_number"] == row["lap_number"])[0][0]], axis=1)
    return df

def plot_actual_vs_predicted(df):
    """
    Compares actual and predicted lap times.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.lineplot(ax=ax, x="lap_number", y="lap_time", hue="driver_name", data=df, label="Actual Lap Time")
    sns.lineplot(ax=ax, x="lap_number", y="predicted_lap_time", hue="driver_name", data=df, linestyle="dashed", label="Predicted Lap Time")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time (s)")
    ax.set_title("Actual vs. Predicted Lap Times")
    ax.legend()
    st.pyplot(fig)

def plot_prediction_errors(df):
    """
    Analyzes residual errors between actual and predicted lap times.
    """
    df["error"] = df["lap_time"] - df["predicted_lap_time"]
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(ax=ax, x="error", hue="driver_name", data=df, kde=True, bins=20)
    ax.set_xlabel("Prediction Error (s)")
    ax.set_ylabel("Frequency")
    ax.set_title("Lap Time Prediction Errors")
    st.pyplot(fig)

# Fetch session data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM laps")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
selected_session = st.selectbox("Select Session", session_list if session_list else [0])

df = get_race_pace_data(selected_session)

if not df.empty:
    df = predict_lap_times(df)
    plot_actual_vs_predicted(df)
    plot_prediction_errors(df)
    
    st.write("### Race Pace Data with Predictions")
    st.dataframe(df)
else:
    st.warning("No race pace data available for this session.")
