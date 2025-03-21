import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from backend.db_connection import get_db_handler

def fetch_sessions(db):
    """Fetch all available sessions grouped by event name."""
    query = """
    SELECT s.id AS session_id, e.event_name, s.name AS session_name, s.date
    FROM sessions s
    JOIN events e ON s.event_id = e.id
    ORDER BY s.date DESC;
    """
    return db.execute_query(query)

def fetch_lap_times(db, session_id):
    """Retrieve lap times from the database for the selected session."""
    query = """
    SELECT d.full_name, l.lap_number, l.lap_time, l.speed_fl, l.compound
    FROM laps l
    JOIN drivers d ON l.driver_id = d.id
    WHERE l.session_id = ?
    ORDER BY l.lap_number
    """
    return db.execute_query(query, params=(session_id,))

def fetch_telemetry(db, session_id, driver_name):
    """Retrieve telemetry data for a specific driver."""
    query = """
    SELECT t.time, t.speed, t.x, t.y
    FROM telemetry t
    JOIN drivers d ON t.driver_id = d.id
    WHERE t.session_id = ? AND d.full_name = ?
    ORDER BY t.time;
    """
    return db.execute_query(query, params=(session_id, driver_name))

def plot_time_vs_speed(telemetry_data, driver_name):
    """Plot Time vs Speed Graph."""
    plt.figure(figsize=(10, 5))
    plt.plot(telemetry_data['time'], telemetry_data['speed'], label=driver_name, linewidth=2)
    plt.xlabel("Time (s)")
    plt.ylabel("Speed (km/h)")
    plt.title("Lap Time Comparison (Time vs Speed)")
    plt.legend()
    plt.grid(True)
    st.pyplot(plt)

def plot_speed_vs_distance(telemetry_data, driver_name):
    """Plot Speed vs Distance Graph."""
    plt.figure(figsize=(10, 5))
    plt.plot(telemetry_data['x'], telemetry_data['speed'], label=driver_name, linewidth=2)
    plt.xlabel("Distance (track position)")
    plt.ylabel("Speed (km/h)")
    plt.title("Speed vs Distance")
    plt.legend()
    plt.grid(True)
    st.pyplot(plt)

def analytics():
    st.title("📊 F1 Data Analytics")

    try:
        with get_db_handler() as db:
            st.subheader("Select Event & Session")

            # Fetch available sessions
            session_options = fetch_sessions(db)

            if not session_options or (isinstance(session_options, pd.DataFrame) and session_options.empty):
                st.warning("No session available.")              
                return
            
            # Properly display event + session + date
            event_selection = [
                f"{row['event_name']} - {row['session_name']} ({row['date']})"
                for _, row in session_options.iterrows()
            ]
            selected_idx = st.selectbox("Select Event & Session", range(len(event_selection)), format_func=lambda x: event_selection[x])
            selected_session_id = session_options.iloc[selected_idx]["session_id"]

            # Select Analysis Type
            analysis_type = st.radio("Select Analysis Type", ["Lap Time Comparison", "Tyre Strategy", "Driver Performance"])

            if st.button("Generate Analysis"):
                if analysis_type == "Lap Time Comparison":
                    lap_times = fetch_lap_times(db, selected_session_id)
                    if not lap_times or (isinstance(lap_times, pd.DataFrame) and lap_times.empty):
                        st.warning("No lap data available.")
                    else:
                        st.subheader("Lap Time Comparison")
                        st.dataframe(lap_times)

                        # Allow user to pick two drivers for visualization
                        driver_options = lap_times["full_name"].unique()
                        driver1 = st.selectbox("Select Driver 1", driver_options)
                        driver2 = st.selectbox("Select Driver 2", driver_options)

                        if driver1 and driver2:
                            telemetry1 = fetch_telemetry(db, selected_session_id, driver1)
                            telemetry2 = fetch_telemetry(db, selected_session_id, driver2)

                            if ((isinstance(telemetry1, pd.DataFrame) and not telemetry1.empty) or (not isinstance(telemetry1, pd.DataFrame) and telemetry1)) and \
                            ((isinstance(telemetry2, pd.DataFrame) and not telemetry2.empty) or (not isinstance(telemetry2, pd.DataFrame) and telemetry2)):
                                st.subheader(f"Time vs Speed: {driver1} vs {driver2}")
                                plot_time_vs_speed(telemetry1, driver1)
                                plot_time_vs_speed(telemetry2, driver2)

                                st.subheader(f"Speed vs Distance: {driver1} vs {driver2}")
                                plot_speed_vs_distance(telemetry1, driver1)
                                plot_speed_vs_distance(telemetry2, driver2)

                elif analysis_type == "Tyre Strategy":
                    st.subheader("Tyre Strategy Analysis - Coming Soon")

                elif analysis_type == "Driver Performance":
                    st.subheader("Driver Performance Insights - Coming Soon")

    except Exception as e:
        st.error(f"Error loading analytics data: {e}")
