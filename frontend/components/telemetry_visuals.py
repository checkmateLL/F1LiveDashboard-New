import streamlit as st
import pandas as pd
import numpy as np
from frontend.components.common_visualizations import create_line_chart

def show_telemetry_chart(telemetry_df, metric='speed', compare_with=None):
    """
    Display telemetry data chart using distance as the x-axis.
    """
    if telemetry_df is None or len(telemetry_df) == 0:
        st.warning("No telemetry data available.")
        return

    # Ensure required columns exist
    required_cols = ['distance', metric]
    missing_cols = [col for col in required_cols if col not in telemetry_df.columns]

    if missing_cols:
        st.warning(f"Missing required columns: {', '.join(missing_cols)}")
        return

    # Generate chart
    title = f"{metric.capitalize()} vs Distance"
    fig = create_line_chart(
        telemetry_df, "distance", metric, title, "Distance (m)", metric.capitalize(),
        driver_color=telemetry_df.get('team_color', ['red'])[0],
        compare_df=compare_with
    )

    # Display chart
    st.plotly_chart(fig, use_container_width=True)