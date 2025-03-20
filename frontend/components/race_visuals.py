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