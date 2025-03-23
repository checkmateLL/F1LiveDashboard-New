import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from collections import defaultdict
from backend.db_connection import get_db_handler

st.set_page_config(layout="wide")
st.title("🏎️ Driver Performance Comparison")

def get_driver_performance_data(session_id, driver_ids):
    session_id = int(session_id)
    driver_ids = tuple(map(int, driver_ids))

    query = """
        SELECT laps.lap_number, drivers.full_name AS driver_name,
               laps.lap_time, laps.sector1_time, laps.sector2_time, laps.sector3_time
        FROM laps
        JOIN drivers ON laps.driver_id = drivers.id
        WHERE laps.session_id = ? AND laps.driver_id IN ({})
        ORDER BY laps.lap_number, drivers.full_name
    """.format(','.join(['?']*len(driver_ids)))

    params = (session_id,) + driver_ids

    with get_db_handler() as db:
        df = pd.DataFrame(db.execute_query(query, params))

    # ✅ Convert timedelta to seconds (only for time-based columns)
    time_columns = ["lap_time", "sector1_time", "sector2_time", "sector3_time"]
    for col in time_columns:
        df[col] = pd.to_timedelta(df[col]).dt.total_seconds()

    return df

def plot_lap_time_comparison(df):
    """
    Creates a Plotly-based lap time comparison chart with dark theme.
    """
    fig = px.line(
        df,
        x="lap_number",
        y="lap_time",
        color="driver_name",
        title="Lap Time Comparison Between Selected Drivers",
        labels={"lap_time": "Lap Time (s)", "lap_number": "Lap Number", "driver_name": "Driver"},
    )

    fig.update_traces(line=dict(width=3))  # Thicker lines

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent background
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=500,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="gray"),
    )

    st.plotly_chart(fig, use_container_width=True)

def plot_sector_times(df):
    """
    Creates Plotly-based sector time comparison with unique colors.
    """
    sector_colors = ["#FF4C4C", "#FFD700", "#4CFF4C"]  # Red, Gold, Green

    fig = px.box(
        df,
        x="driver_name",
        y="sector1_time",
        color="driver_name",
        title="Sector 1 Time Comparison",
        labels={"sector1_time": "Sector 1 Time (s)", "driver_name": "Driver"},
        color_discrete_sequence=[sector_colors[0]]
    )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=500,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="gray"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Repeat for Sector 2 and Sector 3
    for i, sector in enumerate(["sector2_time", "sector3_time"]):
        fig = px.box(
            df,
            x="driver_name",
            y=sector,
            color="driver_name",
            title=f"{sector.replace('_', ' ').title()} Comparison",
            labels={sector: "Time (s)", "driver_name": "Driver"},
            color_discrete_sequence=[sector_colors[i+1]]
        )

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            height=500,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="gray"),
        )

        st.plotly_chart(fig, use_container_width=True)

# Fetch sessions and drivers
with get_db_handler() as db:
    session_data = db.execute_query("""
        SELECT s.id AS session_id, s.name AS session_name, s.event_id, e.event_name
        FROM sessions s
        JOIN events e ON s.event_id = e.id
        ORDER BY e.year DESC, s.date
    """)
    drivers = db.execute_query("SELECT DISTINCT id AS driver_id, full_name FROM drivers")

# Group sessions by event
event_sessions = defaultdict(list)
for s in session_data:
    event_sessions[s["event_name"]].append(s)

# Select Event
event_names = list(event_sessions.keys())
selected_event = st.selectbox("Select Event", event_names)

# Select Session
sessions_for_event = event_sessions[selected_event]
session_labels = [f'{s["session_name"]}' for s in sessions_for_event]
session_ids = [s["session_id"] for s in sessions_for_event]
selected_session_idx = st.selectbox("Select Session", range(len(session_ids)), format_func=lambda i: session_labels[i])
selected_session = session_ids[selected_session_idx]

# Select Drivers
driver_dict = {
    int(driver["driver_id"]): driver["full_name"]
    for driver in drivers
    if driver.get("driver_id") and driver.get("full_name")
}
selected_drivers = st.multiselect("Select Drivers", driver_dict.keys(), format_func=lambda x: driver_dict[x])

# Run visualizations
if len(selected_drivers) >= 2:
    df = get_driver_performance_data(selected_session, selected_drivers)
    
    if isinstance(df, pd.DataFrame) and not df.empty:
        plot_lap_time_comparison(df)
        plot_sector_times(df)
        st.write("### Driver Performance Data")
        st.dataframe(df)
    else:
        st.warning("No lap time data available for this session.")
else:
    st.warning("Please select at least two drivers for comparison.")