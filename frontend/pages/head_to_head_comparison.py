# frontend/pages/head_to_head_comparison.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler

st.set_page_config(layout="wide")

st.title("Head-to-Head Driver Comparison (Multi-Metric Analysis)")

def get_head_to_head_data(session_id, driver1_id, driver2_id):
    """
    Retrieves lap time comparison data between two drivers.
    """
    session_id = int(session_id)
    driver1_id = int(driver1_id)
    driver2_id = int(driver2_id)
    
    query = """
        SELECT laps.lap_number, drivers.driver_name, laps.lap_time
        FROM laps
        JOIN drivers ON laps.driver_id = drivers.driver_id
        WHERE laps.session_id = ? AND (laps.driver_id = ? OR laps.driver_id = ?)
        ORDER BY laps.lap_number, drivers.driver_name
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (session_id, driver1_id, driver2_id))
    
    return df

def plot_lap_time_comparison(df, driver1, driver2):
    """
    Compares lap times between two drivers.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.lineplot(ax=ax, x="lap_number", y="lap_time", hue="driver_name", data=df)
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time (s)")
    ax.set_title(f"Lap Time Comparison: {driver1} vs {driver2}")
    st.pyplot(fig)

def plot_sector_comparison(df):
    """
    Compares sector times between the two drivers.
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    sns.boxplot(ax=axes[0], x="driver_name", y="sector_1_time", data=df)
    axes[0].set_title("Sector 1 Time Comparison")
    
    sns.boxplot(ax=axes[1], x="driver_name", y="sector_2_time", data=df)
    axes[1].set_title("Sector 2 Time Comparison")
    
    sns.boxplot(ax=axes[2], x="driver_name", y="sector_3_time", data=df)
    axes[2].set_title("Sector 3 Time Comparison")
    
    st.pyplot(fig)

def plot_pit_stop_comparison(df):
    """
    Compares pit stop times between the two drivers.
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.barplot(ax=ax, x="driver_name", y="stop_time", data=df)
    ax.set_xlabel("Driver")
    ax.set_ylabel("Pit Stop Time (s)")
    ax.set_title("Pit Stop Performance Comparison")
    st.pyplot(fig)

def plot_overtake_comparison(df):
    """
    Compares overtakes made by both drivers.
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.countplot(ax=ax, x="driver_name", data=df, hue="overtake_position")
    ax.set_xlabel("Driver")
    ax.set_ylabel("Overtake Count")
    ax.set_title("Overtaking Comparison")
    st.pyplot(fig)

# Fetch session and driver data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM laps")
    drivers = db.execute_query("SELECT DISTINCT driver_id, driver_name FROM drivers")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
driver_dict = {int(driver["driver_id"]): driver["driver_name"] for driver in drivers if isinstance(driver, dict) and "driver_id" in driver}

selected_session = st.selectbox("Select Session", session_list if session_list else [0])
selected_driver1 = st.selectbox("Select Driver 1", driver_dict.keys(), format_func=lambda x: driver_dict[x])
selected_driver2 = st.selectbox("Select Driver 2", driver_dict.keys(), format_func=lambda x: driver_dict[x])

if selected_driver1 != selected_driver2:
    df = get_head_to_head_data(selected_session, selected_driver1, selected_driver2)
    
    if not df.empty:
        plot_lap_time_comparison(df)
        plot_sector_comparison(df)
        plot_pit_stop_comparison(df)
        plot_overtake_comparison(df)
        
        st.write("### Head-to-Head Data")
        st.dataframe(df)
    else:
        st.warning("No lap time data available for this session.")
else:
    st.warning("Please select two different drivers for comparison.")