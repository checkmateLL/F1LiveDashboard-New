import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

from frontend.components.countdown import get_next_event, display_countdown
from frontend.components.event_cards import event_card
from backend.db_connection import get_db_handler

def home():
    st.title("🏎️ F1 Dashboard - Home")    
    
    try:
        with get_db_handler() as db:

            # Get current year
            current_year = datetime.now().year
            
            # Fetch events for the current year
            events_df = db.execute_query(
                "SELECT id, round_number, country, location, official_event_name, event_name, event_date, event_format, year "
                "FROM events WHERE year = ? ORDER BY event_date",
                params=(current_year,)
            )
            
            # Get the next event for countdown
            next_event = get_next_event(events_df)
            
            # Display countdown timer for the next event
            if next_event:
                st.subheader("🏁 Next Race")
                display_countdown(next_event)
            
            # Create two columns for past and upcoming events
            col1, col2 = st.columns(2)
            
            # Get current date to compare
            today = datetime.now()
            
            # Filter past and upcoming events
            if 'event_date' in events_df.columns:
                events_df['event_date_dt'] = pd.to_datetime(events_df['event_date'], errors='coerce')
                past_events = events_df[events_df['event_date_dt'] < today].sort_values(by='event_date_dt', ascending=False)
                upcoming_events = events_df[events_df['event_date_dt'] >= today].sort_values(by='event_date_dt')
                
                # Display past events
                with col1:
                    st.subheader("Recent Events")
                    if len(past_events) > 0:
                        for _, event in past_events.head(3).iterrows():
                            event_dict = event.to_dict()
                            if event_card(event_dict, is_past=True):
                                # If card is clicked, navigate to race results page with this event pre-selected
                                st.session_state['selected_event'] = event_dict['id']
                                st.session_state['selected_year'] = current_year
                                st.session_state['page'] = 'Race Results'
                                st.experimental_rerun()
                    else:
                        st.info("No past events in the current season.")
                
                # Display upcoming events
                with col2:
                    st.subheader("Upcoming Events")
                    if len(upcoming_events) > 0:
                        for _, event in upcoming_events.head(3).iterrows():
                            event_dict = event.to_dict()
                            if event_card(event_dict, is_past=False):
                                # If card is clicked, navigate to analytics page with this event pre-selected
                                st.session_state['selected_event'] = event_dict['id']
                                st.session_state['selected_year'] = current_year
                                st.session_state['page'] = 'Analytics'
                                st.experimental_rerun()
                    else:
                        st.info("No upcoming events in the current season.")
            
            # Display summary information
            st.subheader("🏆 Current Season Overview")
            
            # Create metrics for the season
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
            
            # Get season metrics from database
            total_races = len(events_df)
            completed_races = len(past_events) if 'past_events' in locals() else 0
            
            # Get the current leader from driver standings
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
            
            current_leader = driver_standings['full_name'].iloc[0] if len(driver_standings) > 0 else "N/A"
            leader_team = driver_standings['team_name'].iloc[0] if len(driver_standings) > 0 else "N/A"
            leader_points = driver_standings['total_points'].iloc[0] if len(driver_standings) > 0 else 0
            
            metrics_col1.metric("Races Completed", f"{completed_races}/{total_races}")
            metrics_col2.metric("Championship Leader", current_leader)
            metrics_col3.metric("Leader Team", leader_team)
            metrics_col4.metric("Leader Points", leader_points)
        
    except Exception as e:
        st.error(f"Error loading home page data: {e}")    