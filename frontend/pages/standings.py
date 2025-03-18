import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

from backend.db_connection import get_db_handler

def standings():
    st.title("🏆 Championship Standings")    
    
    try:

        with get_db_handler() as db:
             
            # Get available years from the database
            years_df = db.execute_query("SELECT DISTINCT year FROM events ORDER BY year DESC")
            years = years_df['year'].tolist() if not years_df.empty else [2025, 2024, 2023]
            
            # Allow user to select a season
            if 'selected_year' in st.session_state:
                default_year_index = years.index(st.session_state['selected_year']) if st.session_state['selected_year'] in years else 0
            else:
                default_year_index = 0
                
            year = st.selectbox("Select Season", years, index=default_year_index)
            
            # Update session state
            st.session_state['selected_year'] = year
            
            # Create tabs for driver and constructor standings
            tab1, tab2, tab3 = st.tabs(["Driver Standings", "Constructor Standings", "Season Progress"])
            
            with tab1:
                show_driver_standings(year)
            
            with tab2:
                show_constructor_standings(year)
            
            with tab3:
                show_season_progress(year)
    
    except Exception as e:
        st.error(f"Error loading standings: {e}")


def show_driver_standings(db, year):
    """Display the driver championship standings."""
    st.subheader(f"{year} Drivers' Championship")
    
    # Get driver standings for the selected year
    driver_standings = db.execute_query(
        """
        SELECT d.id, d.full_name as driver_name, d.abbreviation, d.driver_number,
               t.name as team_name, t.team_color,
               SUM(r.points) as total_points
        FROM results r
        JOIN drivers d ON r.driver_id = d.id
        JOIN teams t ON d.team_id = t.id
        JOIN sessions s ON r.session_id = s.id
        JOIN events e ON s.event_id = e.id
        WHERE e.year = ? AND (s.session_type = 'race' OR s.session_type = 'sprint')
        GROUP BY d.id
        ORDER BY total_points DESC
        """,        
        params=(year,)
    )
    
    if not driver_standings.empty:
        # Add position column
        driver_standings = driver_standings.reset_index(drop=True)
        driver_standings['position'] = driver_standings.index + 1
        
        # Create a visual representation of the standings
        fig = px.bar(
            driver_standings,
            x='driver_name',
            y='total_points',
            title=f"{year} Drivers' Championship Standings",
            color='team_name',
            color_discrete_map={team: color for team, color in zip(driver_standings['team_name'], driver_standings['team_color'])}
        )
        
        fig.update_layout(
            xaxis_title="Driver",
            yaxis_title="Points",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display the standings table
        display_df = driver_standings[['position', 'driver_name', 'team_name', 'total_points']].copy()
        display_df.columns = ['Position', 'Driver', 'Team', 'Points']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Show the championship leader and gap to second
        if len(driver_standings) >= 2:
            leader = driver_standings.iloc[0]
            second = driver_standings.iloc[1]
            
            leader_gap = leader['total_points'] - second['total_points']
            
            st.subheader("Championship Insights")
            
            col1, col2, col3 = st.columns(3)
            
            col1.metric("Championship Leader", leader['driver_name'])
            col2.metric("Leader's Team", leader['team_name'])
            col3.metric("Gap to Second", f"{leader_gap} points")
    else:
        st.info("No driver standings data available for this season.")

def show_constructor_standings(db, year):
    """Display the constructor championship standings."""
    st.subheader(f"{year} Constructors' Championship")
    
    # Get constructor standings for the selected year
    constructor_standings = db.execute_query(
        """
        SELECT t.id, t.name as team_name, t.team_color,
               SUM(r.points) as total_points
        FROM results r
        JOIN drivers d ON r.driver_id = d.id
        JOIN teams t ON d.team_id = t.id
        JOIN sessions s ON r.session_id = s.id
        JOIN events e ON s.event_id = e.id
        WHERE e.year = ? AND (s.session_type = 'race' OR s.session_type = 'sprint')
        GROUP BY t.id
        ORDER BY total_points DESC
        """,        
        params=(year,)
    )
    
    if not constructor_standings.empty:
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
                marker_color=team['team_color']
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
        
        # Display the standings table
        display_df = constructor_standings[['position', 'team_name', 'total_points']].copy()
        display_df.columns = ['Position', 'Team', 'Points']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Add more metrics and insights
        if len(constructor_standings) >= 2:
            leader = constructor_standings.iloc[0]
            second = constructor_standings.iloc[1]
            
            leader_gap = leader['total_points'] - second['total_points']
            
            # Get drivers for the leading team
            leading_team_drivers = db.execute_query(
                """
                SELECT d.full_name, SUM(r.points) as driver_points
                FROM results r
                JOIN drivers d ON r.driver_id = d.id
                JOIN teams t ON d.team_id = t.id
                JOIN sessions s ON r.session_id = s.id
                JOIN events e ON s.event_id = e.id
                WHERE e.year = ? AND t.id = ? AND (s.session_type = 'race' OR s.session_type = 'sprint')
                GROUP BY d.id
                ORDER BY driver_points DESC
                """,                
                params=(year, leader['id'])
            )
            
            st.subheader("Team Insights")
            
            col1, col2, col3 = st.columns(3)
            
            col1.metric("Leading Team", leader['team_name'])
            col2.metric("Gap to Second", f"{leader_gap} points")
            
            if not leading_team_drivers.empty:
                leading_driver = leading_team_drivers.iloc[0]['full_name']
                leading_driver_points = leading_team_drivers.iloc[0]['driver_points']
                col3.metric("Team's Leading Driver", f"{leading_driver} ({leading_driver_points} pts)")
                
                # Show pie chart of points contribution within team
                if len(leading_team_drivers) > 1:
                    fig = px.pie(
                        leading_team_drivers,
                        values='driver_points',
                        names='full_name',
                        title=f"Points Distribution within {leader['team_name']}",
                        color_discrete_sequence=[leader['team_color'], lighten_color(leader['team_color'], 0.3)]
                    )
                    
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white')
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No constructor standings data available for this season.")

def show_season_progress(db, year):
    """Display how the championships have evolved throughout the season."""
    st.subheader(f"{year} Championship Progress")
    
    # Get all races in the season
    races = db.execute_query(
        """
        SELECT e.id, e.round_number, e.event_name, s.id as session_id
        FROM events e
        JOIN sessions s ON e.id = s.event_id
        WHERE e.year = ? AND s.session_type = 'race'
        ORDER BY e.round_number
        """,        
        params=(year,)
    )
    
    if races.empty:
        st.info("No race data available for this season.")
        return
    
    # Create a progress tracker for both championships
    driver_progress = []
    team_progress = []
    
    # Get top 5 drivers and teams for the legend
    top_drivers = db.execute_query(
        """
        SELECT d.id, d.full_name as driver_name, t.team_color,
               SUM(r.points) as total_points
        FROM results r
        JOIN drivers d ON r.driver_id = d.id
        JOIN teams t ON d.team_id = t.id
        JOIN sessions s ON r.session_id = s.id
        JOIN events e ON s.event_id = e.id
        WHERE e.year = ? AND (s.session_type = 'race' OR s.session_type = 'sprint')
        GROUP BY d.id
        ORDER BY total_points DESC
        LIMIT 5
        """,        
        params=(year,)
    )
    
    top_teams = db.execute_query(
        """
        SELECT t.id, t.name as team_name, t.team_color,
               SUM(r.points) as total_points
        FROM results r
        JOIN drivers d ON r.driver_id = d.id
        JOIN teams t ON d.team_id = t.id
        JOIN sessions s ON r.session_id = s.id
        JOIN events e ON s.event_id = e.id
        WHERE e.year = ? AND (s.session_type = 'race' OR s.session_type = 'sprint')
        GROUP BY t.id
        ORDER BY total_points DESC
        LIMIT 5
        """,        
        params=(year,)
    )
    
    # Track cumulative points after each race
    for _, race in races.iterrows():
        # Get all races up to this one
        previous_races = races[races['round_number'] <= race['round_number']]
        session_ids = previous_races['session_id'].tolist()
        
        # Format for SQL query
        session_ids_str = ','.join(['?'] * len(session_ids))
        
        # Get driver standings after this race
        driver_standings_query = f"""
            SELECT d.id, d.full_name as driver_name, t.team_color,
                   SUM(r.points) as cumulative_points
            FROM results r
            JOIN drivers d ON r.driver_id = d.id
            JOIN teams t ON d.team_id = t.id
            WHERE r.session_id IN ({session_ids_str})
            GROUP BY d.id
            ORDER BY cumulative_points DESC
        """
        
        driver_standings = db.execute_query(
            driver_standings_query,            
            params=session_ids
        )
        
        # Get team standings after this race
        team_standings_query = f"""
            SELECT t.id, t.name as team_name, t.team_color,
                   SUM(r.points) as cumulative_points
            FROM results r
            JOIN drivers d ON r.driver_id = d.id
            JOIN teams t ON d.team_id = t.id
            WHERE r.session_id IN ({session_ids_str})
            GROUP BY t.id
            ORDER BY cumulative_points DESC
        """
        
        team_standings = db.execute_query(
            team_standings_query,            
            params=session_ids
        )
        
        # Add to progress trackers
        for _, driver in driver_standings.iterrows():
            if driver['id'] in top_drivers['id'].values:
                driver_progress.append({
                    'Driver': driver['driver_name'],
                    'Race': race['event_name'],
                    'Round': race['round_number'],
                    'Points': driver['cumulative_points'],
                    'Color': driver['team_color']
                })
        
        for _, team in team_standings.iterrows():
            if team['id'] in top_teams['id'].values:
                team_progress.append({
                    'Team': team['team_name'],
                    'Race': race['event_name'],
                    'Round': race['round_number'],
                    'Points': team['cumulative_points'],
                    'Color': team['team_color']
                })
    
    # Create progress visualizations
    if driver_progress:
        driver_progress_df = pd.DataFrame(driver_progress)
        
        fig = px.line(
            driver_progress_df,
            x='Round',
            y='Points',
            color='Driver',
            title="Drivers' Championship Progress",
            color_discrete_map={driver: color for driver, color in zip(driver_progress_df['Driver'].unique(), driver_progress_df['Color'].unique())},
            markers=True
        )
        
        fig.update_layout(
            xaxis_title="Round",
            yaxis_title="Points",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    if team_progress:
        team_progress_df = pd.DataFrame(team_progress)
        
        fig = px.line(
            team_progress_df,
            x='Round',
            y='Points',
            color='Team',
            title="Constructors' Championship Progress",
            color_discrete_map={team: color for team, color in zip(team_progress_df['Team'].unique(), team_progress_df['Color'].unique())},
            markers=True
        )
        
        fig.update_layout(
            xaxis_title="Round",
            yaxis_title="Points",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)

def lighten_color(hex_color, factor=0.3):
    """Lighten a hex color by a factor."""
    # Remove the # if present
    hex_color = hex_color.lstrip('#')
    
    # Convert hex to RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    # Lighten
    r = min(255, r + int((255 - r) * factor))
    g = min(255, g + int((255 - g) * factor))
    b = min(255, b + int((255 - b) * factor))
    
    # Convert back to hex
    return f"#{r:02x}{g:02x}{b:02x}"