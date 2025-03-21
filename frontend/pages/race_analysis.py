import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError, ResourceNotFoundError

# Initialize data service
data_service = F1DataService()

def is_data_empty(data):
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def convert_time_to_seconds(time_str):
    """Convert lap time strings to seconds."""
    if not time_str or pd.isna(time_str):
        return None
    
    try:
        # Handle different time string formats
        if isinstance(time_str, str):
            parts = time_str.split()
            if len(parts) >= 3:
                time_part = parts[2]
                if ":" in time_part:
                    time_sections = time_part.split(":")
                    if len(time_sections) == 3:  # hours:minutes:seconds
                        return int(time_sections[0]) * 3600 + int(time_sections[1]) * 60 + float(time_sections[2])
                    elif len(time_sections) == 2:  # minutes:seconds
                        return int(time_sections[0]) * 60 + float(time_sections[1])
            elif ":" in time_str:
                time_sections = time_str.split(":")
                if len(time_sections) == 2:  # minutes:seconds
                    return int(time_sections[0]) * 60 + float(time_sections[1])
        
        # Try direct conversion if it's a number
        return float(time_str)
    except (ValueError, IndexError, TypeError):
        return None

def format_seconds_to_time(seconds):
    """Format seconds to MM:SS.ms format."""
    if seconds is None or pd.isna(seconds):
        return "N/A"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes:02}:{remaining_seconds:06.3f}"

def race_analysis():
    """Race Analysis Dashboard"""
    try:
        # Get available years from the database
        years = data_service.get_available_years()
        
        # Make sure years is a list
        if not isinstance(years, list):
            try:
                years = [row['year'] for row in years]
            except:
                years = [2025]  # Default if we can't process
                
        if len(years) == 0:
            st.warning("No years available in the database.")
            return
        
        # Get the default year from session state or use the first year
        default_year = st.session_state.get("selected_year", years[0])
        
        # Make sure default_year is in years
        if default_year not in years:
            default_year = years[0]
            
        # Year selection
        year = st.selectbox("Select Season", years, index=years.index(default_year))
        st.session_state["selected_year"] = year

        # Get events for the selected year
        events = data_service.get_events(year)
        
        if is_data_empty(events):
            st.warning("No events available for this season.")
            return
            
        # Convert to DataFrame if needed
        if not isinstance(events, pd.DataFrame):
            try:
                events_df = pd.DataFrame(events)
            except:
                st.warning("Could not process events data.")
                return
        else:
            events_df = events
            
        # Create event options
        event_options = {}
        for idx, event in events_df.iterrows():
            event_options[event['event_name']] = event['id']
            
        if not event_options:
            st.warning("No events available.")
            return
            
        # Default to event stored in session state or first event
        default_event_id = st.session_state.get("selected_event", None)
        default_index = 0
        
        if default_event_id is not None:
            # Find the index of the default event
            event_ids = list(event_options.values())
            if default_event_id in event_ids:
                default_index = event_ids.index(default_event_id)
        
        # Event selection
        selected_event = st.selectbox(
            "Select Event", 
            options=list(event_options.keys()),
            index=default_index
        )
        event_id = event_options[selected_event]
        st.session_state["selected_event"] = event_id

        # Get sessions for the selected event
        sessions = data_service.get_sessions(event_id)
        
        if is_data_empty(sessions):
            st.warning("No sessions available for this event.")
            return
            
        # Convert to DataFrame if needed
        if not isinstance(sessions, pd.DataFrame):
            try:
                sessions_df = pd.DataFrame(sessions)
            except:
                st.warning("Could not process sessions data.")
                return
        else:
            sessions_df = sessions
            
        # Create session options
        session_options = {}
        for idx, session in sessions_df.iterrows():
            session_options[session['name']] = session['id']
            
        if not session_options:
            st.warning("No sessions available.")
            return
            
        # Default to session stored in session state or first session
        default_session_id = st.session_state.get("selected_session", None)
        default_session_index = 0
        
        if default_session_id is not None:
            # Find the index of the default session
            session_ids = list(session_options.values())
            if default_session_id in session_ids:
                default_session_index = session_ids.index(default_session_id)
        
        # Session selection
        selected_session = st.selectbox(
            "Select Session", 
            options=list(session_options.keys()),
            index=default_session_index
        )
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        # Get lap data
        laps_df = data_service.get_lap_times(session_id)
        
        if is_data_empty(laps_df):
            st.warning("No lap data available for this session.")
            return
            
        # Convert to DataFrame if needed
        if not isinstance(laps_df, pd.DataFrame):
            try:
                laps_df = pd.DataFrame(laps_df)
            except:
                st.warning("Could not process lap data.")
                return
        
        # Convert time values
        laps_df['lap_time_sec'] = laps_df['lap_time'].apply(convert_time_to_seconds)
        
        # Handle sector time columns with proper error checking
        if 'sector1_time' in laps_df.columns:
            laps_df['sector1_sec'] = laps_df['sector1_time'].apply(convert_time_to_seconds)
        elif 'sector_1_time' in laps_df.columns:
            laps_df['sector1_sec'] = laps_df['sector_1_time'].apply(convert_time_to_seconds)
            
        if 'sector2_time' in laps_df.columns:
            laps_df['sector2_sec'] = laps_df['sector2_time'].apply(convert_time_to_seconds)
        elif 'sector_2_time' in laps_df.columns:
            laps_df['sector2_sec'] = laps_df['sector_2_time'].apply(convert_time_to_seconds)
            
        if 'sector3_time' in laps_df.columns:
            laps_df['sector3_sec'] = laps_df['sector3_time'].apply(convert_time_to_seconds)
        elif 'sector_3_time' in laps_df.columns:
            laps_df['sector3_sec'] = laps_df['sector_3_time'].apply(convert_time_to_seconds)

        # Race Analysis Tabs
        tabs = st.tabs(["Lap Time Analysis", "Tire Strategy", "Driver Comparison", "Sector Analysis", "Telemetry Analysis", "Race Overview"])

        # TAB 1: LAP TIME ANALYSIS
        with tabs[0]:
            show_lap_time_analysis(laps_df)

        # TAB 2: TIRE STRATEGY
        with tabs[1]:
            show_tire_strategy_analysis(laps_df)

        # TAB 3: DRIVER COMPARISON
        with tabs[2]:
            show_driver_comparison(laps_df)

        # TAB 4: SECTOR ANALYSIS
        with tabs[3]:
            show_sector_analysis(laps_df)

        # TAB 5: TELEMETRY
        with tabs[4]:
            show_telemetry_analysis(session_id)

        # TAB 6: RACE OVERVIEW
        with tabs[5]:
            show_race_overview(laps_df)

    except Exception as e:
        st.error(f"Error in race analysis: {e}")

