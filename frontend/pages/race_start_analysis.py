# frontend/pages/race_start_analysis.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler

st.set_page_config(layout="wide")

st.title("Race Start Analysis & Position Gains/Losses (Optimized Query Execution & ID Handling)")

def get_race_start_data(session_id):
    """
    Retrieves starting and ending positions to analyze first-lap performance.
    """
    session_id = int(session_id)  # Ensure session_id is integer
    query = """
        SELECT drivers.driver_name, drivers.team_name, results.grid_position, 
               laps.lap_number, laps.position AS first_lap_position, results.classified_position
        FROM results
        JOIN drivers ON results.driver_id = drivers.driver_id
        JOIN laps ON results.driver_id = laps.driver_id AND results.session_id = laps.session_id
        WHERE results.session_id = ? AND laps.lap_number = 1
        ORDER BY results.grid_position
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (session_id,))
    
    df["first_lap_change"] = df["first_lap_position"] - df["grid_position"]
    df["race_position_change"] = df["classified_position"] - df["grid_position"]
    
    return df

def plot_start_position_changes(df):
    """
    Visualizes position gains/losses at the start of the race.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(ax=ax, x="first_lap_change", y="driver_name", hue="team_name", data=df, dodge=False)
    ax.set_xlabel("Position Change After First Lap")
    ax.set_ylabel("Driver")
    ax.set_title("First Lap Position Changes")
    st.pyplot(fig)

def plot_race_position_changes(df):
    """
    Visualizes overall position changes from start to finish.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(ax=ax, x="race_position_change", y="driver_name", hue="team_name", data=df, dodge=False)
    ax.set_xlabel("Total Position Change (Start to Finish)")
    ax.set_ylabel("Driver")
    ax.set_title("Race Position Changes")
    st.pyplot(fig)

def plot_team_start_performance(df):
    """
    Compares first-lap performance between teams.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(ax=ax, x="team_name", y="first_lap_change", data=df)
    ax.set_xlabel("Team")
    ax.set_ylabel("Average First Lap Position Change")
    ax.set_title("Team Start Performance Comparison")
    st.pyplot(fig)

# Fetch session data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM results")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
selected_session = st.selectbox("Select Session", session_list if session_list else [0])

df = get_race_start_data(selected_session)

if not df.empty:
    plot_start_position_changes(df)
    plot_race_position_changes(df)
    plot_team_start_performance(df)
    
    st.write("### Race Start Data")
    st.dataframe(df)
else:
    st.warning("No race start data available for this session.")