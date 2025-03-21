# frontend/components/race_visuals.py (partial update)

import streamlit as st
import pandas as pd
import numpy as np

def is_data_empty(data):
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def show_race_results(results_df):
    """Display formatted race results."""
    if is_data_empty(results_df):
        st.warning("No race results available.")
        return

    st.subheader("🏁 Race Results")
    
    # Convert to DataFrame if needed
    if not isinstance(results_df, pd.DataFrame) and isinstance(results_df, (list, dict)):
        try:
            results_df = pd.DataFrame(results_df)
        except:
            st.warning("Could not process race results data.")
            return
    
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
    if is_data_empty(results_df):
        return

    # Ensure we have the necessary data
    if not all(col in results_df.columns for col in ['grid_position', 'position', 'driver_name']):
        st.warning("Missing required position data columns.")
        return
    
    # Make sure data is in a format we can use
    try:
        import plotly.graph_objects as go
        
        # Sort by final position
        df = results_df.sort_values('position')
        
        # Create figure
        fig = go.Figure()
        
        # Add a line for each driver
        for i, row in df.iterrows():
            if pd.isna(row['grid_position']) or pd.isna(row['position']):
                continue
                
            team_color = row['team_color']
            if not team_color.startswith('#'):
                team_color = f"#{team_color}"
                
            fig.add_trace(go.Scatter(
                x=['Start', 'Finish'],
                y=[row['grid_position'], row['position']],
                mode='lines+markers',
                name=row['driver_name'],
                line=dict(color=team_color, width=3),
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
    except Exception as e:
        st.error(f"Error creating position changes chart: {e}")

def show_points_distribution(results_df):
    """Show pie chart of points distribution."""
    if is_data_empty(results_df) or 'points' not in results_df.columns:
        return

    try:
        import plotly.express as px
        
        # Group points by team
        team_points = results_df.groupby(['team_name'])['points'].sum().reset_index()
        
        # Only include teams with points
        team_points = team_points[team_points['points'] > 0]
        
        if is_data_empty(team_points):
            return
        
        # Create pie chart
        fig = px.pie(
            team_points,
            values="points",
            names="team_name",
            title="Points Distribution by Team"
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating points distribution chart: {e}")

def show_race_summary(results_df):
    """Display a comprehensive race summary with key statistics."""
    if is_data_empty(results_df):
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
        # Calculate position changes
        results_df['position_change'] = results_df['grid_position'] - results_df['position']
        
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
        if len(points_leader) > 0 and points_leader['points'].iloc[0] > 0:
            cols[3].metric("Most Points", 
                         f"{points_leader['driver_name'].iloc[0]} ({points_leader['points'].iloc[0]})")

# frontend/components/telemetry_visuals.py (partial update)

def show_telemetry_chart(telemetry_df, metric='speed', title=None, compare_with=None):
    """
    Display telemetry data chart.
    
    Parameters:
    - telemetry_df: DataFrame containing telemetry data
    - metric: The telemetry metric to visualize (speed, throttle, brake, etc.)
    - title: Optional title for the chart
    - compare_with: Optional second telemetry DataFrame to compare with
    """
    if is_data_empty(telemetry_df):
        st.warning("No telemetry data available.")
        return
    
    # Convert to DataFrame if needed
    if not isinstance(telemetry_df, pd.DataFrame) and isinstance(telemetry_df, (list, dict)):
        try:
            telemetry_df = pd.DataFrame(telemetry_df)
        except:
            st.warning("Could not process telemetry data.")
            return
    
    # Ensure required columns exist
    required_cols = ['distance', metric]
    missing_cols = [col for col in required_cols if col not in telemetry_df.columns]

    if missing_cols:
        st.warning(f"Missing required columns: {', '.join(missing_cols)}")
        return

    try:
        import plotly.graph_objects as go
        
        # Generate chart
        title = title or f"{metric.capitalize()} vs Distance"
        
        fig = go.Figure()
        
        # Add main trace
        driver_color = telemetry_df.get('team_color', ['red'])[0]
        
        fig.add_trace(go.Scatter(
            x=telemetry_df["distance"],
            y=telemetry_df[metric],
            mode='lines',
            name='Driver',
            line=dict(color=driver_color, width=3)
        ))
        
        # Add comparison trace if provided
        if compare_with is not None and not is_data_empty(compare_with):
            if not isinstance(compare_with, pd.DataFrame):
                try:
                    compare_with = pd.DataFrame(compare_with)
                except:
                    st.warning("Could not process comparison data.")
                    return
                    
            compare_color = compare_with.get('team_color', ['blue'])[0]
            
            fig.add_trace(go.Scatter(
                x=compare_with["distance"],
                y=compare_with[metric],
                mode='lines',
                name='Comparison',
                line=dict(color=compare_color, width=3, dash='dash')
            ))
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title="Distance (m)",
            yaxis_title=metric.capitalize(),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        # Display chart
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating telemetry chart: {e}")

def show_track_map(telemetry_df, highlight_points=None, compare_df=None):
    """
    Display a track map visualization.
    
    Parameters:
    - telemetry_df: DataFrame with x, y coordinates
    - highlight_points: List of points to highlight
    - compare_df: Optional comparison DataFrame
    """
    if is_data_empty(telemetry_df):
        st.warning("No track map data available.")
        return
        
    # Convert to DataFrame if needed
    if not isinstance(telemetry_df, pd.DataFrame) and isinstance(telemetry_df, (list, dict)):
        try:
            telemetry_df = pd.DataFrame(telemetry_df)
        except:
            st.warning("Could not process track map data.")
            return
    
    # Check for required columns
    if 'x' not in telemetry_df.columns or 'y' not in telemetry_df.columns:
        st.warning("Missing x, y coordinates for track map.")
        return
    
    try:
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        # Add main track
        fig.add_trace(go.Scatter(
            x=telemetry_df['x'],
            y=telemetry_df['y'],
            mode='lines',
            name='Track',
            line=dict(color='red', width=3)
        ))
        
        # Add comparison if provided
        if compare_df is not None and not is_data_empty(compare_df):
            if not isinstance(compare_df, pd.DataFrame):
                try:
                    compare_df = pd.DataFrame(compare_df)
                except:
                    st.warning("Could not process comparison data.")
                    return
                    
            if 'x' in compare_df.columns and 'y' in compare_df.columns:
                fig.add_trace(go.Scatter(
                    x=compare_df['x'],
                    y=compare_df['y'],
                    mode='lines',
                    name='Comparison',
                    line=dict(color='blue', width=3, dash='dash')
                ))
        
        # Add highlighted points
        if highlight_points and isinstance(highlight_points, list) and len(highlight_points) > 0:
            x_points = [p[0] for p in highlight_points if len(p) >= 2]
            y_points = [p[1] for p in highlight_points if len(p) >= 2]
            
            fig.add_trace(go.Scatter(
                x=x_points,
                y=y_points,
                mode='markers',
                name='Highlights',
                marker=dict(color='yellow', size=10)
            ))
        
        # Update layout
        fig.update_layout(
            title="Track Map",
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating track map: {e}")