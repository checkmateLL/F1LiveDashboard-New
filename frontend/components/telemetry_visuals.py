import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

def show_telemetry_chart(telemetry_df, metric='speed', title=None, compare_with=None):
    """
    Display telemetry data chart.
    
    Parameters:
    - telemetry_df: DataFrame containing telemetry data
    - metric: The telemetry metric to visualize (speed, throttle, brake, etc.)
    - title: Optional title for the chart
    - compare_with: Optional second telemetry DataFrame to compare with
    """
    if telemetry_df is None or len(telemetry_df) == 0:
        st.warning("No telemetry data available.")
        return
    
    # Ensure required columns exist
    required_cols = ['time', 'session_time', metric]
    missing_cols = [col for col in required_cols if col not in telemetry_df.columns]
    
    if missing_cols:
        st.warning(f"Missing required columns for telemetry visualization: {', '.join(missing_cols)}")
        return
    
    # Format column names for display
    metric_display = metric.capitalize()
    if metric_display == 'Rpm':
        metric_display = 'RPM'
    
    # Set default title if not provided
    if title is None:
        title = f"{metric_display} Telemetry"
    
    # Create basic figure
    fig = go.Figure()
    
    # Add main telemetry line
    driver_name = telemetry_df.get('driver_name', ['Driver 1'])[0] if 'driver_name' in telemetry_df.columns else 'Driver 1'
    driver_color = telemetry_df.get('team_color', ['#e10600'])[0] if 'team_color' in telemetry_df.columns else '#e10600'
    
    # Add the main driver's telemetry
    fig.add_trace(go.Scatter(
        x=telemetry_df['session_time'] if 'session_time' in telemetry_df.columns else telemetry_df['time'],
        y=telemetry_df[metric],
        mode='lines',
        name=driver_name,
        line=dict(color=driver_color, width=3)
    ))
    
    # Add comparison telemetry if provided
    if compare_with is not None and len(compare_with) > 0:
        compare_driver = compare_with.get('driver_name', ['Driver 2'])[0] if 'driver_name' in compare_with.columns else 'Driver 2'
        compare_color = compare_with.get('team_color', ['#0600EF'])[0] if 'team_color' in compare_with.columns else '#0600EF'
        
        fig.add_trace(go.Scatter(
            x=compare_with['session_time'] if 'session_time' in compare_with.columns else compare_with['time'],
            y=compare_with[metric],
            mode='lines',
            name=compare_driver,
            line=dict(color=compare_color, width=3, dash='dash')
        ))
    
    # Update layout for better appearance
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title=metric_display,
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
        height=400
    )
    
    # Add special y-axis configurations based on metric
    if metric == 'speed':
        fig.update_layout(yaxis=dict(title="Speed (km/h)"))
    elif metric == 'throttle':
        fig.update_layout(yaxis=dict(title="Throttle %", range=[0, 100]))
    elif metric == 'brake':
        fig.update_layout(yaxis=dict(title="Brake", range=[0, 1]))
    elif metric == 'rpm':
        fig.update_layout(yaxis=dict(title="RPM"))
    elif metric == 'gear':
        fig.update_layout(yaxis=dict(title="Gear", dtick=1))
    elif metric == 'drs':
        fig.update_layout(yaxis=dict(title="DRS", range=[-0.5, 1.5], dtick=1))
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True)

def show_track_map(telemetry_df, highlight_points=None):
    """
    Display a track map (x, y coordinates) with optional highlight points.
    
    Parameters:
    - telemetry_df: DataFrame containing x and y coordinates
    - highlight_points: Optional list of tuples (index, color, label) to highlight specific points
    """
    if telemetry_df is None or len(telemetry_df) == 0:
        return
    
    # Check if x and y coordinates are present
    if 'x' not in telemetry_df.columns or 'y' not in telemetry_df.columns:
        return
    
    # Create a track map visualization
    fig = go.Figure()
    
    # Add the track outline
    driver_color = telemetry_df.get('team_color', ['#e10600'])[0] if 'team_color' in telemetry_df.columns else '#e10600'
    
    fig.add_trace(go.Scatter(
        x=telemetry_df['x'],
        y=telemetry_df['y'],
        mode='lines',
        line=dict(color=driver_color, width=3),
        name='Track'
    ))
    
    # Add highlight points if provided
    if highlight_points:
        for idx, color, label in highlight_points:
            if idx < len(telemetry_df):
                fig.add_trace(go.Scatter(
                    x=[telemetry_df['x'].iloc[idx]],
                    y=[telemetry_df['y'].iloc[idx]],
                    mode='markers',
                    marker=dict(size=10, color=color),
                    name=label
                ))
    
    # Update layout
    fig.update_layout(
        title="Track Map",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(
            showgrid=False,
            showticklabels=False
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            scaleanchor="x",
            scaleratio=1
        ),
        height=600
    )