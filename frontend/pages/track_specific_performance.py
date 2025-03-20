import streamlit as st
import pandas as pd
import plotly.express as px

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def track_specific_performance():
    """Track-Specific Performance Analysis."""
    st.title("🏎️ Track-Specific Performance Analysis")

    try:
        # Fetch available years
        available_years = data_service.get_available_years()
        selected_year = st.selectbox("Select Season", available_years, index=available_years.index(st.session_state.get("selected_year", available_years[0])))
        st.session_state["selected_year"] = selected_year

        # Fetch events
        events = data_service.get_events(selected_year)
        if not events:
            st.warning("No events available.")
            return

        event_options = {event["event_name"]: event["id"] for event in events}
        selected_event = st.selectbox("Select Event", event_options.keys(), index=list(event_options.values()).index(st.session_state.get("selected_event", next(iter(event_options.values())))))
        event_id = event_options[selected_event]
        st.session_state["selected_event"] = event_id

        # Fetch track-specific session data
        track_df = data_service.get_track_performance(event_id)
        if track_df.empty:
            st.warning("No data available for this track.")
            return

        # Create visualization tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Driver Performance", "Tire Usage", "Weather Impact", "Telemetry Trends"])

        with tab1:
            plot_driver_performance(track_df)

        with tab2:
            plot_tire_performance(track_df)

        with tab3:
            plot_weather_impact(track_df)

        with tab4:
            plot_telemetry_trends(track_df)

        # Display dataset
        st.subheader("📊 Track Performance Data")
        st.dataframe(track_df, use_container_width=True)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def plot_driver_performance(df):
    """Visualizes driver performances at a specific track."""
    fig = px.box(
        df,
        x="year",
        y="final_position",
        color="driver_name",
        title="🏁 Driver Performance Across Years",
        labels={"final_position": "Final Position"},
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_tire_performance(df):
    """Analyzes tire compound performance at the track."""
    fig = px.box(
        df,
        x="compound",
        y="lap_time",
        color="driver_name",
        title="🔥 Tire Performance at Selected Track",
        labels={"lap_time": "Lap Time (s)"},
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_weather_impact(df):
    """Evaluates weather impact on lap times."""
    fig = px.scatter_matrix(
        df,
        dimensions=["track_temp", "air_temp", "wind_speed"],
        color="lap_time",
        title="🌦️ Weather Impact on Lap Times",
        labels={"lap_time": "Lap Time (s)"},
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_telemetry_trends(df):
    """Analyzes telemetry impact on performance."""
    fig = px.scatter_matrix(
        df,
        dimensions=["speed", "throttle", "brake"],
        color="lap_time",
        title="📊 Telemetry Factors Affecting Lap Time",
        labels={"lap_time": "Lap Time (s)"},
    )
    st.plotly_chart(fig, use_container_width=True)

track_specific_performance()