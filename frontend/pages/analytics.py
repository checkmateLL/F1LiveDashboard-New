import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

from frontend.components.countdown import get_next_event, display_countdown
from backend.db_connection import get_db_handler

def analytics():
    st.title("📊 F1 Data Analytics")    
    
    try:
        with get_db_handler() as db:

            # Get current year
            current_year = datetime.now().year
            
            # Get events for the current year
            events_df = db.execute_query(
                "SELECT id, round_number, country, location, official_event_name, event_name, event_date, event_format "
                "FROM events WHERE year = ? ORDER BY event_date",
                params=(current_year,)
            )
            
            # Create layout with two columns
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Historical Race Analysis")
                
                # Year selection
                years_df = db.execute_query("SELECT DISTINCT year FROM events ORDER BY year DESC")
                years = years_df['year'].tolist() if not years_df.empty else [2025, 2024, 2023]
                selected_year = st.selectbox("Select Season", years)
                
                # Event selection
                year_events = db.execute_query(
                    "SELECT id, round_number, event_name FROM events WHERE year = ? ORDER BY round_number",
                    
                    params=(selected_year,)
                )
                
                if not year_events.empty:
                    event_options = [(row['id'], f"Round {row['round_number']} - {row['event_name']}") 
                                    for _, row in year_events.iterrows()]
                    
                    # Use index and label for better display
                    event_labels = [label for _, label in event_options]
                    event_indices = [idx for idx, _ in enumerate(event_options)]
                    
                    selected_event_idx = st.selectbox("Select Event", event_indices, format_func=lambda x: event_labels[x])
                    selected_event_id = event_options[selected_event_idx][0]
                    
                    # Session selection
                    sessions = db.execute_query(
                        "SELECT id, name, session_type FROM sessions WHERE event_id = ? ORDER BY date",
                        
                        params=(selected_event_id,)
                    )
                    
                    if not sessions.empty:
                        session_options = [(int(row['id']), f"{row['name']} ({row['session_type'].capitalize()})") 
                                        for _, row in sessions.iterrows()]
                        
                        # Use index and label for better display
                        session_labels = [label for _, label in session_options]
                        session_indices = [idx for idx, _ in enumerate(session_options)]
                        
                        selected_session_idx = st.selectbox("Select Session", session_indices, format_func=lambda x: session_labels[x])
                        selected_session_id = int(session_options[selected_session_idx][0])  # Ensure int conversion
                        
                        # Display analysis options
                        analysis_type = st.radio(
                            "Select Analysis Type",
                            ["Lap Time Comparison", "Tyre Strategy", "Driver Performance", "Race Pace"]
                        )
                        
                        if st.button("Generate Analysis"):
                            st.info(f"Analysis for {session_labels[selected_session_idx]} will be displayed here.")
                            st.session_state['selected_session'] = selected_session_id
                            
                            # Redirect to appropriate analysis page
                            if analysis_type == "Lap Time Comparison":
                                st.session_state['page'] = 'Lap Times'
                                st.experimental_rerun()
                            elif analysis_type == "Driver Performance":
                                st.session_state['page'] = 'Performance Analysis'
                                st.experimental_rerun()
                            elif analysis_type == "Tyre Strategy":
                                st.session_state['page'] = 'Performance Analysis'
                                st.experimental_rerun()
                            else:
                                # Show placeholder for now
                                st.write("This analysis type is under development.")
                    else:
                        st.warning("No session data found for the selected event.")
                else:
                    st.warning("No events found for the selected year.")
            
            with col2:
                # Next event countdown
                next_event = get_next_event(events_df)
                if next_event:
                    st.subheader("Next Race Event")
                    display_countdown(next_event)
                
                # Quick stats
                st.subheader("Season Stats")
                
                try:
                    # Get championship leader
                    driver_standings = db.execute_query("""
                        SELECT d.full_name, t.name as team_name, SUM(r.points) as total_points
                        FROM results r
                        JOIN drivers d ON r.driver_id = d.id
                        JOIN teams t ON d.team_id = t.id
                        JOIN sessions s ON r.session_id = s.id
                        JOIN events e ON s.event_id = e.id
                        WHERE e.year = ? AND s.session_type = 'race'
                        GROUP BY d.id
                        ORDER BY total_points DESC
                        LIMIT 1
                    """, params=(current_year,))
                    
                    if not driver_standings.empty:
                        st.metric("Championship Leader", 
                                driver_standings['full_name'].iloc[0])
                        st.metric("Leader's Team", 
                                driver_standings['team_name'].iloc[0])
                        st.metric("Leader's Points", 
                                driver_standings['total_points'].iloc[0])
                except Exception as e:
                    st.error(f"Error loading stats: {e}")
    
    except Exception as e:
        st.error(f"Error loading analytics data: {e}")
        