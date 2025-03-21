import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

from backend.data_service import F1DataService

def is_data_empty(data):
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def standings():
    st.title("🏆 Championship Standings")    
    
    try:
        # Initialize data service
        data_service = F1DataService()

        # Get available years
        available_years = data_service.get_available_years()
        
        # Handle case where no years are returned
        if is_data_empty(available_years):
            available_years = [2025, 2024, 2023]
        
        # Allow user to select a season
        if 'selected_year' in st.session_state:
            default_year_index = available_years.index(st.session_state['selected_year']) if st.session_state['selected_year'] in available_years else 0
        else:
            default_year_index = 0
            
        year = st.selectbox("Select Season", available_years, index=default_year_index)
        
        # Update session state
        st.session_state['selected_year'] = year
        
        # Create tabs for driver and constructor standings
        tab1, tab2, tab3 = st.tabs(["Driver Standings", "Constructor Standings", "Season Progress"])
        
        with tab1:
            show_driver_standings(data_service, year)
        
        with tab2:
            show_constructor_standings(data_service, year)
        
        with tab3:
            show_season_progress(data_service, year)
    
    except Exception as e:
        st.error(f"Error loading standings: {e}")


def show_driver_standings(data_service, year):
    """Display the driver championship standings."""
    st.subheader(f"{year} Drivers' Championship")
    
    # Get driver standings for the selected year
    driver_standings = data_service.get_driver_standings(year)
    
    # Ensure all drivers are included, even those with zero points
    all_drivers = data_service.get_drivers(year)
    
    # Convert to DataFrame if necessary
    if not isinstance(driver_standings, pd.DataFrame):
        try:
            driver_standings = pd.DataFrame(driver_standings)
        except:
            driver_standings = pd.DataFrame()
    
    if not isinstance(all_drivers, pd.DataFrame):
        try:
            all_drivers = pd.DataFrame(all_drivers)
        except:
            all_drivers = pd.DataFrame()
    
    # Get existing driver IDs
    if not is_data_empty(driver_standings) and 'driver_id' in driver_standings.columns:
        existing_ids = set(driver_standings['driver_id'].tolist())
        
        # Add missing drivers with zero points
        if not is_data_empty(all_drivers):
            # Make sure all_drivers has a 'id' column to match against driver_standings 'driver_id'
            if 'id' in all_drivers.columns and 'driver_id' not in all_drivers.columns:
                all_drivers['driver_id'] = all_drivers['id']
            
            if 'driver_id' in all_drivers.columns:
                missing_drivers = all_drivers[~all_drivers['driver_id'].isin(existing_ids)].copy()
                
                if not is_data_empty(missing_drivers):
                    # Ensure missing_drivers has a 'total_points' column with zeros
                    if 'total_points' not in missing_drivers.columns:
                        missing_drivers['total_points'] = 0
                    
                    # Ensure both DataFrames have the same columns
                    common_columns = set(driver_standings.columns) & set(missing_drivers.columns)
                    driver_standings = driver_standings[list(common_columns)]
                    missing_drivers = missing_drivers[list(common_columns)]
                    
                    # Concatenate and sort
                    driver_standings = pd.concat([driver_standings, missing_drivers], ignore_index=True)
                    driver_standings = driver_standings.sort_values('total_points', ascending=False)
    
    if not is_data_empty(driver_standings):
        # Add position column
        driver_standings = driver_standings.reset_index(drop=True)
        driver_standings['position'] = driver_standings.index + 1
        
        # Create a visual representation of the standings
        fig = px.bar(
            driver_standings,
            x='full_name' if 'full_name' in driver_standings.columns else 'driver_name',
            y='total_points',
            title=f"{year} Drivers' Championship Standings",
            color='team_name',
            color_discrete_map={team: add_hash_to_color(color) for team, color in zip(driver_standings['team_name'], driver_standings['team_color'])}
        )
        
        # Update the bar labels - just show the points value
        fig.update_traces(
            texttemplate='%{y}',  # Show the points value
            textposition='outside',
            textfont=dict(color='white'),
            hovertemplate='<b>%{x}</b><br>Points: %{y}<br>Team: %{marker.color}'
        )
        
        fig.update_layout(
            xaxis_title="Driver",
            yaxis_title="Points",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=600,
            xaxis={'tickangle': 45}  # Angle the driver names for better readability
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add a checkbox to toggle the detailed table view
        if st.checkbox("Show detailed standings table", value=False):
            name_col = 'full_name' if 'full_name' in driver_standings.columns else 'driver_name'
            display_df = driver_standings[['position', name_col, 'team_name', 'total_points']].copy()
            display_df.columns = ['Position', 'Driver', 'Team', 'Points']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Show the championship leader and gap to second
        if len(driver_standings) >= 2:
            leader = driver_standings.iloc[0]
            second = driver_standings.iloc[1]
            
            leader_gap = leader['total_points'] - second['total_points']
            
            st.subheader("Championship Insights")
            
            col1, col2, col3 = st.columns(3)
            
            name_col = 'full_name' if 'full_name' in driver_standings.columns else 'driver_name'
            col1.metric("Championship Leader", leader[name_col])
            col2.metric("Leader's Team", leader['team_name'])
            col3.metric("Gap to Second", f"{leader_gap} points")
    else:
        st.info("No driver standings data available for this season.")


def show_constructor_standings(data_service, year):
    """Display the constructor championship standings."""
    st.subheader(f"{year} Constructors' Championship")
    
    # Get constructor standings for the selected year
    constructor_standings = data_service.get_constructor_standings(year)
    
    # Convert to DataFrame if necessary
    if not isinstance(constructor_standings, pd.DataFrame):
        try:
            constructor_standings = pd.DataFrame(constructor_standings)
        except:
            constructor_standings = pd.DataFrame()
    
    if not is_data_empty(constructor_standings):
        # Add position column
        constructor_standings = constructor_standings.reset_index(drop=True)
        constructor_standings['position'] = constructor_standings.index + 1
        
        # Create a visual representation of the standings
        fig = go.Figure()
        
        # Add a bar for each team with their team color
        for i, team in constructor_standings.iterrows():
            fig.add_trace(go.Bar(
                x=[team['team_name']],
                y=[team['total_points']],
                name=team['team_name'],
                marker_color=add_hash_to_color(team['team_color']),
                text=[team['total_points']],  # Just show the points
                textposition="outside",
                textfont=dict(color="white")
            ))
        
        fig.update_layout(
            title=f"{year} Constructors' Championship Standings",
            xaxis_title="Team",
            yaxis_title="Points",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=500,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add a checkbox to toggle the detailed table view
        if st.checkbox("Show detailed constructors table", value=False):
            display_df = constructor_standings[['position', 'team_name', 'total_points']].copy()
            display_df.columns = ['Position', 'Team', 'Points']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Add more metrics and insights
        if len(constructor_standings) >= 2:
            leader = constructor_standings.iloc[0]
            second = constructor_standings.iloc[1]
            
            leader_gap = leader['total_points'] - second['total_points']
            
            # Get drivers for the leading team
            team_id = leader['team_id']
            leading_team_drivers = data_service.get_drivers(year, team_id)
            
            # Convert to DataFrame and calculate points for each driver
            if not is_data_empty(leading_team_drivers):
                # This part is simplified compared to the original as we don't have a direct way
                # to get driver points through the data_service yet
                st.subheader("Team Insights")
                
                col1, col2 = st.columns(2)
                
                col1.metric("Leading Team", leader['team_name'])
                col2.metric("Gap to Second", f"{leader_gap} points")
    else:
        st.info("No constructor standings data available for this season.")


def show_season_progress(data_service, year):
    """Display how the championships have evolved throughout the season."""
    st.subheader(f"{year} Championship Progress")
    
    # Get all events for the year
    events = data_service.get_events(year)
    
    # Convert to DataFrame if necessary
    if not isinstance(events, pd.DataFrame):
        try:
            events = pd.DataFrame(events)
        except:
            events = pd.DataFrame()
    
    if is_data_empty(events):
        st.info("No race data available for this season.")
        return
    
    # Get all races with sessions
    races = []
    for _, event in events.iterrows():
        event_id = event['id']
        sessions = data_service.get_sessions(event_id)
        
        if not is_data_empty(sessions):
            for session in sessions:
                if session['session_type'] == 'race':
                    races.append({
                        'id': event['id'],
                        'round_number': event['round_number'],
                        'event_name': event['event_name'],
                        'session_id': session['id']
                    })
    
    # Convert races to DataFrame
    races_df = pd.DataFrame(races)
    
    if is_data_empty(races_df):
        st.info("No race data available for this season.")
        return
    
    # Create a simplified progress visualization
    # For a full implementation, you would need to adapt the complex queries 
    # in the original code to use data_service methods
    
    st.info("Race progression data is being calculated. Please wait...")
    
    # Get driver standings to create progress chart
    driver_standings = data_service.get_driver_standings(year)
    if not is_data_empty(driver_standings):
        # Convert to DataFrame if necessary
        if not isinstance(driver_standings, pd.DataFrame):
            driver_standings = pd.DataFrame(driver_standings)
        
        # Create simplified visualization
        st.subheader("Current Drivers' Championship Standings")
        
        # Sort by points
        driver_standings = driver_standings.sort_values('total_points', ascending=False)
        
        # Create bar chart
        name_col = 'full_name' if 'full_name' in driver_standings.columns else 'driver_name'
        fig = px.bar(
            driver_standings,
            x=name_col,
            y='total_points',
            color='team_name',
            title=f"{year} Drivers' Championship Standings",
            color_discrete_map={team: add_hash_to_color(color) for team, color in zip(driver_standings['team_name'], driver_standings['team_color'])}
        )
        
        fig.update_layout(
            xaxis_title="Driver",
            yaxis_title="Points",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=500,
            xaxis={'tickangle': 45}
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    # Similar simplified visualization for team standings
    team_standings = data_service.get_constructor_standings(year)
    if not is_data_empty(team_standings):
        # Convert to DataFrame if necessary
        if not isinstance(team_standings, pd.DataFrame):
            team_standings = pd.DataFrame(team_standings)
        
        # Create simplified visualization
        st.subheader("Current Constructors' Championship Standings")
        
        # Sort by points
        team_standings = team_standings.sort_values('total_points', ascending=False)
        
        # Create bar chart with team colors
        fig = go.Figure()
        
        for i, team in team_standings.iterrows():
            fig.add_trace(go.Bar(
                x=[team['team_name']],
                y=[team['total_points']],
                name=team['team_name'],
                marker_color=add_hash_to_color(team['team_color']),
                text=[team['total_points']],
                textposition="outside",
                textfont=dict(color="white")
            ))
        
        fig.update_layout(
            title=f"{year} Constructors' Championship Standings",
            xaxis_title="Team",
            yaxis_title="Points",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=500,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Note on progress calculation
    st.info("""
    For detailed race-by-race progression of standings, additional functionality 
    would need to be implemented in the F1DataService to calculate points after 
    each race. The current implementation shows current standings only.
    """)


def add_hash_to_color(color_str):
    """Ensure a color string starts with # for hex colors."""
    if color_str and isinstance(color_str, str) and not color_str.startswith('#') and not color_str.startswith('rgb'):
        return f"#{color_str}"
    return color_str


def lighten_color(hex_color, factor=0.3):
    """Lighten a hex color by a factor."""
    # Remove the # if present
    hex_color = hex_color.lstrip('#')
    
    # Convert hex to RGB
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Lighten
        r = min(255, r + int((255 - r) * factor))
        g = min(255, g + int((255 - g) * factor))
        b = min(255, b + int((255 - b) * factor))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    except (ValueError, IndexError):
        # If there's an error processing the color, return a default
        return "#CCCCCC"