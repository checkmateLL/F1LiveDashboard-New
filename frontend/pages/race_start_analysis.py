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

def race_start_analysis():
    """Race Start Performance & Position Gains."""
    st.title("🚦 Race Start Analysis")

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

        # Fetch lap 1 data
        lap1_df = data_service.get_lap_times(session_id, lap_number=1)
        if is_data_empty(lap1_df):
            st.warning("No data available for lap 1.")
            return pd.DataFrame()

        # Fetch grid positions
        results_df = data_service.get_race_results(session_id)
        if is_data_empty(results_df):
            st.warning("No race result data available.")
            return pd.DataFrame()

        # Merge grid positions with first-lap positions
        start_data = results_df[["driver_name", "grid_position", "team_name"]].merge(
            lap1_df[["driver_name", "position", "lap_time", "sector1_time"]],
            on="driver_name"
        )

        # Calculate position gains/losses
        start_data["Position Change"] = start_data["grid_position"] - start_data["position"]

        # Create visualization tabs
        tab1, tab2 = st.tabs(["Position Gains", "Reaction Time"])

        with tab1:
            plot_start_position_changes(start_data)

        with tab2:
            plot_reaction_time_analysis(start_data)

        # Display dataset
        st.subheader("📊 Race Start Performance Data")
        st.dataframe(start_data, use_container_width=True)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def plot_start_position_changes(df):
    """Visualizes position gains/losses at the start."""
    fig = px.bar(
        df,
        x="driver_name",
        y="Position Change",
        color="team_name",
        title="📈 Position Gains at Race Start",
        text="Position Change",
    )
    fig.update_layout(yaxis_title="Position Change (Higher is Better)")
    st.plotly_chart(fig, use_container_width=True)

def plot_reaction_time_analysis(df):
    """Analyzes reaction times using sector 1 times."""
    if "sector1_time" not in df.columns:
        st.info("No reaction time data available.")
        return

    fig = px.bar(
        df,
        x="driver_name",
        y="sector1_time",
        color="team_name",
        title="⏱️ Reaction Time (Sector 1 Performance)",
        text="sector1_time",
    )
    fig.update_layout(yaxis_title="Sector 1 Time (Lower is Better)")
    st.plotly_chart(fig, use_container_width=True)

race_start_analysis()