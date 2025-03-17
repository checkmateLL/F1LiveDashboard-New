import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# Inject custom CSS for dark mode with neon accents
st.markdown(
    """
    <style>
    /* Set background to dark and text to neon colors */
    .reportview-container {
        background-color: #121212;
        color: #E0E0E0;
    }
    .sidebar .sidebar-content {
        background-color: #1E1E1E;
    }
    .stButton>button {
        background-color: #00ff99;
        color: #121212;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Set page config
st.set_page_config(page_title="F1 Dashboard", layout="wide", initial_sidebar_state="expanded")

# Utility function: get a connection to your SQLite database.
def get_connection(db_path="./f1_data.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Page 1: Season Overview (Events & Sessions)
def page_overview():
    st.title("Season Overview")
    conn = get_connection()
    # Query available years from events table
    years = pd.read_sql_query("SELECT DISTINCT year FROM events ORDER BY year DESC", conn)
    year = st.selectbox("Select Season", years["year"].tolist())
    
    # Query events for the season
    events = pd.read_sql_query(
        "SELECT round_number, event_name, event_date FROM events WHERE year = ? ORDER BY round_number",
        conn,
        params=(year,)
    )
    st.subheader("Event Schedule")
    st.dataframe(events)
    
    # If an event is selected, show sessions
    selected_event = st.selectbox("Select Event", events["event_name"].tolist())
    if selected_event:
        event_id = pd.read_sql_query(
            "SELECT id FROM events WHERE year = ? AND event_name = ?",
            conn,
            params=(year, selected_event)
        )["id"].iloc[0]
        sessions = pd.read_sql_query(
            "SELECT name, date, session_type FROM sessions WHERE event_id = ?",
            conn,
            params=(event_id,)
        )
        st.subheader("Sessions")
        st.dataframe(sessions)
    conn.close()

# Page 2: Race Results
def page_results():
    st.title("Race Results")
    conn = get_connection()
    years = pd.read_sql_query("SELECT DISTINCT year FROM events ORDER BY year DESC", conn)
    year = st.selectbox("Select Season", years["year"].tolist(), key="res_year")
    events = pd.read_sql_query(
        "SELECT id, event_name FROM events WHERE year = ? ORDER BY round_number",
        conn,
        params=(year,)
    )
    selected_event = st.selectbox("Select Event", events["event_name"].tolist(), key="res_event")
    if selected_event:
        event_id = events[events["event_name"] == selected_event]["id"].iloc[0]
        sessions = pd.read_sql_query(
            "SELECT id, name, session_type FROM sessions WHERE event_id = ? ORDER BY session_type",
            conn,
            params=(event_id,)
        )
        selected_session = st.selectbox("Select Session", sessions["name"].tolist(), key="res_session")
        if selected_session:
            session_id = sessions[sessions["name"] == selected_session]["id"].iloc[0]
            # Get results with driver names and team info
            query = """
            SELECT r.position, r.grid_position, r.status, r.points,
                   d.full_name AS driver_name, d.driver_number, d.abbreviation,
                   t.name AS team_name, t.team_color
            FROM results r
            JOIN drivers d ON r.driver_id = d.id
            JOIN teams t ON d.team_id = t.id
            WHERE r.session_id = ?
            ORDER BY r.position
            """
            results = pd.read_sql_query(query, conn, params=(session_id,))
            st.subheader("Results")
            st.dataframe(results)
    conn.close()

# Page 3: Lap Times
def page_lap_times():
    st.title("Lap Times")
    conn = get_connection()
    years = pd.read_sql_query("SELECT DISTINCT year FROM events ORDER BY year DESC", conn)
    year = st.selectbox("Select Season", years["year"].tolist(), key="lap_year")
    events = pd.read_sql_query(
        "SELECT id, event_name FROM events WHERE year = ? ORDER BY round_number",
        conn,
        params=(year,)
    )
    selected_event = st.selectbox("Select Event", events["event_name"].tolist(), key="lap_event")
    if selected_event:
        event_id = events[events["event_name"] == selected_event]["id"].iloc[0]
        sessions = pd.read_sql_query(
            "SELECT id, name FROM sessions WHERE event_id = ? ORDER BY session_type",
            conn,
            params=(event_id,)
        )
        selected_session = st.selectbox("Select Session", sessions["name"].tolist(), key="lap_session")
        if selected_session:
            session_id = sessions[sessions["name"] == selected_session]["id"].iloc[0]
            # Join laps with drivers and teams to get driver number and team color
            query = """
            SELECT l.lap_number, l.lap_time, d.driver_number, d.abbreviation, t.team_color
            FROM laps l
            JOIN drivers d ON l.driver_id = d.id
            JOIN teams t ON d.team_id = t.id
            WHERE l.session_id = ?
            ORDER BY d.abbreviation, l.lap_number
            """
            laps = pd.read_sql_query(query, conn, params=(session_id,))
            st.subheader("Lap Times")
            st.dataframe(laps)
            # Convert lap_time string to seconds if possible (assumes format "0 days HH:MM:SS.micro")
            def to_seconds(ts):
                try:
                    parts = ts.split()
                    h, m, s = parts[2].split(":")
                    return int(h)*3600 + int(m)*60 + float(s)
                except Exception:
                    return None
            laps["lap_time_sec"] = laps["lap_time"].apply(lambda ts: to_seconds(ts) if ts else None)
            # Create a scatter plot: x=lap number, y=lap time (s), colored by driver/team color
            fig = px.scatter(
                laps,
                x="lap_number",
                y="lap_time_sec",
                color="team_color",
                hover_data=["driver_number", "abbreviation"],
                template="plotly_dark",
                title="Lap Times (in seconds)"
            )
            st.plotly_chart(fig, use_container_width=True)
    conn.close()

# Page 4: Telemetry Analysis
def page_telemetry():
    st.title("Telemetry Analysis")
    conn = get_connection()
    years = pd.read_sql_query("SELECT DISTINCT year FROM events ORDER BY year DESC", conn)
    year = st.selectbox("Select Season", years["year"].tolist(), key="tel_year")
    events = pd.read_sql_query(
        "SELECT id, event_name FROM events WHERE year = ? ORDER BY round_number",
        conn,
        params=(year,)
    )
    selected_event = st.selectbox("Select Event", events["event_name"].tolist(), key="tel_event")
    if selected_event:
        event_id = events[events["event_name"] == selected_event]["id"].iloc[0]
        sessions = pd.read_sql_query(
            "SELECT id, name FROM sessions WHERE event_id = ? ORDER BY session_type",
            conn,
            params=(event_id,)
        )
        selected_session = st.selectbox("Select Session", sessions["name"].tolist(), key="tel_session")
        if selected_session:
            session_id = sessions[sessions["name"] == selected_session]["id"].iloc[0]
            # Let user choose a driver from telemetry data (assume drivers who have telemetry)
            drivers = pd.read_sql_query("""
                SELECT DISTINCT d.abbreviation, d.driver_number, d.full_name, t.team_color
                FROM telemetry tel
                JOIN drivers d ON tel.driver_id = d.id
                JOIN teams t ON d.team_id = t.id
                WHERE tel.session_id = ?
            """, conn, params=(session_id,))
            if not drivers.empty:
                driver_choice = st.selectbox("Select Driver", drivers["abbreviation"].tolist(), key="tel_driver")
                laps = pd.read_sql_query("""
                    SELECT DISTINCT lap_number FROM telemetry
                    WHERE session_id = ? AND driver_id = (
                        SELECT id FROM drivers WHERE abbreviation = ? AND year = ?
                    )
                    ORDER BY lap_number
                """, conn, params=(session_id, driver_choice, year))
                if not laps.empty:
                    lap_choice = st.selectbox("Select Lap", laps["lap_number"].tolist(), key="tel_lap")
                    tel_data = pd.read_sql_query("""
                        SELECT time, session_time, speed, rpm, gear, throttle, brake, drs
                        FROM telemetry
                        WHERE session_id = ? AND lap_number = ? AND driver_id = (
                            SELECT id FROM drivers WHERE abbreviation = ? AND year = ?
                        )
                        ORDER BY time
                    """, conn, params=(session_id, lap_choice, driver_choice, year))
                    st.subheader("Telemetry Data")
                    st.dataframe(tel_data)
                    if not tel_data.empty:
                        fig = px.line(
                            tel_data,
                            x="time",
                            y="speed",
                            title=f"Speed vs Time for {driver_choice} (Lap {lap_choice})",
                            template="plotly_dark"
                        )
                        st.plotly_chart(fig, use_container_width=True)
    conn.close()

# Main: Sidebar navigation
def main():
    st.sidebar.title("F1 Dashboard Navigation")
    pages = {
        "Season Overview": page_overview,
        "Race Results": page_results,
        "Lap Times": page_lap_times,
        "Telemetry Analysis": page_telemetry
    }
    choice = st.sidebar.radio("Select Page", list(pages.keys()))
    pages[choice]()

if __name__ == "__main__":
    main()
