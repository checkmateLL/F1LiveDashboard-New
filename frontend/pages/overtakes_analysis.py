# frontend/pages/overtakes_analysis.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler

st.set_page_config(layout="wide")

st.title("Overtakes Analysis (Optimized Query Execution & ID Handling)")

def get_overtakes_data(session_id):
    """
    Retrieves overtakes data for the given session, including sector and DRS usage.
    """
    session_id = int(session_id)  # Ensure session_id is integer
    query = """
        SELECT overtakes.lap_number, overtakes.sector, drivers.driver_name AS overtaking_driver, 
               overtakes.overtaken_driver, overtakes.overtake_position, overtakes.drs_used
        FROM overtakes
        JOIN drivers ON overtakes.driver_id = drivers.driver_id
        WHERE overtakes.session_id = ?
        ORDER BY overtakes.lap_number, overtakes.sector
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (session_id,))
    
    return df

def plot_overtakes_distribution(df):
    """
    Displays the number of overtakes per driver.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.countplot(ax=ax, y=df["overtaking_driver"], order=df["overtaking_driver"].value_counts().index)
    ax.set_xlabel("Number of Overtakes")
    ax.set_ylabel("Driver")
    ax.set_title("Total Overtakes Per Driver")
    st.pyplot(fig)

def plot_overtakes_timeline(df):
    """
    Visualizes overtakes over the course of the race.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    for driver in df["overtaking_driver"].unique():
        driver_df = df[df["overtaking_driver"] == driver]
        ax.scatter(driver_df["lap_number"], [driver] * len(driver_df), label=driver, s=100)
    ax.set_xlabel("Lap Number")
    ax.set_title("Overtakes Timeline")
    ax.legend()
    st.pyplot(fig)

def plot_sector_based_overtakes(df):
    """
    Shows overtakes per sector to analyze track sections where most overtakes happen.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.countplot(ax=ax, x=df["sector"], hue=df["overtaking_driver"])
    ax.set_xlabel("Sector")
    ax.set_ylabel("Number of Overtakes")
    ax.set_title("Overtakes Per Sector")
    ax.legend(title="Driver")
    st.pyplot(fig)

def plot_drs_overtakes(df):
    """
    Compares overtakes with and without DRS to measure its impact.
    """
    drs_counts = df["drs_used"].value_counts()
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(drs_counts, labels=["With DRS", "Without DRS"], autopct="%1.1f%%", colors=["red", "blue"])
    ax.set_title("DRS Impact on Overtakes")
    st.pyplot(fig)

# Fetch session data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM overtakes")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
selected_session = st.selectbox("Select Session", session_list if session_list else [0])

df = get_overtakes_data(selected_session)

if not df.empty:
    plot_overtakes_distribution(df)
    plot_overtakes_timeline(df)
    plot_sector_based_overtakes(df)
    plot_drs_overtakes(df)
    
    st.write("### Overtakes Data")
    st.dataframe(df)
else:
    st.warning("No overtakes data available for this session.")
