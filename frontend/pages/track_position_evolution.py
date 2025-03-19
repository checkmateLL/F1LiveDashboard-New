# frontend/pages/track_position_evolution.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler

st.set_page_config(layout="wide")

st.title("Track Position Evolution with Heatmap (Optimized Query Execution & ID Handling)")

def get_track_position_data(session_id):
    """
    Retrieves telemetry data for track position heatmap visualization.
    """
    session_id = int(session_id)  # Ensure session_id is integer
    query = """
        SELECT telemetry.x, telemetry.y, telemetry.speed, drivers.driver_name
        FROM telemetry
        JOIN drivers ON telemetry.driver_id = drivers.driver_id
        WHERE telemetry.session_id = ?
        ORDER BY drivers.driver_name
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (session_id,))
    
    return df

def plot_track_position_heatmap(df):
    """
    Generates a heatmap of driver positions on track.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    heatmap, xedges, yedges = np.histogram2d(df["x"], df["y"], bins=(50, 50), weights=df["speed"])
    ax.imshow(heatmap.T, origin="lower", cmap="coolwarm", aspect="auto")
    ax.set_xlabel("X Position")
    ax.set_ylabel("Y Position")
    ax.set_title("Track Position Heatmap (Speed-Weighted)")
    st.pyplot(fig)

# Fetch session data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM telemetry")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
selected_session = st.selectbox("Select Session", session_list if session_list else [0])

df = get_track_position_data(selected_session)

if not df.empty:
    plot_track_position_heatmap(df)
    
    st.write("### Track Position Data")
    st.dataframe(df)
else:
    st.warning("No track position data available for this session.")
