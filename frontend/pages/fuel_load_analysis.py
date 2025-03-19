# frontend/pages/fuel_load_analysis.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler

st.set_page_config(layout="wide")

st.title("Fuel Load Impact Analysis (Optimized Query Execution & ID Handling)")

def get_fuel_load_data(session_id):
    """
    Retrieves fuel load data and lap performance impact.
    """
    session_id = int(session_id)  # Ensure session_id is integer
    query = """
        SELECT laps.lap_number, drivers.driver_name, laps.fuel_load, laps.lap_time
        FROM laps
        JOIN drivers ON laps.driver_id = drivers.driver_id
        WHERE laps.session_id = ?
        ORDER BY laps.lap_number, drivers.driver_name
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (session_id,))
    
    return df

def apply_fuel_correction(df):
    """
    Applies a fuel correction model to normalize lap times.
    """
    fuel_correction_factor = 0.035  # Estimated lap time loss per kg of fuel
    df["corrected_lap_time"] = df["lap_time"] - (df["fuel_load"] * fuel_correction_factor)
    return df

def plot_fuel_load_vs_lap_time(df):
    """
    Visualizes the effect of fuel load on lap times.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(ax=ax, x="fuel_load", y="lap_time", hue="driver_name", data=df, alpha=0.6)
    ax.set_xlabel("Fuel Load (kg)")
    ax.set_ylabel("Lap Time (s)")
    ax.set_title("Fuel Load vs. Lap Time")
    st.pyplot(fig)

def plot_actual_vs_corrected_lap_time(df):
    """
    Compares actual lap times vs. fuel-corrected lap times.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.lineplot(ax=ax, x="lap_number", y="lap_time", hue="driver_name", data=df, label="Actual Lap Time")
    sns.lineplot(ax=ax, x="lap_number", y="corrected_lap_time", hue="driver_name", data=df, linestyle="dashed", label="Fuel-Corrected Lap Time")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time (s)")
    ax.set_title("Actual vs. Fuel-Corrected Lap Times")
    ax.legend()
    st.pyplot(fig)

# Fetch session data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM laps")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
selected_session = st.selectbox("Select Session", session_list if session_list else [0])

df = get_fuel_load_data(selected_session)

if not df.empty:
    df = apply_fuel_correction(df)
    plot_fuel_load_vs_lap_time(df)
    plot_actual_vs_corrected_lap_time(df)
    
    st.write("### Fuel Load Data")
    st.dataframe(df)
else:
    st.warning("No fuel load data available for this session.")
