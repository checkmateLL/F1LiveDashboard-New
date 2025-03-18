import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from frontend.components.telemetry_visuals import show_telemetry_chart, show_track_map
from backend.db_connection import get_db_handler

def telemetry():
    st.title("📡 Telemetry Analysis")
    
    
    try:

        with get_db_handler() as db:
             
            # Get available years from the database
            years_df = db.execute_query("SELECT DISTINCT year FROM events ORDER BY year DESC",)
            years = years_df['year'].tolist() if not years_df.empty else [2025, 2024, 2023]
            
            # Allow user to select a season
            if 'selected_year' in st.session_state:
                default_year_index = years.index(st.session_state['selected_year']) if st.session_state['selected_year'] in years else 0
            else:
                default_year_index = 0
                
            year = st.selectbox("Select Season", years, index=default_year_index)
            
            # Update session state
            st.session_state['selected_year'] = year
            
            # Get all events for the selected season
            events_df = db.execute_query(
                """
                SELECT id, round_number, country, location, official_event_name, 
                    event_name, event_date, event_format
                FROM events
                WHERE year = ?
                ORDER BY round_number
                """,                
                params=(year,)
            )
            
            # Allow user to select an event
            event_options = events_df['event_name'].tolist() if not events_df.empty else []
            
            if 'selected_event' in st.session_state and st.session_state['selected_event']:
                # Find the event name for the selected event ID
                event_id = st.session_state['selected_event']
                event_name_df = events_df[events_df['id'] == event_id]
                if not event_name_df.empty:
                    default_event = event_name_df['event_name'].iloc[0]
                    if default_event in event_options:
                        default_event_index = event_options.index(default_event)
                    else:
                        default_event_index = 0
                else:
                    default_event_index = 0
            else:
                default_event_index = 0
                
            selected_event_name = st.selectbox("Select Event", event_options, index=default_event_index)
            
            if not events_df.empty and selected_event_name:
                # Get the event ID
                event_id = events_df[events_df['event_name'] == selected_event_name]['id'].iloc[0]
                
                # Update session state
                st.session_state['selected_event'] = event_id
                
                # Get all sessions for this event
                sessions_df = db.execute_query(
                    """
                    SELECT id, name, date, session_type, total_laps
                    FROM sessions
                    WHERE event_id = ?
                    ORDER BY date
                    """,                    
                    params=(event_id,)
                )
                
                if not sessions_df.empty:
                    # Allow user to select a session
                    session_options = sessions_df['name'].tolist()
                    
                    if 'selected_session' in st.session_state and st.session_state['selected_session']:
                        # Find the session name for the selected session ID
                        session_id = st.session_state['selected_session']
                        session_name_df = sessions_df[sessions_df['id'] == session_id]
                        if not session_name_df.empty:
                            default_session = session_name_df['name'].iloc[0]
                            if default_session in session_options:
                                default_session_index = session_options.index(default_session)
                            else:
                                default_session_index = 0
                        else:
                            default_session_index = 0
                    else:
                        default_session_index = 0
                    
                    selected_session_name = st.selectbox("Select Session", session_options, index=default_session_index)
                    
                    # Get the session ID
                    session_id = sessions_df[sessions_df['name'] == selected_session_name]['id'].iloc[0]
                    
                    # Update session state
                    st.session_state['selected_session'] = session_id
                    
                    # Get drivers for this session
                    drivers_df = db.execute_query(
                        """
                        SELECT DISTINCT d.id, d.full_name as driver_name, d.abbreviation, 
                            t.name as team_name, t.team_color
                        FROM telemetry tel
                        JOIN drivers d ON tel.driver_id = d.id
                        JOIN teams t ON d.team_id = t.id
                        WHERE tel.session_id = ?
                        ORDER BY t.name, d.full_name
                        """,                        
                        params=(session_id,)
                    )
                    
                    if not drivers_df.empty:
                        # Allow user to select a driver
                        driver_options = drivers_df['driver_name'].tolist()
                        selected_driver = st.selectbox("Select Driver", driver_options)
                        
                        # Get the driver ID
                        driver_id = drivers_df[drivers_df['driver_name'] == selected_driver]['id'].iloc[0]
                        driver_abbr = drivers_df[drivers_df['driver_name'] == selected_driver]['abbreviation'].iloc[0]
                        driver_team_color = drivers_df[drivers_df['driver_name'] == selected_driver]['team_color'].iloc[0]
                        
                        # Get laps for this driver in this session
                        laps_df = db.execute_query(
                            """
                            SELECT DISTINCT lap_number
                            FROM telemetry
                            WHERE session_id = ? AND driver_id = ?
                            ORDER BY lap_number
                            """,                            
                            params=(session_id, driver_id)
                        )
                        
                        if not laps_df.empty:
                            # Allow user to select a lap
                            lap_options = laps_df['lap_number'].tolist()
                            selected_lap = st.selectbox("Select Lap", lap_options)
                            
                            # Add comparison option
                            st.subheader("Driver Comparison")
                            compare_enabled = st.checkbox("Compare with another driver")
                            
                            comparison_driver_id = None
                            if compare_enabled:
                                # Get other drivers
                                other_drivers = drivers_df[drivers_df['driver_name'] != selected_driver]
                                if not other_drivers.empty:
                                    comparison_driver = st.selectbox("Compare with", other_drivers['driver_name'].tolist())
                                    comparison_driver_id = other_drivers[other_drivers['driver_name'] == comparison_driver]['id'].iloc[0]
                            
                            # Get telemetry data
                            telemetry_df = db.execute_query(
                                """
                                SELECT time, session_time, speed, rpm, gear, throttle, brake, drs,
                                    x, y, z, d.full_name as driver_name, t.team_color
                                FROM telemetry tel
                                JOIN drivers d ON tel.driver_id = d.id
                                JOIN teams t ON d.team_id = t.id
                                WHERE tel.session_id = ? AND tel.driver_id = ? AND tel.lap_number = ?
                                ORDER BY tel.time
                                """,                                
                                params=(session_id, driver_id, selected_lap)
                            )
                            
                            # Get comparison telemetry if enabled
                            comparison_df = None
                            if compare_enabled and comparison_driver_id:
                                comparison_df = db.execute_query(
                                    """
                                    SELECT time, session_time, speed, rpm, gear, throttle, brake, drs,
                                        x, y, z, d.full_name as driver_name, t.team_color
                                    FROM telemetry tel
                                    JOIN drivers d ON tel.driver_id = d.id
                                    JOIN teams t ON d.team_id = t.id
                                    WHERE tel.session_id = ? AND tel.driver_id = ? AND tel.lap_number = ?
                                    ORDER BY tel.time
                                    """,                                    
                                    params=(session_id, comparison_driver_id, selected_lap)
                                )
                            
                            if not telemetry_df.empty:
                                # Create tabs for different telemetry views
                                tab1, tab2, tab3, tab4 = st.tabs(["Speed & Throttle", "Braking & DRS", "Gears", "Track Map"])
                                
                                with tab1:
                                    # Show speed telemetry
                                    show_telemetry_chart(telemetry_df, 'speed', "Speed Telemetry", comparison_df)
                                    
                                    # Show throttle telemetry
                                    show_telemetry_chart(telemetry_df, 'throttle', "Throttle Telemetry", comparison_df)
                                    
                                    # Show combined view (TODO)
                                
                                with tab2:
                                    # Show brake telemetry
                                    show_telemetry_chart(telemetry_df, 'brake', "Brake Telemetry", comparison_df)
                                    
                                    # Show DRS telemetry
                                    show_telemetry_chart(telemetry_df, 'drs', "DRS Telemetry", comparison_df)
                                    
                                    # Find DRS activation points
                                    drs_activations = []
                                    for i in range(1, len(telemetry_df)):
                                        if telemetry_df['drs'].iloc[i] > telemetry_df['drs'].iloc[i-1]:
                                            drs_activations.append(i)
                                    
                                    # Show DRS activation points on a speed chart
                                    fig = go.Figure()
                                    
                                    # Add the speed trace
                                    fig.add_trace(go.Scatter(
                                        x=telemetry_df['session_time'],
                                        y=telemetry_df['speed'],
                                        mode='lines',
                                        name='Speed',
                                        line=dict(color=driver_team_color, width=3)
                                    ))
                                    
                                    # Add DRS activation markers
                                    for idx in drs_activations:
                                        if idx < len(telemetry_df):
                                            fig.add_trace(go.Scatter(
                                                x=[telemetry_df['session_time'].iloc[idx]],
                                                y=[telemetry_df['speed'].iloc[idx]],
                                                mode='markers',
                                                marker=dict(
                                                    size=10,
                                                    color='green',
                                                    symbol='star'
                                                ),
                                                name='DRS Activation'
                                            ))
                                    
                                    # Update layout
                                    fig.update_layout(
                                        title="Speed and DRS Activation Points",
                                        xaxis_title="Time",
                                        yaxis_title="Speed (km/h)",
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        paper_bgcolor='rgba(0,0,0,0)',
                                        font=dict(color='white'),
                                        height=400
                                    )
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                                
                                with tab3:
                                    # Show gear shifts telemetry
                                    show_telemetry_chart(telemetry_df, 'gear', "Gear Shifts", comparison_df)
                                    
                                    # Show RPM telemetry
                                    show_telemetry_chart(telemetry_df, 'rpm', "Engine RPM", comparison_df)
                                    
                                    # Count gear shifts
                                    gear_shifts = 0
                                    for i in range(1, len(telemetry_df)):
                                        if telemetry_df['gear'].iloc[i] != telemetry_df['gear'].iloc[i-1]:
                                            gear_shifts += 1
                                    
                                    # Display gear statistics
                                    st.subheader("Gear Statistics")
                                    
                                    col1, col2, col3 = st.columns(3)
                                    
                                    col1.metric("Total Gear Shifts", gear_shifts)
                                    
                                    # Calculate time spent in each gear
                                    if 'gear' in telemetry_df.columns and 'time' in telemetry_df.columns:
                                        gear_times = {}
                                        
                                        for i in range(1, len(telemetry_df)):
                                            gear = telemetry_df['gear'].iloc[i]
                                            if pd.notna(gear):
                                                gear = int(gear)
                                                if gear not in gear_times:
                                                    gear_times[gear] = 0
                                                
                                                # Add time difference between points
                                                gear_times[gear] += 1  # Simplified as 1 unit per datapoint
                                        
                                        # Calculate percentage of time in each gear
                                        total_time = sum(gear_times.values())
                                        
                                        if total_time > 0:
                                            for gear, time in gear_times.items():
                                                gear_times[gear] = (time / total_time) * 100
                                            
                                            # Find most used gear
                                            most_used_gear = max(gear_times, key=gear_times.get)
                                            col2.metric("Most Used Gear", most_used_gear)
                                            col3.metric("% in Most Used Gear", f"{gear_times[most_used_gear]:.1f}%")
                                            
                                            # Create gear distribution chart
                                            gear_data = pd.DataFrame({
                                                'Gear': list(gear_times.keys()),
                                                'Percentage': list(gear_times.values())
                                            })
                                            
                                            fig = px.bar(
                                                gear_data,
                                                x='Gear',
                                                y='Percentage',
                                                title='Time Spent in Each Gear',
                                                color='Gear',
                                                color_continuous_scale=px.colors.sequential.Plasma
                                            )
                                            
                                            fig.update_layout(
                                                plot_bgcolor='rgba(0,0,0,0)',
                                                paper_bgcolor='rgba(0,0,0,0)',
                                                font=dict(color='white'),
                                                height=400
                                            )
                                            
                                            st.plotly_chart(fig, use_container_width=True)
                                
                                with tab4:
                                    # Show track map if x, y coordinates are available
                                    if 'x' in telemetry_df.columns and 'y' in telemetry_df.columns:
                                        # Find braking points (where brake > 0)
                                        braking_points = []
                                        for i in range(len(telemetry_df)):
                                            if pd.notna(telemetry_df['brake'].iloc[i]) and telemetry_df['brake'].iloc[i] > 0:
                                                braking_points.append((i, 'red', 'Braking Point'))
                                        
                                        # Show track map with highlighted points
                                        show_track_map(telemetry_df, braking_points)
                                        
                                        # Add description of the track map
                                        st.info("""
                                        **Track Map Legend:**
                                        - **Blue Line**: The racing line taken by the driver
                                        - **Red Points**: Braking points
                                        
                                        This visualization shows the driver's path around the track with key points highlighted.
                                        """)
                                    else:
                                        st.warning("Track map data (x, y coordinates) not available for this lap.")
                                    
                                    # Additional track statistics
                                    st.subheader("Lap Statistics")
                                    
                                    col1, col2, col3 = st.columns(3)
                                    
                                    # Calculate maximum speed
                                    max_speed = telemetry_df['speed'].max() if 'speed' in telemetry_df.columns else None
                                    if max_speed is not None:
                                        col1.metric("Maximum Speed", f"{max_speed:.1f} km/h")
                                    
                                    # Calculate average speed
                                    avg_speed = telemetry_df['speed'].mean() if 'speed' in telemetry_df.columns else None
                                    if avg_speed is not None:
                                        col2.metric("Average Speed", f"{avg_speed:.1f} km/h")
                                    
                                    # Count braking points
                                    braking_count = sum(1 for b in telemetry_df['brake'] if pd.notna(b) and b > 0)
                                    col3.metric("Braking Points", braking_count)
                            else:
                                st.warning("No telemetry data available for this lap.")
                        else:
                            st.warning("No lap data available for this driver in this session.")
                    else:
                        st.warning("No drivers with telemetry data found for this session.")
                else:
                    st.warning("No sessions available for this event.")
            else:
                st.info("Please select an event to view telemetry data.")
        
    except Exception as e:
        st.error(f"Error loading telemetry: {e}")