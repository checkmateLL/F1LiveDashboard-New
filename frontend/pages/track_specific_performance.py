# frontend/pages/track_specific_performance.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler
from sklearn.linear_model import LinearRegression

st.set_page_config(layout="wide")

st.title("Track-Specific Performance Analysis (Optimized Query Execution & ID Handling)")

def get_track_performance_data(track_name):
    """
    Retrieves lap times, tire usage, weather conditions, and telemetry for past races on the selected track.
    """
    query = """
        SELECT races.year, races.track_name, drivers.driver_name, results.classified_position AS final_position, 
               laps.lap_time, laps.compound, weather.track_temp, weather.air_temp, weather.wind_speed,
               telemetry.speed, telemetry.throttle, telemetry.brake
        FROM results
        JOIN races ON results.session_id = races.session_id
        JOIN drivers ON results.driver_id = drivers.driver_id
        JOIN laps ON results.driver_id = laps.driver_id AND results.session_id = laps.session_id
        JOIN weather ON races.session_id = weather.session_id
        JOIN telemetry ON laps.driver_id = telemetry.driver_id AND laps.lap_number = telemetry.lap_number AND laps.session_id = telemetry.session_id
        WHERE races.track_name = ?
        ORDER BY races.year, final_position
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (track_name,))
    
    return df

def plot_driver_performance_on_track(df):
    """
    Compares driver performance across multiple years at a specific track.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(ax=ax, x="year", y="final_position", hue="driver_name", data=df)
    ax.set_xlabel("Year")
    ax.set_ylabel("Final Position")
    ax.set_title("Driver Performance Across Years at Selected Track")
    st.pyplot(fig)

def plot_tire_usage_on_track(df):
    """
    Analyzes tire compound performance at the selected track.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(ax=ax, x="compound", y="lap_time", data=df)
    ax.set_xlabel("Tire Compound")
    ax.set_ylabel("Lap Time (s)")
    ax.set_title("Tire Performance at This Track")
    st.pyplot(fig)

def plot_weather_impact_on_performance(df):
    """
    Evaluates how weather conditions affected lap times at the selected track.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.scatterplot(ax=axes[0], x=df["track_temp"], y=df["lap_time"], alpha=0.5)
    axes[0].set_title("Track Temperature vs. Lap Time")
    axes[0].set_xlabel("Track Temperature (°C)")
    axes[0].set_ylabel("Lap Time (s)")
    
    sns.scatterplot(ax=axes[1], x=df["wind_speed"], y=df["lap_time"], alpha=0.5)
    axes[1].set_title("Wind Speed vs. Lap Time")
    axes[1].set_xlabel("Wind Speed (km/h)")
    
    st.pyplot(fig)

def plot_telemetry_impact_on_performance(df):
    """
    Analyzes how telemetry factors (speed, throttle, brake usage) affect lap performance.
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    sns.scatterplot(ax=axes[0], x=df["speed"], y=df["lap_time"], alpha=0.5)
    axes[0].set_title("Speed vs. Lap Time")
    axes[0].set_xlabel("Speed (km/h)")
    axes[0].set_ylabel("Lap Time (s)")
    
    sns.scatterplot(ax=axes[1], x=df["throttle"], y=df["lap_time"], alpha=0.5)
    axes[1].set_title("Throttle vs. Lap Time")
    axes[1].set_xlabel("Throttle (%)")
    
    sns.scatterplot(ax=axes[2], x=df["brake"], y=df["lap_time"], alpha=0.5)
    axes[2].set_title("Brake Usage vs. Lap Time")
    axes[2].set_xlabel("Brake Pressure (%)")
    
    st.pyplot(fig)

# Fetch available tracks
with get_db_handler() as db:
    tracks = db.execute_query("SELECT DISTINCT track_name FROM races")

track_list = [track["track_name"] for track in tracks if isinstance(track, dict) and "track_name" in track]
selected_track = st.selectbox("Select Track", track_list if track_list else ["Unknown Track"])

df = get_track_performance_data(selected_track)

if not df.empty:
    plot_driver_performance_on_track(df)
    plot_tire_usage_on_track(df)
    plot_weather_impact_on_performance(df)
    plot_telemetry_impact_on_performance(df)
    
    st.write("### Track-Specific Performance Data")
    st.dataframe(df)
else:
    st.warning("No data available for this track.")