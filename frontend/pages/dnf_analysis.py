import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def dnf_analysis():
    """DNF (Did Not Finish) Analysis & Failure Trends."""
    st.title("⚠️ DNF Analysis & Reliability Trends")

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

        # Fetch DNF data from results table (derived from race status)
        dnf_df = data_service.get_dnf_data(session_id)
        if dnf_df.empty:
            st.warning("No DNF data available for this session.")
            return

        # Create visualization tabs
        tab1, tab2, tab3 = st.tabs(["DNF Timeline", "Failure Causes", "Team DNFs"])

        with tab1:
            plot_dnf_timeline(dnf_df)

        with tab2:
            plot_dnf_reasons(dnf_df)

        with tab3:
            plot_team_dnf_analysis(dnf_df)

        # Display DNF dataset
        st.subheader("📋 DNF Data")
        st.dataframe(dnf_df, use_container_width=True)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def plot_dnf_timeline(df):
    """Visualizes DNFs over the race duration."""
    fig = px.scatter(
        df,
        x="lap_number",
        y="driver_name",
        text="team_name",
        title="📌 DNF Timeline (Lap of Retirement)",
        color="failure_reason",
        labels={"lap_number": "Lap", "driver_name": "Driver"},
    )
    fig.update_traces(textposition="top center", marker=dict(size=10))
    st.plotly_chart(fig, use_container_width=True)

def plot_dnf_reasons(df):
    """Shows distribution of failure reasons causing DNFs."""
    if "failure_reason" not in df.columns or df["failure_reason"].isna().all():
        st.info("No failure reasons available for this session.")
        return

    reason_counts = df["failure_reason"].value_counts().reset_index()
    reason_counts.columns = ["Failure Reason", "Count"]

    fig = px.bar(
        reason_counts,
        x="Count",
        y="Failure Reason",
        orientation="h",
        title="⚙️ Breakdown of DNF Causes",
        text="Count",
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_team_dnf_analysis(df):
    """Compares DNFs across teams to detect reliability issues."""
    if "team_name" not in df.columns or df["team_name"].isna().all():
        st.info("No team data available for this session.")
        return

    team_counts = df["team_name"].value_counts().reset_index()
    team_counts.columns = ["Team", "DNFs"]

    fig = px.bar(
        team_counts,
        x="DNFs",
        y="Team",
        orientation="h",
        title="🏎️ DNFs Per Team",
        text="DNFs",
    )
    st.plotly_chart(fig, use_container_width=True)

dnf_analysis()