def show_lap_time_analysis(laps_df):
    """Show lap time analysis visualization."""
    st.subheader("Lap Time Analysis")
    
    if is_data_empty(laps_df):
        st.warning("No lap data available.")
        return
        
    if 'driver_name' not in laps_df.columns:
        st.warning("Driver information missing in lap data.")
        return
        
    drivers = laps_df['driver_name'].unique().tolist()
    selected_drivers = st.multiselect("Select Drivers", drivers, default=drivers[:5] if len(drivers) >= 5 else drivers)
    
    if not selected_drivers:
        st.warning("Please select at least one driver to analyze.")
        return
    
    filtered_df = laps_df[laps_df['driver_name'].isin(selected_drivers)]
    view_type = st.radio("View Type", ["Lap Time Evolution", "Lap Time Distribution", "Gap to Fastest Lap"])

    if view_type == "Lap Time Evolution":
        if 'lap_time_sec' not in filtered_df.columns or 'lap_number' not in filtered_df.columns:
            st.warning("Required lap time data missing.")
            return
            
        try:
            fig = go.Figure()
            for driver in selected_drivers:
                driver_data = filtered_df[filtered_df['driver_name'] == driver]
                
                if is_data_empty(driver_data):
                    continue
                    
                team_color = driver_data['team_color'].iloc[0] if 'team_color' in driver_data.columns else "#CCCCCC"
                
                fig.add_trace(go.Scatter(
                    x=driver_data['lap_number'],
                    y=driver_data['lap_time_sec'],
                    mode='lines+markers',
                    name=driver,
                    line=dict(color=f"#{team_color}" if not team_color.startswith('#') else team_color, width=2),
                ))
    
            fig.update_layout(
                title="Lap Time Evolution", 
                xaxis_title="Lap Number", 
                yaxis_title="Lap Time (seconds)",
                height=600,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating lap time evolution chart: {e}")

# Other analysis functions would be implemented similarly
# I've shown the pattern for handling the data safely with error checking

def show_tire_strategy_analysis(laps_df):
    """Show tire strategy analysis."""
    st.subheader("Tire Strategy Analysis")
    st.info("Tire strategy analysis would be displayed here.")
    # Implement similar to show_lap_time_analysis with proper error handling

def show_driver_comparison(laps_df):
    """Show driver comparison visualization."""
    st.subheader("Driver Comparison")
    st.info("Driver comparison analysis would be displayed here.")
    # Implement similar to show_lap_time_analysis with proper error handling

def show_sector_analysis(laps_df):
    """Show sector analysis visualization."""
    st.subheader("Sector Analysis")
    st.info("Sector analysis would be displayed here.")
    # Implement similar to show_lap_time_analysis with proper error handling

def show_telemetry_analysis(session_id):
    """Show telemetry data analysis for selected driver and lap."""
    st.subheader("Telemetry Analysis")
    st.info("Telemetry analysis would be displayed here.")
    # Implement with proper error handling

def show_race_overview(laps_df):
    """Show race overview visualization."""
    st.subheader("Race Overview")
    st.info("Race overview would be displayed here.")
    # Implement with proper error handling

race_analysis()