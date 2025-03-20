import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

def create_line_chart(df, x_col, y_col, title, x_label, y_label, driver_color="red", compare_df=None, compare_color="blue"):
    """
    Generic function to create a line chart for telemetry or race data.
    """
    fig = go.Figure()

    # Add primary line
    fig.add_trace(go.Scatter(
        x=df[x_col],
        y=df[y_col],
        mode='lines',
        name="Driver",
        line=dict(color=driver_color, width=3)
    ))

    # Add comparison driver if provided
    if compare_df is not None:
        fig.add_trace(go.Scatter(
            x=compare_df[x_col],
            y=compare_df[y_col],
            mode='lines',
            name="Comparison Driver",
            line=dict(color=compare_color, width=3, dash='dash')
        ))

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        hovermode="closest",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )

    return fig

def create_pie_chart(df, values_col, names_col, title):
    """
    Generic function to create a pie chart.
    """
    fig = px.pie(
        df,
        values=values_col,
        names=names_col,
        title=title
    )

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )

    return fig