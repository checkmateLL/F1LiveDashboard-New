import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

from frontend.components.race_visuals import show_race_results, show_position_changes, show_points_distribution, show_race_summary

def race_results():
    st.title("🏁 Race Results")
    
    # Connect to the database
    conn = sqlite3.connect("f1_data_full_2025.db")
    
    try:
        # Get available years from the database
        years_df = pd.read_sql_query("SELECT DISTINCT year FROM events ORDER BY year DESC", conn)
        years = years_df['year'].tolist() if not years_df.empty else [2025, 2024, 2023]
        
        # Allow user to select a season
        # Use session state for persistence across page navigations
        if 'selected_year' in st.session_state:
            default_year_index = years.index(st.session_state['selected_year']) if st.session_state['selected_year'] in years else 0
        else:
            default_year_index = 0
            
        year = st.selectbox("Select Season", years, index=default_year_index)
        
        # Update session state
        st.session_state['selected_year'] = year
        
        # Get all events for the selected season
        events_df = pd.read_sql_query(
            """
            SELECT id, round_number, country, location, official_event_name, 
                   event_name, event_date, event_format
            FROM events
            WHERE year = ?
            ORDER BY round_number
            """,
            conn,
            params=(year,)
        )
        
        # Allow user to select an event
        event_options = events_df['event_name'].tolist() if not events_df.empty else []
        
        # If there's a selected event in session state, use it as default
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
            
            # Get all race sessions for this event
            sessions_df = pd.read_sql_query(
                """
                SELECT id, name, date, session_type, total_laps
                FROM sessions
                WHERE event_id = ? AND (session_type = 'race' OR session_type = 'sprint')
                ORDER BY date
                """,
                conn,
                params=(event_id,)
            )
            
            if not sessions_df.empty:
                # Allow user to select a session
                session_options = sessions_df['name'].tolist()
                
                # If there's a selected session in session state, use it as default
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
                
                # Get results for this session
                results_df = pd.read_sql_query(
                    """
                    SELECT r.position, r.grid_position, r.points, r.status, r.race_time,
                           d.full_name as driver_name, d.abbreviation, d.driver_number,
                           t.name as team_name, t.team_color
                    FROM results r
                    JOIN drivers d ON r.driver_id = d.id
                    JOIN teams t ON d.team_id = t.id
                    WHERE r.session_id = ?
                    ORDER BY r.position
                    """,
                    conn,
                    params=(session_id,)
                )
                
                if not results_df.empty:
                    # Create tabs for different views
                    tab1, tab2, tab3 = st.tabs(["Results Table", "Race Analysis", "Points & Stats"])
                    
                    with tab1:
                        # Display the results table
                        show_race_results(results_df)
                        
                        # Display race summary
                        show_race_summary(results_df)
                        
                    with tab2:
                        # Show position changes visualization
                        show_position_changes(results_df)
                        
                        # Add additional filters and visualizations
                        st.subheader("Filters")
                        
                        # Filter by team
                        teams = results_df['team_name'].unique().tolist()
                        selected_teams = st.multiselect("Filter by Teams", teams, default=teams)
                        
                        # Apply filters
                        filtered_results = results_df[results_df['team_name'].isin(selected_teams)]
                        
                        # Show filtered position changes
                        if not filtered_results.empty:
                            show_position_changes(filtered_results)
                        else:
                            st.warning("No data to display with the current filters.")
                        
                    with tab3:
                        # Show points distribution
                        show_points_distribution(results_df)
                        
                        # Show additional stats
                        st.subheader("Race Statistics")
                        
                        # Split into two columns
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Points by team
                            team_points = results_df.groupby('team_name')['points'].sum().reset_index()
                            team_points = team_points.sort_values('points', ascending=False)
                            
                            st.subheader("Team Points in this Race")
                            st.dataframe(team_points, use_container_width=True, hide_index=True)
                        
                        with col2:
                            # Status summary (finishers, retirements, etc.)
                            status_counts = results_df['status'].value_counts().reset_index()
                            status_counts.columns = ['Status', 'Count']
                            
                            st.subheader("Race Status Summary")
                            st.dataframe(status_counts, use_container_width=True, hide_index=True)
                else:
                    st.warning("No results available for this session.")
            else:
                st.warning("No race sessions available for this event.")
        else:
            st.info("Please select an event to view race results.")
    
    except Exception as e:
        st.error(f"Error loading race results: {e}")
    
    finally:
        conn.close()