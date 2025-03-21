import streamlit as st
import pandas as pd
import plotly.express as px

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def is_data_empty(data):
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def weather_impact_analysis():
    """Weather Impact on Tire Performance & Race Strategy."""
    st.title("🌦️ Weather Impact Analysis")

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

        # Fetch race sessions
        sessions = data_service.get_race_sessions(event_id)
        if not sessions:
            st.warning("No race sessions available.")
            return

        session_options = {session["name"]: session["id"] for session in sessions}
        selected_session = st.selectbox("Select Session", session_options.keys(), index=list(session_options.values()).index(st.session_state.get("selected_session", next(iter(session_options.values())))))
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        # Fetch weather impact data
        weather_df = data_service.get_weather_impact_data(session_id)
        if is_data_empty(weather_df):
            st.warning("No weather impact data available.")
            return pd.DataFrame()

        # Create visualization tabs
        tab1, tab2, tab3 = st.tabs(["Weather vs Lap Time", "Weather Trends", "Tire Performance"])

        with tab1:
            plot_weather_vs_lap_time(weather_df)

        with tab2:
            plot_weather_trends(weather_df)

        with tab3:
            plot_tire_performance_by_weather(weather_df)

        # Display dataset
        st.subheader("📊 Weather Impact Data")
        st.dataframe(weather_df, use_container_width=True)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def plot_weather_vs_lap_time(df):
    """Visualizes the relationship between weather conditions and lap time."""
    fig = px.scatter_matrix(
        df,
        dimensions=["track_temp", "air_temp", "humidity", "wind_speed"],
        color="lap_time",
        title="🌡️ Weather Impact on Lap Times",
        labels={"lap_time": "Lap Time (s)"},
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_weather_trends(df):
    """Shows how weather conditions changed over the race."""
    fig = px.line(
        df,
        x="lap_number",
        y=["track_temp", "air_temp", "humidity", "wind_speed"],
        title="📊 Weather Conditions Over Laps",
        labels={"lap_number": "Lap Number"},
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_tire_performance_by_weather(df):
    """Compares lap times by tire compound under different weather conditions."""
    fig = px.box(
        df,
        x="compound",
        y="lap_time",
        color="track_temp",
        title="🏎️ Tire Performance vs Track Temperature",
        labels={"lap_time": "Lap Time (s)", "compound": "Tire Compound"},
    )
    st.plotly_chart(fig, use_container_width=True)

weather_impact_analysis()