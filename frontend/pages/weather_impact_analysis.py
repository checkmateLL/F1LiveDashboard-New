# frontend/pages/weather_impact_analysis.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler

st.set_page_config(layout="wide")

st.title("Weather Impact on Tire Performance and Race Strategy")

def get_weather_impact_data(session_id):
    """
    Retrieves weather conditions and their impact on lap times.
    """
    session_id = int(session_id)  # Ensure session_id is integer
    query = """
        SELECT laps.lap_number, drivers.driver_name, laps.lap_time, 
               weather.track_temp, weather.air_temp, weather.humidity, weather.wind_speed
        FROM laps
        JOIN drivers ON laps.driver_id = drivers.driver_id
        JOIN weather ON laps.session_id = weather.session_id
        WHERE laps.session_id = ?
        ORDER BY laps.lap_number, drivers.driver_name
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (session_id,))
    
    return df

def plot_weather_vs_lap_time(df, weather_metric, label):
    """
    Visualizes the relationship between a specific weather metric and lap time.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(ax=ax, x=df[weather_metric], y=df["lap_time"], hue=df["driver_name"], alpha=0.6)
    ax.set_xlabel(label)
    ax.set_ylabel("Lap Time (s)")
    ax.set_title(f"{label} vs. Lap Time")
    st.pyplot(fig)

def plot_weather_trends(df):
    """
    Shows how weather conditions changed over the race.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    sns.lineplot(ax=axes[0, 0], x="lap_number", y="track_temp", data=df)
    axes[0, 0].set_title("Track Temperature Over Laps")
    
    sns.lineplot(ax=axes[0, 1], x="lap_number", y="air_temp", data=df)
    axes[0, 1].set_title("Air Temperature Over Laps")
    
    sns.lineplot(ax=axes[1, 0], x="lap_number", y="humidity", data=df)
    axes[1, 0].set_title("Humidity Over Laps")
    
    sns.lineplot(ax=axes[1, 1], x="lap_number", y="wind_speed", data=df)
    axes[1, 1].set_title("Wind Speed Over Laps")
    
    st.pyplot(fig)

def plot_tire_performance_by_weather(df):
    """
    Compares lap times by tire compound under different weather conditions.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(ax=ax, x="compound", y="lap_time", hue=df["track_temp"].round(-1), data=df)
    ax.set_xlabel("Tire Compound")
    ax.set_ylabel("Lap Time (s)")
    ax.set_title("Tire Performance vs. Track Temperature")
    st.pyplot(fig)

def suggest_optimal_tires(df):
    """
    Suggests best tire strategy based on weather impact.
    """
    avg_times = df.groupby("compound")["lap_time"].mean().sort_values()
    best_tire = avg_times.idxmin()
    st.subheader("Optimal Tire Choice Based on Weather Conditions")
    st.write(f"🚀 Recommended Tire: **{best_tire}** for current weather conditions.")
    
# Fetch session data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM weather")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
selected_session = st.selectbox("Select Session", session_list if session_list else [0])

df = get_weather_impact_data(selected_session)

if not df.empty:
    plot_weather_vs_lap_time(df, "track_temp", "Track Temperature (°C)")
    plot_weather_vs_lap_time(df, "air_temp", "Air Temperature (°C)")
    plot_weather_vs_lap_time(df, "humidity", "Humidity (%)")
    plot_weather_vs_lap_time(df, "wind_speed", "Wind Speed (km/h)")
    plot_weather_trends(df)
    
    st.write("### Weather Impact Data")
    st.dataframe(df)
else:
    st.warning("No weather data available for this session.")
