# frontend/pages/strategy_comparison_analysis.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler

st.set_page_config(layout="wide")

st.title("Strategy Comparison & Effectiveness Analysis (Optimized Query Execution & ID Handling)")

def get_strategy_data(session_id):
    """
    Retrieves pit stop strategies, tire compounds, fuel loads, and total race time using optimized query execution.
    """
    session_id = int(session_id)  # Ensure session_id is integer
    query = """
        SELECT drivers.driver_name, drivers.team_name, results.grid_position, results.classified_position, 
               results.total_race_time, pit_stops.total_stops, pit_stops.strategy_type, 
               laps.compound, laps.fuel_load, telemetry.speed, telemetry.throttle, telemetry.brake
        FROM results
        JOIN drivers ON results.driver_id = drivers.driver_id
        JOIN pit_stops ON results.driver_id = pit_stops.driver_id AND results.session_id = pit_stops.session_id
        JOIN laps ON results.driver_id = laps.driver_id AND results.session_id = laps.session_id
        JOIN telemetry ON laps.driver_id = telemetry.driver_id AND laps.lap_number = telemetry.lap_number AND laps.session_id = telemetry.session_id
        WHERE results.session_id = ?
        ORDER BY results.classified_position
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (session_id,))
    
    return df

def plot_strategy_vs_position(df):
    """
    Compares race strategy type vs final position.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(ax=ax, x="strategy_type", y="classified_position", data=df)
    ax.set_xlabel("Strategy Type")
    ax.set_ylabel("Final Position")
    ax.set_title("Effectiveness of Race Strategies")
    st.pyplot(fig)

def plot_pit_stops_vs_race_time(df):
    """
    Analyzes how pit stop count affects race time.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(ax=ax, x="total_stops", y="total_race_time", hue="strategy_type", data=df, s=100)
    ax.set_xlabel("Total Pit Stops")
    ax.set_ylabel("Total Race Time (s)")
    ax.set_title("Impact of Pit Stop Count on Race Time")
    st.pyplot(fig)

def plot_tire_compound_vs_performance(df):
    """
    Evaluates performance of tire compounds used in different strategies.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(ax=ax, x="compound", y="classified_position", data=df)
    ax.set_xlabel("Tire Compound")
    ax.set_ylabel("Final Position")
    ax.set_title("Tire Compound Performance Comparison")
    st.pyplot(fig)

def plot_fuel_usage_vs_performance(df):
    """
    Compares fuel load impact on race performance.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(ax=ax, x="fuel_load", y="classified_position", alpha=0.5)
    ax.set_xlabel("Average Fuel Load (kg)")
    ax.set_ylabel("Final Position")
    ax.set_title("Fuel Load Impact on Race Results")
    st.pyplot(fig)

def plot_telemetry_vs_performance(df):
    """
    Analyzes the relationship between speed, throttle, and braking with race outcomes.
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    sns.scatterplot(ax=axes[0], x=df["speed"], y=df["classified_position"], alpha=0.5)
    axes[0].set_title("Speed vs. Final Position")
    axes[0].set_xlabel("Speed (km/h)")
    axes[0].set_ylabel("Final Position")
    
    sns.scatterplot(ax=axes[1], x=df["throttle"], y=df["classified_position"], alpha=0.5)
    axes[1].set_title("Throttle vs. Final Position")
    axes[1].set_xlabel("Throttle (%)")
    
    sns.scatterplot(ax=axes[2], x=df["brake"], y=df["classified_position"], alpha=0.5)
    axes[2].set_title("Brake Usage vs. Final Position")
    axes[2].set_xlabel("Brake Pressure (%)")
    
    st.pyplot(fig)

# Fetch session data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM results")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
selected_session = st.selectbox("Select Session", session_list if session_list else [0])

df = get_strategy_data(selected_session)

if not df.empty:
    plot_strategy_vs_position(df)
    plot_pit_stops_vs_race_time(df)
    plot_tire_compound_vs_performance(df)
    plot_fuel_usage_vs_performance(df)
    plot_telemetry_vs_performance(df)
    
    st.write("### Strategy Effectiveness Data")
    st.dataframe(df)
else:
    st.warning("No strategy data available for this session.")