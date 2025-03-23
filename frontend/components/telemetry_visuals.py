import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from frontend.components.common_visualizations import create_line_chart


def is_data_empty(data):
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)


def ensure_dataframe(data):
    if not isinstance(data, pd.DataFrame):
        try:
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error converting data to DataFrame: {e}")
            return pd.DataFrame()
    return data


def show_telemetry_chart(telemetry_df, metric='speed', title=None, compare_with=None):
    telemetry_df = ensure_dataframe(telemetry_df)

    if is_data_empty(telemetry_df):
        st.warning("No telemetry data available.")
        return

    required_cols = ['distance', metric]
    missing_cols = [col for col in required_cols if col not in telemetry_df.columns]
    if missing_cols:
        st.warning(f"Missing required columns: {', '.join(missing_cols)}")
        return

    title = title or f"{metric.capitalize()} vs Distance"

    fig = go.Figure()

    driver_color = telemetry_df.get('team_color', ['red'])[0]

    fig.add_trace(go.Scatter(
        x=telemetry_df["distance"],
        y=telemetry_df[metric],
        mode='lines',
        name='Driver',
        line=dict(color=driver_color, width=3)
    ))

    if compare_with is not None and not is_data_empty(compare_with):
        compare_with = ensure_dataframe(compare_with)
        if not is_data_empty(compare_with):
            compare_missing_cols = [col for col in required_cols if col not in compare_with.columns]
            if not compare_missing_cols:
                compare_color = compare_with.get('team_color', ['blue'])[0]
                fig.add_trace(go.Scatter(
                    x=compare_with["distance"],
                    y=compare_with[metric],
                    mode='lines',
                    name='Comparison',
                    line=dict(color=compare_color, width=3, dash='dash')
                ))

    fig.update_layout(
        title=title,
        xaxis_title="Distance (m)",
        yaxis_title=metric.capitalize(),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )

    st.plotly_chart(fig, use_container_width=True)


def show_track_map(telemetry_df, highlight_points=None, compare_df=None):
    telemetry_df = ensure_dataframe(telemetry_df)

    if is_data_empty(telemetry_df):
        st.warning("No track map data available.")
        return

    required_cols = ['x', 'y']
    missing_cols = [col for col in required_cols if col not in telemetry_df.columns]
    if missing_cols:
        st.warning(f"Missing required columns: {', '.join(missing_cols)}")
        return

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=telemetry_df['x'],
        y=telemetry_df['y'],
        mode='lines',
        name='Track',
        line=dict(color='red', width=3)
    ))

    if compare_df is not None and not is_data_empty(compare_df):
        compare_df = ensure_dataframe(compare_df)
        if not is_data_empty(compare_df) and all(col in compare_df.columns for col in required_cols):
            fig.add_trace(go.Scatter(
                x=compare_df['x'],
                y=compare_df['y'],
                mode='lines',
                name='Comparison',
                line=dict(color='blue', width=3, dash='dash')
            ))

    if highlight_points and isinstance(highlight_points, list):
        x_points = [p[0] for p in highlight_points if len(p) >= 2]
        y_points = [p[1] for p in highlight_points if len(p) >= 2]

        fig.add_trace(go.Scatter(
            x=x_points,
            y=y_points,
            mode='markers',
            name='Highlights',
            marker=dict(color='yellow', size=10)
        ))

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