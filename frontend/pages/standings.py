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
            if isinstance(available_years, list) and len(available_years) == 0:
                available_years = [2025, 2024, 2023]
            else:
                try:
                    available_years = [row['year'] for row in available_years]
                except:
                    available_years = [2025, 2024, 2023]
        
        # Allow user to select a season
        if 'selected_year' in st.session_state:
            # Make sure the year is in the available years
            if st.session_state['selected_year'] in available_years:
                default_year_index = available_years.index(st.session_state['selected_year'])
            else:
                default_year_index = 0
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
    
    try:
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
        
        # Check if we have valid data
        if is_data_empty(driver_standings):
            st.info("No driver standings data available for this season.")
            return
            
        # Add position column
        driver_standings = driver_standings.reset_index(drop=True)
        driver_standings['position'] = driver_standings.index + 1
        
        # Create a visual representation of the standings
        if 'full_name' in driver_standings.columns:
            name_col = 'full_name'
        elif 'driver_name' in driver_standings.columns:
            name_col = 'driver_name'
        else:
            st.warning("Driver name column not found in standings data.")
            return
            
        if 'team_name' not in driver_standings.columns or 'team_color' not in driver_standings.columns:
            st.warning("Team information missing from standings data.")
            return
            
        # Create the bar chart
        fig = px.bar(
            driver_standings,
            x=name_col,
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
        
        st.plotly_chart(fig, use_container_width=True, key=f"driver_standings_chart_{year}")
        
        # Add a checkbox to toggle the detailed table view
        if st.checkbox("Show detailed standings table", value=False):
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
            
            col1.metric("Championship Leader", leader[name_col])
            col2.metric("Leader's Team", leader['team_name'])
            col3.metric("Gap to Second", f"{leader_gap} points")
    except Exception as e:
        st.error(f"Error displaying driver standings: {e}")


def show_constructor_standings(data_service, year):
    """Display the constructor championship standings."""
    st.subheader(f"{year} Constructors' Championship")
    
    try:
        # Get constructor standings for the selected year
        constructor_standings = data_service.get_constructor_standings(year)
        
        # Convert to DataFrame if necessary
        if not isinstance(constructor_standings, pd.DataFrame):
            try:
                constructor_standings = pd.DataFrame(constructor_standings)
            except:
                constructor_standings = pd.DataFrame()
        
        if is_data_empty(constructor_standings):
            st.info("No constructor standings data available for this season.")
            return
            
        # Check for required columns
        required_cols = ['team_name', 'team_color', 'total_points']
        missing_cols = [col for col in required_cols if col not in constructor_standings.columns]
        
        if missing_cols:
            st.warning(f"Missing required data columns: {', '.join(missing_cols)}")
            return
        
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
        
        st.plotly_chart(fig, use_container_width=True, key=f"constructor_standings_chart_{year}")
        
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
            
            # Get drivers for the leading team - FIXED to handle the session_id parameter
            team_id = leader['team_id'] if 'team_id' in leader else None
            
            st.subheader("Team Insights")
            
            col1, col2 = st.columns(2)
            
            col1.metric("Leading Team", leader['team_name'])
            col2.metric("Gap to Second", f"{leader_gap} points")
    except Exception as e:
        st.error(f"Error displaying constructor standings: {e}")


def show_season_progress(data_service, year):
    """Display how the championships have evolved throughout the season."""
    st.subheader(f"{year} Championship Progress")
    
    try:
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
                # Convert to DataFrame if needed
                if not isinstance(sessions, pd.DataFrame):
                    try:
                        sessions_df = pd.DataFrame(sessions)
                    except:
                        continue  # Skip if we can't process
                else:
                    sessions_df = sessions
                    
                # Find race sessions
                for _, session in sessions_df.iterrows():
                    if session['session_type'] == 'race':
                        races.append({
                            'id': event['id'],
                            'round_number': event['round_number'],
                            'event_name': event['event_name'],
                            'session_id': session['id']
                        })
        
        # Convert races to DataFrame
        races_df = pd.DataFrame(races) if races else pd.DataFrame()
        
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
                try:
                    driver_standings = pd.DataFrame(driver_standings)
                except:
                    driver_standings = pd.DataFrame()
            
            # Create simplified visualization
            st.subheader("Current Drivers' Championship Standings")
            
            # Sort by points
            driver_standings = driver_standings.sort_values('total_points', ascending=False)
            
            # Create bar chart
            name_col = 'full_name' if 'full_name' in driver_standings.columns else 'driver_name'
            
            if name_col in driver_standings.columns and 'team_name' in driver_standings.columns and 'team_color' in driver_standings.columns:
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
                
                st.plotly_chart(fig, use_container_width=True, key=f"season_progress_drivers_chart_{year}")
        
        # Similar simplified visualization for team standings
        team_standings = data_service.get_constructor_standings(year)
        if not is_data_empty(team_standings):
            # Convert to DataFrame if necessary
            if not isinstance(team_standings, pd.DataFrame):
                try:
                    team_standings = pd.DataFrame(team_standings)
                except:
                    team_standings = pd.DataFrame()
            
            # Check for required columns
            if 'team_name' in team_standings.columns and 'total_points' in team_standings.columns and 'team_color' in team_standings.columns:
                # Create simplified visualization
                st.subheader("Current Constructors' Championship Standings")
                
                # Sort by points
                team_standings = team_standings.sort_values('total_points', ascending=False)
                
                # Create bar chart with team colors
                if not is_data_empty(team_standings):
                    fig_constructors = go.Figure()

                    for i, team in team_standings.iterrows():
                        fig_constructors.add_trace(go.Bar(
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
                
                st.plotly_chart(fig_constructors, use_container_width=True, key=f"season_progress_constructors_chart_{year}")
        
        # Note on progress calculation
        st.info("""
        For detailed race-by-race progression of standings, additional functionality 
        would need to be implemented in the F1DataService to calculate points after 
        each race. The current implementation shows current standings only.
        """)
    except Exception as e:
        st.error(f"Error displaying season progress: {e}")


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

standings()