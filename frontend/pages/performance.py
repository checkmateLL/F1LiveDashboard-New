import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

from backend.db_connection import get_db_handler

# Helper function for color formatting
def add_hash_to_color(color_str):
    """Ensure a color string starts with # for hex colors."""
    if color_str and isinstance(color_str, str) and not color_str.startswith('#') and not color_str.startswith('rgb'):
        return f"#{color_str}"
    return color_str

def performance():
    st.title("📊 Performance Analysis")
    
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
            
            # Create tabs for different performance analyses
            tab1, tab2, tab3, tab4 = st.tabs([
                "Driver Performance", 
                "Team Performance", 
                "Tire Strategy", 
                "Pit Stop Analysis"
            ])
            
            with tab1:
                show_driver_performance(db, year)
            
            with tab2:
                show_team_performance(db, year)
            
            with tab3:
                show_tire_strategy(db, year)
            
            with tab4:
                show_pit_stop_analysis(db, year)
    
    except Exception as e:
        st.error(f"Error loading performance analysis: {e}") 
   

def show_driver_performance(db, year):
    """Analyze and visualize driver performance metrics."""
    st.subheader("Driver Performance Analysis")
    
    # Get all drivers for the selected year
    drivers_df = db.execute_query(
        """
        SELECT DISTINCT d.id, d.full_name as driver_name, d.abbreviation,
               t.name as team_name, t.team_color
        FROM drivers d
        JOIN teams t ON d.team_id = t.id
        WHERE d.year = ?
        ORDER BY t.name, d.full_name
        """,        
        params=(year,)
    )
    
    if drivers_df.empty:
        st.info("No driver data available for this season.")
        return
    
    # Select drivers to compare
    selected_drivers = st.multiselect(
        "Select Drivers to Compare",
        drivers_df['driver_name'].tolist(),
        default=drivers_df['driver_name'].tolist()[:2] if len(drivers_df) > 1 else drivers_df['driver_name'].tolist()
    )
    
    if not selected_drivers:
        st.warning("Please select at least one driver to analyze.")
        return
    
    # Filter selected drivers
    selected_drivers_df = drivers_df[drivers_df['driver_name'].isin(selected_drivers)]
    
    # Get metrics for the selected drivers
    performance_metrics = []
    
    for _, driver in selected_drivers_df.iterrows():
        # Get qualifying performance
        quali_data = db.execute_query(
            """
            SELECT AVG(r.position) as avg_quali_position,
                   MIN(r.position) as best_quali_position,
                   COUNT(*) as quali_count
            FROM results r
            JOIN sessions s ON r.session_id = s.id
            JOIN events e ON s.event_id = e.id
            WHERE r.driver_id = ? AND e.year = ? AND 
                  (s.session_type = 'qualifying' OR s.session_type = 'sprint_qualifying' OR s.session_type = 'sprint_shootout')
            """,            
            params=(driver['id'], year)
        )
        
        # Get race performance
        race_data = db.execute_query(
            """
            SELECT AVG(r.position) as avg_race_position,
                   MIN(r.position) as best_race_position,
                   AVG(r.grid_position - r.position) as avg_positions_gained,
                   SUM(r.points) as total_points,
                   COUNT(*) as race_count
            FROM results r
            JOIN sessions s ON r.session_id = s.id
            JOIN events e ON s.event_id = e.id
            WHERE r.driver_id = ? AND e.year = ? AND 
                  (s.session_type = 'race' OR s.session_type = 'sprint')
            """,            
            params=(driver['id'], year)
        )
        
        # Get fastest laps
        fastest_laps = db.execute_query(
            """
            SELECT COUNT(*) as fastest_lap_count
            FROM (
                SELECT s.id as session_id, MIN(l.lap_time) as fastest_lap_time
                FROM laps l
                JOIN sessions s ON l.session_id = s.id
                JOIN events e ON s.event_id = e.id
                WHERE e.year = ? AND s.session_type = 'race' AND l.deleted = 0
                GROUP BY s.id
            ) fastest
            JOIN laps l ON l.session_id = fastest.session_id AND l.lap_time = fastest.fastest_lap_time
            WHERE l.driver_id = ?
            """,            
            params=(year, driver['id'])
        )
        
        # Compile metrics
        performance_metrics.append({
            'Driver': driver['driver_name'],
            'Team': driver['team_name'],
            'Color': driver['team_color'],
            'Avg Quali Position': round(quali_data['avg_quali_position'].iloc[0], 2) if not quali_data.empty and not pd.isna(quali_data['avg_quali_position'].iloc[0]) else None,
            'Best Quali Position': int(quali_data['best_quali_position'].iloc[0]) if not quali_data.empty and not pd.isna(quali_data['best_quali_position'].iloc[0]) else None,
            'Avg Race Position': round(race_data['avg_race_position'].iloc[0], 2) if not race_data.empty and not pd.isna(race_data['avg_race_position'].iloc[0]) else None,
            'Best Race Position': int(race_data['best_race_position'].iloc[0]) if not race_data.empty and not pd.isna(race_data['best_race_position'].iloc[0]) else None,
            'Avg Positions Gained': round(race_data['avg_positions_gained'].iloc[0], 2) if not race_data.empty and not pd.isna(race_data['avg_positions_gained'].iloc[0]) else None,
            'Points': float(race_data['total_points'].iloc[0]) if not race_data.empty and not pd.isna(race_data['total_points'].iloc[0]) else 0,
            'Fastest Laps': int(fastest_laps['fastest_lap_count'].iloc[0]) if not fastest_laps.empty and not pd.isna(fastest_laps['fastest_lap_count'].iloc[0]) else 0
        })
    
    if performance_metrics:
        metrics_df = pd.DataFrame(performance_metrics)
        
        # Display performance metrics table
        st.dataframe(
            metrics_df.drop('Color', axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        # Create radar chart for overall comparison
        st.subheader("Driver Performance Comparison")
        
        # Prepare data for radar chart
        categories = ['Qualifying', 'Race Position', 'Position Gain', 'Points', 'Fastest Laps']
        
        fig = go.Figure()
        
        for _, row in metrics_df.iterrows():
            # Normalize metrics for radar chart (higher value = better performance)
            quali_norm = 20 - row['Avg Quali Position'] if pd.notna(row['Avg Quali Position']) else 0
            race_norm = 20 - row['Avg Race Position'] if pd.notna(row['Avg Race Position']) else 0
            gain_norm = row['Avg Positions Gained'] + 10 if pd.notna(row['Avg Positions Gained']) else 0
            points_norm = row['Points'] / max(metrics_df['Points']) * 10 if max(metrics_df['Points']) > 0 else 0
            fl_norm = row['Fastest Laps'] * 2
            
            # Add trace for driver
            fig.add_trace(go.Scatterpolar(
                r=[quali_norm, race_norm, gain_norm, points_norm, fl_norm],
                theta=categories,
                fill='toself',
                name=row['Driver'],
                line_color=add_hash_to_color(row['Color'])
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 20]
                )
            ),
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display individual performance trends
        if len(selected_drivers) <= 3:  # Limit to avoid cluttering
            for driver_name in selected_drivers:
                driver_id = drivers_df[drivers_df['driver_name'] == driver_name]['id'].iloc[0]
                driver_color = drivers_df[drivers_df['driver_name'] == driver_name]['team_color'].iloc[0]
                
                # Get race results over the season
                race_results = db.execute_query(
                    """
                    SELECT r.position, e.round_number, e.event_name
                    FROM results r
                    JOIN sessions s ON r.session_id = s.id
                    JOIN events e ON s.event_id = e.id
                    WHERE r.driver_id = ? AND e.year = ? AND s.session_type = 'race'
                    ORDER BY e.round_number
                    """,                    
                    params=(driver_id, year)
                )
                
                if not race_results.empty:
                    # Create individual trend chart
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=race_results['round_number'],
                        y=race_results['position'],
                        mode='lines+markers',
                        name='Position',
                        line=dict(color=add_hash_to_color(driver_color), width=3),
                        hovertemplate=(
                            "Round: %{x}<br>" +
                            "Position: %{y}<br>" +
                            "Race: %{customdata}"
                        ),
                        customdata=race_results['event_name']
                    ))
                    
                    # Update layout
                    fig.update_layout(
                        title=f"{driver_name}'s Race Performance Trend",
                        xaxis_title="Round",
                        yaxis_title="Position",
                        yaxis=dict(
                            autorange="reversed",  # Lower position number is better
                            dtick=1
                        ),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        height=300
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No performance data available for the selected drivers.")

def show_team_performance(db, year):
    """Analyze and visualize team performance metrics."""
    st.subheader("Team Performance Analysis")
    
    # Get all teams for the selected year
    teams_df = db.execute_query(
        """
        SELECT DISTINCT id, name as team_name, team_color
        FROM teams
        WHERE year = ?
        ORDER BY name
        """,        
        params=(year,)
    )
    
    if teams_df.empty:
        st.info("No team data available for this season.")
        return
    
    # Select teams to compare
    selected_teams = st.multiselect(
        "Select Teams to Compare",
        teams_df['team_name'].tolist(),
        default=teams_df['team_name'].tolist()[:3] if len(teams_df) > 2 else teams_df['team_name'].tolist()
    )
    
    if not selected_teams:
        st.warning("Please select at least one team to analyze.")
        return
    
    # Filter selected teams
    selected_teams_df = teams_df[teams_df['team_name'].isin(selected_teams)]
    
    # Get metrics for the selected teams
    performance_metrics = []
    
    for _, team in selected_teams_df.iterrows():
        # Get race performance
        race_data = db.execute_query(
            """
            SELECT AVG(r.position) as avg_position,
                   MIN(r.position) as best_position,
                   SUM(r.points) as total_points,
                   COUNT(*) as race_entries
            FROM results r
            JOIN drivers d ON r.driver_id = d.id
            JOIN sessions s ON r.session_id = s.id
            JOIN events e ON s.event_id = e.id
            WHERE d.team_id = ? AND e.year = ? AND s.session_type = 'race'
            """,            
            params=(team['id'], year)
        )
        
        # Get qualifying performance
        quali_data = db.execute_query(
            """
            SELECT AVG(r.position) as avg_quali_position,
                   MIN(r.position) as best_quali_position
            FROM results r
            JOIN drivers d ON r.driver_id = d.id
            JOIN sessions s ON r.session_id = s.id
            JOIN events e ON s.event_id = e.id
            WHERE d.team_id = ? AND e.year = ? AND s.session_type = 'qualifying'
            """,            
            params=(team['id'], year)
        )
        
        # Get podium and win count
        results_data = db.execute_query(
            """
            SELECT 
                SUM(CASE WHEN r.position = 1 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN r.position <= 3 THEN 1 ELSE 0 END) as podiums
            FROM results r
            JOIN drivers d ON r.driver_id = d.id
            JOIN sessions s ON r.session_id = s.id
            JOIN events e ON s.event_id = e.id
            WHERE d.team_id = ? AND e.year = ? AND s.session_type = 'race'
            """,            
            params=(team['id'], year)
        )
        
        # Compile metrics
        performance_metrics.append({
            'Team': team['team_name'],
            'Color': team['team_color'],
            'Points': float(race_data['total_points'].iloc[0]) if not race_data.empty and not pd.isna(race_data['total_points'].iloc[0]) else 0,
            'Avg Position': round(race_data['avg_position'].iloc[0], 2) if not race_data.empty and not pd.isna(race_data['avg_position'].iloc[0]) else None,
            'Best Position': int(race_data['best_position'].iloc[0]) if not race_data.empty and not pd.isna(race_data['best_position'].iloc[0]) else None,
            'Avg Quali': round(quali_data['avg_quali_position'].iloc[0], 2) if not quali_data.empty and not pd.isna(quali_data['avg_quali_position'].iloc[0]) else None,
            'Best Quali': int(quali_data['best_quali_position'].iloc[0]) if not quali_data.empty and not pd.isna(quali_data['best_quali_position'].iloc[0]) else None,
            'Wins': int(results_data['wins'].iloc[0]) if not results_data.empty and not pd.isna(results_data['wins'].iloc[0]) else 0,
            'Podiums': int(results_data['podiums'].iloc[0]) if not results_data.empty and not pd.isna(results_data['podiums'].iloc[0]) else 0,
            'Entries': int(race_data['race_entries'].iloc[0]) if not race_data.empty and not pd.isna(race_data['race_entries'].iloc[0]) else 0
        })
    
    if performance_metrics:
        metrics_df = pd.DataFrame(performance_metrics)
        
        # Display performance metrics table
        st.dataframe(
            metrics_df.drop('Color', axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        # Create points comparison chart
        fig = px.bar(
            metrics_df,
            x='Team',
            y='Points',
            color='Team',
            color_discrete_map={team: add_hash_to_color(color) for team, color in zip(metrics_df['Team'], metrics_df['Color'])},
            title="Constructor Points Comparison"
        )
        
        fig.update_layout(
            xaxis_title="Team",
            yaxis_title="Points",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show team performance efficiency
        st.subheader("Team Efficiency")
        
        # Calculate points per entry
        metrics_df['Points per Entry'] = metrics_df['Points'] / metrics_df['Entries'].apply(lambda x: max(1, x))
        
        # Create points efficiency chart
        fig = px.bar(
            metrics_df,
            x='Team',
            y='Points per Entry',
            color='Team',
            color_discrete_map={team: add_hash_to_color(color) for team, color in zip(metrics_df['Team'], metrics_df['Color'])},
            title="Points per Race Entry"
        )
        
        fig.update_layout(
            xaxis_title="Team",
            yaxis_title="Points per Entry",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show season progress for selected teams
        st.subheader("Season Progress by Team")
        
        # Get events for the selected year
        events = db.execute_query(
            """
            SELECT id, round_number, event_name
            FROM events
            WHERE year = ?
            ORDER BY round_number
            """,            
            params=(year,)
        )
        
        if not events.empty:
            # Track cumulative points for each team
            team_progress = []
            
            for _, team in selected_teams_df.iterrows():
                team_id = team['id']
                
                for _, event in events.iterrows():
                    # Get all races up to this one
                    previous_events = events[events['round_number'] <= event['round_number']]
                    event_ids = previous_events['id'].tolist()
                    
                    # Format for SQL query
                    event_ids_str = ','.join(['?'] * len(event_ids))
                    
                    # Get team points after this event
                    query = f"""
                        SELECT SUM(r.points) as cumulative_points
                        FROM results r
                        JOIN drivers d ON r.driver_id = d.id
                        JOIN sessions s ON r.session_id = s.id
                        JOIN events e ON s.event_id = e.id
                        WHERE d.team_id = ? AND e.id IN ({event_ids_str}) AND s.session_type = 'race'
                    """
                    
                    params = [team_id] + event_ids
                    
                    points_data = db.execute_query(
                        query,                        
                        params=tuple(params)
                    )
                    
                    points = float(points_data['cumulative_points'].iloc[0]) if not points_data.empty and not pd.isna(points_data['cumulative_points'].iloc[0]) else 0
                    
                    team_progress.append({
                        'Team': team['team_name'],
                        'Round': event['round_number'],
                        'Event': event['event_name'],
                        'Points': points,
                        'Color': team['team_color']
                    })
            
            # Create progress chart
            if team_progress:
                progress_df = pd.DataFrame(team_progress)
                
                # Create a figure with steps instead of smooth lines
                fig = go.Figure()
                
                # Get all unique teams
                unique_teams = progress_df['Team'].unique()
                
                # Max round to display (only show completed rounds)
                max_round = events['round_number'].max()
                completed_rounds = db.execute_query(
                    """
                    SELECT MAX(e.round_number) as max_round
                    FROM results r
                    JOIN sessions s ON r.session_id = s.id
                    JOIN events e ON s.event_id = e.id
                    WHERE e.year = ? AND s.session_type = 'race'
                    """,
                    params=(year,)
                )
                if not completed_rounds.empty and not pd.isna(completed_rounds['max_round'].iloc[0]):
                    max_round = min(max_round, completed_rounds['max_round'].iloc[0])
                
                for team in unique_teams:
                    team_data = progress_df[progress_df['Team'] == team]
                    team_data = team_data[team_data['Round'] <= max_round].sort_values('Round')
                    
                    if not team_data.empty:
                        color = add_hash_to_color(team_data['Color'].iloc[0])
                        
                        fig.add_trace(go.Scatter(
                            x=team_data['Round'],
                            y=team_data['Points'],
                            mode='lines+markers',
                            name=team,
                            line=dict(color=color, shape='hv'),  # 'hv' creates step-like horizontal-then-vertical lines
                            marker=dict(size=8, color=color),
                            hovertemplate="<b>%{fullData.name}</b><br>Round: %{x}<br>Points: %{y}<br>Race: %{customdata}",
                            customdata=team_data['Event']
                        ))
                
                fig.update_layout(
                    title="Constructors' Points Progress",
                    xaxis_title="Round",
                    yaxis_title="Cumulative Points",
                    xaxis=dict(
                        tickmode='linear',
                        tick0=1,
                        dtick=1,
                        range=[0.5, max_round + 0.5]  # Only show completed rounds
                    ),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No performance data available for the selected teams.")

def show_tire_strategy(db, year):
    """Analyze and visualize tire strategy patterns for teams and drivers."""
    st.subheader("Tire Strategy Analysis")
    
    # Get all events for the selected year
    events_df = db.execute_query(
        """
        SELECT id, round_number, event_name
        FROM events
        WHERE year = ?
        ORDER BY round_number
        """,        
        params=(year,)
    )
    
    if not events_df or len(events_df) == 0:
        st.warning("No events available for this season.")
        return
    
    # Allow user to select an event
    selected_event = st.selectbox("Select Event", events_df['event_name'].tolist())
    
    # Get the event ID
    event_id = events_df[events_df['event_name'] == selected_event]['id'].iloc[0]
    
    # Get race session for this event
    race_session = db.execute_query(
        """
        SELECT id
        FROM sessions
        WHERE event_id = ? AND session_type = 'race'
        """,        
        params=(event_id,)
    )
    
    if race_session.empty:
        st.info("No race session available for this event.")
        return
    
    session_id = race_session['id'].iloc[0]
    
    # Get tire usage data
    tire_data = db.execute_query(
        """
        SELECT d.full_name as driver_name, t.name as team_name, t.team_color, 
               l.compound, COUNT(*) as lap_count
        FROM laps l
        JOIN drivers d ON l.driver_id = d.id
        JOIN teams t ON d.team_id = t.id
        WHERE l.session_id = ? AND l.compound IS NOT NULL
        GROUP BY d.id, l.compound
        ORDER BY t.name, d.full_name, l.compound
        """,        
        params=(session_id,)
    )
    
    if tire_data.empty:
        st.info("No tire strategy data available for this race.")
        return
    
    # Visualize tire usage by driver
    st.subheader(f"Tire Usage in {selected_event}")
    
    # Pivot the data to show tire compounds as columns
    pivot_tire_data = tire_data.pivot_table(
        index=['driver_name', 'team_name', 'team_color'],
        columns='compound',
        values='lap_count',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    
    # Get all compound types
    compound_columns = [col for col in pivot_tire_data.columns if col not in ['driver_name', 'team_name', 'team_color']]
    
    # Create a stacked bar chart of tire usage
    tire_usage_df = pd.melt(
        pivot_tire_data,
        id_vars=['driver_name', 'team_name', 'team_color'],
        value_vars=compound_columns,
        var_name='Compound',
        value_name='Laps'
    )
    
    # Define a color map for tire compounds
    compound_colors = {
        'S': '#FF0000',  # Red
        'M': '#FFFF00',  # Yellow
        'H': '#FFFFFF',  # White
        'I': '#00FF00',  # Green
        'W': '#0000FF'   # Blue
    }
    
    fig = px.bar(
        tire_usage_df,
        x='driver_name',
        y='Laps',
        color='Compound',
        color_discrete_map=compound_colors,
        title="Tire Usage by Driver",
        hover_data=['team_name']
    )
    
    fig.update_layout(
        xaxis_title="Driver",
        yaxis_title="Laps",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show stint information
    st.subheader("Stint Analysis")
    
    # Get stint data
    stint_data = db.execute_query(
        """
        SELECT d.full_name as driver_name, t.name as team_name, t.team_color,
               l.stint, l.compound, MIN(l.lap_number) as start_lap, MAX(l.lap_number) as end_lap,
               COUNT(*) as stint_length
        FROM laps l
        JOIN drivers d ON l.driver_id = d.id
        JOIN teams t ON d.team_id = t.id
        WHERE l.session_id = ? AND l.stint IS NOT NULL
        GROUP BY d.id, l.stint
        ORDER BY d.full_name, l.stint
        """,        
        params=(session_id,)
    )
    
    if not stint_data.empty:
        # Display stint data
        st.dataframe(
            stint_data.drop('team_color', axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        # Create a Gantt-like chart to visualize stints
        fig = go.Figure()
        
        # Add a bar for each stint
        for _, stint in stint_data.iterrows():
            # Choose color based on compound
            color = compound_colors.get(stint['compound'], add_hash_to_color(stint['team_color']))
            
            fig.add_trace(go.Bar(
                x=[stint['stint_length']],
                y=[f"{stint['driver_name']} (Stint {int(stint['stint'])})"],
                orientation='h',
                marker_color=color,
                text=f"{stint['compound']} - {stint['stint_length']} laps",
                hovertemplate=(
                    "Driver: %{y}<br>" +
                    "Compound: " + stint['compound'] + "<br>" +
                    "Stint Length: %{x} laps<br>" +
                    "Lap Range: " + str(int(stint['start_lap'])) + "-" + str(int(stint['end_lap']))
                )
            ))
        
        fig.update_layout(
            title="Race Stints by Driver",
            xaxis_title="Stint Length (laps)",
            yaxis_title="Driver & Stint",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            showlegend=False,
            height=600,
            barmode='relative',
            yaxis={'categoryorder': 'category ascending'}
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No stint data available for this race.")

def show_pit_stop_analysis(db, year):
    """Analyze and visualize pit stop performance."""
    st.subheader("Pit Stop Analysis")
    
    # For pit stop analysis, we'll use the lap data to infer pit stops
    # A pit stop can be identified by a change in stint or compound
    
    # Get all events for the selected year with races
    events_with_races = db.execute_query(
        """
        SELECT DISTINCT e.id, e.round_number, e.event_name
        FROM events e
        JOIN sessions s ON e.id = s.event_id
        WHERE e.year = ? AND s.session_type = 'race'
        ORDER BY e.round_number
        """,        
        params=(year,)
    )
    
    if events_with_races.empty:
        st.info("No race data available for this season.")
        return
    
    # Option to view season-wide analysis or specific race
    analysis_type = st.radio("Analysis Type", ["Season Overview", "Race Specific"])
    
    if analysis_type == "Season Overview":
        # Get pit stop performance across the season
        st.subheader("Season Pit Stop Performance")
        
        # Get teams for comparison
        teams_df = db.execute_query(
            """
            SELECT DISTINCT id, name as team_name, team_color
            FROM teams
            WHERE year = ?
            ORDER BY name
            """,            
            params=(year,)
        )
        
        if teams_df.empty:
            st.info("No team data available for this season.")
            return
        
        # Get pit stop data across all races
        # This is a simplified version as we don't have actual pit stop timing data
        # Instead, we'll count the number of stints as a proxy for pit stops
        pit_stops_by_team = db.execute_query(
            """
            SELECT t.name as team_name, t.team_color, COUNT(DISTINCT l.stint) as pit_stop_count,
                   COUNT(DISTINCT s.id) as race_count
            FROM laps l
            JOIN drivers d ON l.driver_id = d.id
            JOIN teams t ON d.team_id = t.id
            JOIN sessions s ON l.session_id = s.id
            JOIN events e ON s.event_id = e.id
            WHERE e.year = ? AND s.session_type = 'race' AND l.stint > 1
            GROUP BY t.id
            ORDER BY pit_stop_count
            """,            
            params=(year,)
        )
        
        if not pit_stops_by_team.empty:
            # Calculate average pit stops per race
            pit_stops_by_team['avg_pit_stops_per_race'] = pit_stops_by_team['pit_stop_count'] / pit_stops_by_team['race_count']
            
            # Display pit stop data
            st.dataframe(
                pit_stops_by_team.drop('team_color', axis=1),
                use_container_width=True,
                hide_index=True
            )
            
            # Create visualization
            fig = px.bar(
                pit_stops_by_team,
                x='team_name',
                y='avg_pit_stops_per_race',
                color='team_name',
                color_discrete_map={team: add_hash_to_color(color) for team, color in zip(pit_stops_by_team['team_name'], pit_stops_by_team['team_color'])},
                title="Average Pit Stops per Race by Team"
            )
            
            fig.update_layout(
                xaxis_title="Team",
                yaxis_title="Average Pit Stops per Race",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=False,
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No pit stop data available for this season.")
    
    else:  # Race Specific Analysis
        # Allow user to select a race
        selected_event = st.selectbox("Select Race", events_with_races['event_name'].tolist())
        
        # Get the event ID
        event_id = events_with_races[events_with_races['event_name'] == selected_event]['id'].iloc[0]
        
        # Get race session for this event
        race_session = db.execute_query(
            """
            SELECT id
            FROM sessions
            WHERE event_id = ? AND session_type = 'race'
            """,            
            params=(event_id,)
        )
        
        if race_session.empty:
            st.info("No race session available for this event.")
            return
            
        session_id = race_session['id'].iloc[0]
        
        # Get pit stop data for this race
        # Again, we're using stint changes as a proxy for pit stops
        driver_pit_stops = db.execute_query(
            """
            SELECT d.full_name as driver_name, t.name as team_name, t.team_color,
                   COUNT(DISTINCT l.stint) - 1 as pit_stop_count
            FROM laps l
            JOIN drivers d ON l.driver_id = d.id
            JOIN teams t ON d.team_id = t.id
            WHERE l.session_id = ?
            GROUP BY d.id
            ORDER BY pit_stop_count
            """,            
            params=(session_id,)
        )
        
        if not driver_pit_stops.empty:
            # Display pit stop data
            st.dataframe(
                driver_pit_stops.drop('team_color', axis=1),
                use_container_width=True,
                hide_index=True
            )
            
            # Create visualization
            fig = px.bar(
                driver_pit_stops,
                x='driver_name',
                y='pit_stop_count',
                color='team_name',
                color_discrete_map={team: add_hash_to_color(color) for team, color in zip(driver_pit_stops['team_name'].unique(), driver_pit_stops['team_color'].unique())},
                title=f"Pit Stops by Driver - {selected_event}"
            )
            
            fig.update_layout(
                xaxis_title="Driver",
                yaxis_title="Number of Pit Stops",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Get pit stop timing (lap numbers)
            pit_stop_laps = db.execute_query(
                """
                SELECT d.full_name as driver_name, t.name as team_name, t.team_color,
                       l1.stint, MIN(l2.lap_number) as pit_lap
                FROM laps l1
                JOIN laps l2 ON l1.driver_id = l2.driver_id AND l1.session_id = l2.session_id AND l1.stint = l2.stint - 1
                JOIN drivers d ON l1.driver_id = d.id
                JOIN teams t ON d.team_id = t.id
                WHERE l1.session_id = ? AND l2.stint > 1
                GROUP BY d.id, l1.stint
                ORDER BY d.full_name, l1.stint
                """,                
                params=(session_id,)
            )
            
            if not pit_stop_laps.empty:
                st.subheader("Pit Stop Timing")
                
                # Display pit stop lap data
                st.dataframe(
                    pit_stop_laps.drop('team_color', axis=1),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Create scatter plot of pit stop timing
                fig = px.scatter(
                    pit_stop_laps,
                    x='pit_lap',
                    y='driver_name',
                    color='team_name',
                    color_discrete_map={team: add_hash_to_color(color) for team, color in zip(pit_stop_laps['team_name'].unique(), pit_stop_laps['team_color'].unique())},
                    title=f"Pit Stop Timing - {selected_event}",
                    size=[10] * len(pit_stop_laps),
                    hover_data=['stint']
                )
                
                fig.update_layout(
                    xaxis_title="Lap Number",
                    yaxis_title="Driver",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No pit stop data available for this race.")