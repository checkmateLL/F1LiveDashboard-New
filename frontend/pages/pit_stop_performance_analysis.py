# frontend/pages/pit_stop_performance_analysis.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler

st.set_page_config(layout="wide")

st.title("Pit Stop Performance Analysis (Optimized Query Execution & ID Handling)")

def get_pit_stop_data(session_id):
    """
    Retrieves pit stop times and effectiveness per driver by analyzing lap data.
    """
    session_id = int(session_id)  # Ensure session_id is integer
    query = """
        SELECT l.driver_id, d.full_name as driver_name, t.name as team_name, 
               l.lap_number, l.pit_in_time, l.pit_out_time,
               COUNT(DISTINCT l.stint) - 1 as total_stops,
               r.position as classified_position
        FROM laps l
        JOIN drivers d ON l.driver_id = d.id
        JOIN teams t ON d.team_id = t.id
        LEFT JOIN results r ON l.driver_id = r.driver_id AND l.session_id = r.session_id
        WHERE l.session_id = ? AND (l.pit_in_time IS NOT NULL OR l.pit_out_time IS NOT NULL)
        GROUP BY l.driver_id
        ORDER BY l.lap_number
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (session_id,))
    
    return df

def plot_pit_stop_times(df):
    """
    Visualizes pit stop duration per driver.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(ax=ax, x="driver_name", y="stop_time", data=df)
    ax.set_xlabel("Driver")
    ax.set_ylabel("Pit Stop Time (s)")
    ax.set_title("Pit Stop Times Per Driver")
    st.pyplot(fig)

def plot_pit_stop_counts(df):
    """
    Displays total pit stops per driver.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(ax=ax, x="driver_name", y="total_stops", hue="team_name", data=df)
    ax.set_xlabel("Driver")
    ax.set_ylabel("Total Pit Stops")
    ax.set_title("Pit Stops Per Driver")
    st.pyplot(fig)

def plot_pit_stop_effectiveness(df):
    """
    Analyzes correlation between pit stop count and final position.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(ax=ax, x="total_stops", y="classified_position", hue="driver_name", data=df, s=100)
    ax.set_xlabel("Total Pit Stops")
    ax.set_ylabel("Final Position")
    ax.set_title("Effectiveness of Pit Stops on Final Position")
    st.pyplot(fig)

# Fetch session data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM laps WHERE pit_in_time IS NOT NULL OR pit_out_time IS NOT NULL")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
selected_session = st.selectbox("Select Session", session_list if session_list else [0])

df = get_pit_stop_data(selected_session)

if not df.empty:
    plot_pit_stop_times(df)
    plot_pit_stop_counts(df)
    plot_pit_stop_effectiveness(df)
    
    st.write("### Pit Stop Performance Data")
    st.dataframe(df)
else:
    st.warning("No pit stop data available for this session.")
