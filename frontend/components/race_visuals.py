import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

def show_race_results(results_df):
    """Display formatted race results table with team colors."""
    if results_df is None or len(results_df) == 0:
        st.warning("No race results available.")
        return
    
    # Create formatted table
    st.subheader("🏁 Race Results")
    
    # Add position change column
    if 'grid_position' in results_df.columns and 'position' in results_df.columns:
        results_df['position_change'] = results_df['grid_position'] - results_df['position']
        
    # Format the dataframe for display
    display_df = results_df.copy()
    
    # Rename columns for better display
    column_map = {
        'position': 'Pos',
        'driver_name': 'Driver',
        'team_name': 'Team',
        'grid_position': 'Grid',
        'points': 'Points',
        'race_time': 'Time',
        'status': 'Status',
        'position_change': 'Δ Pos'
    }
    
    # Select and rename columns
    cols_to_show = [col for col in column_map.keys() if col in display_df.columns]
    display_df = display_df[cols_to_show]
    display_df = display_df.rename(columns=column_map)
    
    # Format position change column with arrows and colors
    if 'Δ Pos' in display_df.columns:
        display_df['Δ Pos'] = display_df['Δ Pos'].apply(
            lambda x: f"🔼 {x}" if x > 0 else (f"🔽 {abs(x)}" if x < 0 else "◯")
        )
    
    # Display the formatted table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

def show_position_changes(results_df):
    """Create a visual chart showing position changes from grid to finish."""
    if results_df is None or len(results_df) == 0:
        return
    
    if not ('grid_position' in results_df.columns and 'position' in results_df.columns):
        return
    
    # Sort by final position
    df = results_df.sort_values('position')
    
    # Create figure
    fig = go.Figure()
    
    # Add a line for each driver
    for i, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=['Start', 'Finish'],
            y=[row['grid_position'], row['position']],
            mode='lines+markers',
            name=row['driver_name'],
            line=dict(color=row['team_color'], width=3),
            marker=dict(size=10),
            hovertemplate="Position: %{y}<br>Driver: " + row['driver_name']
        ))
    
    # Update layout
    fig.update_layout(
        title="Grid to Finish Position Changes",
        xaxis_title="Race Progress",
        yaxis_title="Position",
        yaxis=dict(
            autorange="reversed",
            dtick=1,
            gridcolor='rgba(150, 150, 150, 0.2)'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_points_distribution(results_df):
    """Show pie chart of points distribution by team."""
    if results_df is None or len(results_df) == 0 or 'points' not in results_df.columns:
        return
    
    # Group by team and sum points
    team_points = results_df.groupby(['team_name', 'team_color'])['points'].sum().reset_index()
    
    # Filter teams with points
    team_points = team_points[team_points['points'] > 0]
    
    if len(team_points) == 0:
        return
    
    # Create pie chart
    fig = px.pie(
        team_points, 
        values='points', 
        names='team_name',
        color='team_name',
        color_discrete_map={team: color for team, color in zip(team_points['team_name'], team_points['team_color'])},
        title="Points Distribution by Team"
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_race_summary(results_df):
    """Display a comprehensive race summary with key statistics."""
    if results_df is None or len(results_df) == 0:
        return
    
    st.subheader("Race Summary")
    
    # Create 4 columns for key stats
    cols = st.columns(4)
    
    # Stats to show
    if 'position' in results_df.columns and len(results_df) > 0:
        winner = results_df[results_df['position'] == 1]
        if len(winner) > 0:
            cols[0].metric("Winner", winner['driver_name'].iloc[0])
    
    if 'position_change' in results_df.columns:
        # Best recovery
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
        if len(points_leader) > 0:
            cols[3].metric("Most Points", 
                          f"{points_leader['driver_name'].iloc[0]} ({points_leader['points'].iloc[0]})")