# frontend/pages/driver_performance_comparison.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler

st.set_page_config(layout="wide")

st.title("Driver Performance Comparison (Optimized Query Execution & ID Handling)")

def get_driver_performance_data(session_id, driver_ids):
    """
    Retrieves lap times, sector times, and overall race performance for selected drivers.
    """
    session_id = int(session_id)
    driver_ids = tuple(map(int, driver_ids))  # Ensure all driver IDs are integers
    
    query = """
        SELECT laps.lap_number, drivers.full_name, laps.lap_time, laps.sector_1_time, laps.sector_2_time, laps.sector_3_time
        FROM laps
        JOIN drivers ON laps.driver_id = drivers.driver_id
        WHERE laps.session_id = ? AND laps.driver_id IN ({})
        ORDER BY laps.lap_number, drivers.full_name
    """.format(','.join(['?']*len(driver_ids)))
    
    params = (session_id,) + driver_ids
    
    with get_db_handler() as db:
        df = db.execute_query(query, params)
    
    return df

def plot_lap_time_comparison(df):
    """
    Compares lap times between selected drivers.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.lineplot(ax=ax, x="lap_number", y="lap_time", hue="driver_name", data=df)
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time (s)")
    ax.set_title("Lap Time Comparison Between Selected Drivers")
    st.pyplot(fig)

def plot_sector_times(df):
    """
    Compares sector times between selected drivers.
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    sns.boxplot(ax=axes[0], x="driver_name", y="sector_1_time", data=df)
    axes[0].set_title("Sector 1 Time Comparison")
    
    sns.boxplot(ax=axes[1], x="driver_name", y="sector_2_time", data=df)
    axes[1].set_title("Sector 2 Time Comparison")
    
    sns.boxplot(ax=axes[2], x="driver_name", y="sector_3_time", data=df)
    axes[2].set_title("Sector 3 Time Comparison")
    
    st.pyplot(fig)

# Fetch session and driver data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM laps")
    drivers = db.execute_query("SELECT DISTINCT driver_id, full_name FROM drivers")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
driver_dict = {int(driver["driver_id"]): driver["driver_name"] for driver in drivers 
              if isinstance(driver, dict) and "driver_id" in driver and driver["driver_id"] and str(driver["driver_id"]).strip()}
selected_session = st.selectbox("Select Session", session_list if session_list else [0])
selected_drivers = st.multiselect("Select Drivers", driver_dict.keys(), format_func=lambda x: driver_dict[x])

if len(selected_drivers) >= 2:
    df = get_driver_performance_data(selected_session, selected_drivers)
    
    if not df or (isinstance(df, pd.DataFrame) and df.empty):
        plot_lap_time_comparison(df)
        plot_sector_times(df)
        
        st.write("### Driver Performance Data")
        st.dataframe(df)
    else:
        st.warning("No lap time data available for this session.")
else:
    st.warning("Please select at least two drivers for comparison.")
