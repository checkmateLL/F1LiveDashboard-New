import streamlit as st
import pandas as pd
from frontend.components.common_visualizations import create_pie_chart, create_line_chart

def show_race_results(results_df):
    """Display formatted race results."""
    if results_df.empty:
        st.warning("No race results available.")
        return

    st.subheader("🏁 Race Results")
    
    # Format race table
    display_df = results_df.rename(columns={
        'position': 'Pos',
        'driver_name': 'Driver',
        'team_name': 'Team',
        'grid_position': 'Grid',
        'points': 'Points',
        'race_time': 'Time',
        'status': 'Status'
    })

    # Add position change column
    if 'grid_position' in results_df.columns and 'position' in results_df.columns:
        display_df['Δ Pos'] = results_df['grid_position'] - results_df['position']

    # Display results
    st.dataframe(display_df, use_container_width=True, hide_index=True)

def show_position_changes(results_df):
    """Create position change chart."""
    if results_df.empty:
        return

    # Create position change visualization
    fig = create_line_chart(
        results_df, "grid_position", "position",
        "Position Changes (Start to Finish)", "Start Position", "Finish Position",
        driver_color="red"
    )

    st.plotly_chart(fig, use_container_width=True)

def show_points_distribution(results_df):
    """Show pie chart of points distribution."""
    if results_df.empty or 'points' not in results_df.columns:
        return

    # Group points by team
    team_points = results_df.groupby(['team_name'])['points'].sum().reset_index()

    # Create pie chart
    fig = create_pie_chart(team_points, "points", "team_name", "Points Distribution by Team")
    st.plotly_chart(fig, use_container_width=True)

# Add this to frontend/components/race_visuals.py
def show_race_summary(results_df):
    """Display a comprehensive race summary with key statistics."""
    if results_df.empty:
        return
    
    st.subheader("Race Summary")
    
    # Create 4 columns for key stats
    cols = st.columns(4)
    
    # Stats to show
    if 'position' in results_df.columns and len(results_df) > 0:
        winner = results_df[results_df['position'] == 1]
        if len(winner) > 0:
            cols[0].metric("Winner", winner['driver_name'].iloc[0])
    
    if 'grid_position' in results_df.columns and 'position' in results_df.columns:
        # Best recovery
        results_df['position_change'] = results_df['grid_position'] - results_df['position']
        best_recovery = results_df[results_df['position_change'] > 0].sort_values('position_change', ascending=False)
        if len(best_recovery) > 0:
            cols[1].metric("Best Recovery", 
                         f"{best_recovery['driver_name'].iloc[0]} (+{best_recovery['position_change'].iloc[0]})")
    
    # Number of finishers
    if 'status' in results_df.columns:
        finishers = results_df[results_df['status'] == 'Finished'].shape[0]
        cols[2].metric("Finishers", f"{finishers}/{len(results_df)}")
    
    # Points leader (if points exist)
    if 'points' in results_df.columns:
        points_leader = results_df.sort_values('points', ascending=False)
        if len(points_leader) > 0 and points_leader['points'].iloc[0] > 0:
            cols[3].metric("Most Points", 
                         f"{points_leader['driver_name'].iloc[0]} ({points_leader['points'].iloc[0]})")