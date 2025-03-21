import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

from backend.db_connection import get_db_handler

# Helper function for checking if data is empty
def is_data_empty(data):
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

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
            years_query = db.execute_query("SELECT DISTINCT year FROM events ORDER BY year DESC")
            
            if not is_data_empty(years_query):
                # Convert to a simple list if it's a list of dictionaries
                if isinstance(years_query, list) and len(years_query) > 0 and isinstance(years_query[0], dict) and 'year' in years_query[0]:
                    years = [year_dict['year'] for year_dict in years_query]
                else:
                    # Try to convert from DataFrame
                    try:
                        years_df = pd.DataFrame(years_query)
                        years = years_df['year'].tolist()
                    except:
                        # Fallback to default years
                        years = [2025, 2024, 2023]
            else:
                # Fallback to default years
                years = [2025, 2024, 2023]
            
            # Allow user to select a season
            if 'selected_year' in st.session_state:
                if st.session_state['selected_year'] in years:
                    default_year_index = years.index(st.session_state['selected_year'])
                else:
                    default_year_index = 0
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
    drivers_query = db.execute_query(
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
    
    if is_data_empty(drivers_query):
        st.info("No driver data available for this season.")
        return
    
    # Convert to DataFrame if needed
    try:
        drivers_df = pd.DataFrame(drivers_query)
    except:
        st.warning("Could not process driver data.")
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
        try:
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
            
            # Convert to DataFrame if needed
            if not isinstance(quali_data, pd.DataFrame):
                quali_data = pd.DataFrame(quali_data)
            
            if not isinstance(race_data, pd.DataFrame):
                race_data = pd.DataFrame(race_data)
                
            if not isinstance(fastest_laps, pd.DataFrame):
                fastest_laps = pd.DataFrame(fastest_laps)
                
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
        except Exception as e:
            st.warning(f"Error processing driver {driver['driver_name']}: {e}")
    
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
        
        # Display individual performance trends for selected drivers (limit to 3)
        if len(selected_drivers) <= 3:
            for driver_name in selected_drivers:
                try:
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
                    
                    if not is_data_empty(race_results):
                        race_results_df = pd.DataFrame(race_results)
                        
                        # Create individual trend chart
                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatter(
                            x=race_results_df['round_number'],
                            y=race_results_df['position'],
                            mode='lines+markers',
                            name='Position',
                            line=dict(color=add_hash_to_color(driver_color), width=3),
                            hovertemplate=(
                                "Round: %{x}<br>" +
                                "Position: %{y}<br>" +
                                "Race: %{customdata}"
                            ),
                            customdata=race_results_df['event_name']
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
                except Exception as e:
                    st.warning(f"Could not create performance trend for {driver_name}: {e}")
    else:
        st.info("No performance data available for the selected drivers.")


def show_team_performance(db, year):
    """Analyze and visualize team performance metrics."""
    st.subheader("Team Performance Analysis")
    
    # Get all teams for the selected year
    teams_query = db.execute_query(
        """
        SELECT DISTINCT id, name as team_name, team_color
        FROM teams
        WHERE year = ?
        ORDER BY name
        """,        
        params=(year,)
    )
    
    if is_data_empty(teams_query):
        st.info("No team data available for this season.")
        return
        
    # Convert to DataFrame if needed
    try:
        teams_df = pd.DataFrame(teams_query)
    except:
        st.warning("Could not process team data.")
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
        try:
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
            
            # Convert to DataFrame if needed
            if not isinstance(race_data, pd.DataFrame):
                race_data = pd.DataFrame(race_data)
                
            if not isinstance(quali_data, pd.DataFrame):
                quali_data = pd.DataFrame(quali_data)
                
            if not isinstance(results_data, pd.DataFrame):
                results_data = pd.DataFrame(results_data)
            
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
        except Exception as e:
            st.warning(f"Error processing team {team['team_name']}: {e}")
    
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
        
        if not is_data_empty(events):
            # Convert to DataFrame if needed
            try:
                events_df = pd.DataFrame(events)
            except:
                st.warning("Could not process events data.")
                return
                
            # Track cumulative points for each team
            team_progress = []
            
            for _, team in selected_teams_df.iterrows():
                team_id = team['id']
                
                for _, event in events_df.iterrows():
                    # Get all races up to this one
                    previous_events = events_df[events_df['round_number'] <= event['round_number']]
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
                    
                    try:
                        points_data = db.execute_query(query, params=tuple(params))
                        
                        # Convert to DataFrame if needed
                        if not isinstance(points_data, pd.DataFrame):
                            points_data = pd.DataFrame(points_data)
                            
                        points = float(points_data['cumulative_points'].iloc[0]) if not points_data.empty and not pd.isna(points_data['cumulative_points'].iloc[0]) else 0
                        
                        team_progress.append({
                            'Team': team['team_name'],
                            'Round': event['round_number'],
                            'Event': event['event_name'],
                            'Points': points,
                            'Color': team['team_color']
                        })
                    except Exception as e:
                        st.warning(f"Error getting points data: {e}")
            
            # Create progress chart
            if team_progress:
                progress_df = pd.DataFrame(team_progress)
                
                # Create a figure with steps instead of smooth lines
                fig = go.Figure()
                
                # Get all unique teams
                unique_teams = progress_df['Team'].unique()
                
                # Max round to display (only show completed rounds)
                max_round = events_df['round_number'].max()
                completed_rounds_query = db.execute_query(
                    """
                    SELECT MAX(e.round_number) as max_round
                    FROM results r
                    JOIN sessions s ON r.session_id = s.id
                    JOIN events e ON s.event_id = e.id
                    WHERE e.year = ? AND s.session_type = 'race'
                    """,
                    params=(year,)
                )
                
                # Convert to DataFrame if needed
                if not isinstance(completed_rounds_query, pd.DataFrame):
                    completed_rounds_df = pd.DataFrame(completed_rounds_query)
                else:
                    completed_rounds_df = completed_rounds_query
                    
                if not completed_rounds_df.empty and not pd.isna(completed_rounds_df['max_round'].iloc[0]):
                    max_round = min(max_round, completed_rounds_df['max_round'].iloc[0])
                
                for team in unique_teams:
                    team_data = progress_df[progress_df['Team'] == team]
                    team_data = team_data[team_data['Round'] <= max_round].sort_values('Round')
                    
                    if not is_data_empty(team_data):
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
    
    st.info("Tire strategy analysis would be implemented here. This requires additional race-specific data.")
    
    # This is a more complex analysis that would require joining multiple tables
    # and potentially calculating tire stint information from the lap data
    
    # For now, just display a placeholder
    st.markdown("""
    ### Tire Strategy Analysis Features
    
    When implemented, this section would include:
    
    1. Tire compound usage by team
    2. Average stint length by compound
    3. Performance degradation by compound
    4. Optimal tire strategy recommendations
    
    This analysis requires additional data processing capabilities.
    """)


def show_pit_stop_analysis(db, year):
    """Analyze and visualize pit stop performance."""
    st.subheader("Pit Stop Analysis")
    
    st.info("Pit stop analysis would be implemented here. This requires additional race-specific data.")
    
    # This is a more complex analysis that would require joining multiple tables
    # and potentially calculating pit stop timing information from the lap data
    
    # For now, just display a placeholder
    st.markdown("""
    ### Pit Stop Analysis Features
    
    When implemented, this section would include:
    
    1. Average pit stop duration by team
    2. Pit stop success rate
    3. Impact of pit stop timing on race outcome
    4. Comparison of pit strategy effectiveness
    
    This analysis requires additional data processing capabilities.
    """)

performance()