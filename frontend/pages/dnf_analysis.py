
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def is_data_empty(data):
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def dnf_analysis():
    """DNF (Did Not Finish) Analysis & Failure Trends."""
    st.title("⚠️ DNF Analysis & Reliability Trends")

    try:
        # Fetch available years
        available_years = data_service.get_available_years()
        selected_year = st.selectbox(
            "Select Season",
            available_years,
            index=available_years.index(
                st.session_state.get("selected_year", available_years[0])
            )
            if st.session_state.get("selected_year", available_years[0]) in available_years
            else 0,
        )
        st.session_state["selected_year"] = selected_year

        # Fetch events
        events = data_service.get_events(selected_year)
        if not events:
            st.warning("No events available.")
            return

        event_options = {event["event_name"]: event["id"] for event in events}
        event_names = list(event_options.keys())
        event_ids = list(event_options.values())

        default_event_id = st.session_state.get("selected_event", event_ids[0])
        if default_event_id not in event_ids:
            default_event_id = event_ids[0]
        default_event_name = next(name for name, eid in event_options.items() if eid == default_event_id)

        selected_event = st.selectbox("Select Event", event_names, index=event_names.index(default_event_name))
        event_id = event_options[selected_event]
        st.session_state["selected_event"] = event_id

        # Fetch race sessions
        sessions = data_service.get_race_sessions(event_id)
        if not sessions:
            st.warning("No race sessions available.")
            return

        session_options = {session["name"]: session["id"] for session in sessions}
        session_names = list(session_options.keys())
        session_ids = list(session_options.values())

        default_session_id = st.session_state.get("selected_session", session_ids[0])
        if default_session_id not in session_ids:
            default_session_id = session_ids[0]
        default_session_name = next(name for name, sid in session_options.items() if sid == default_session_id)

        selected_session = st.selectbox("Select Session", session_names, index=session_names.index(default_session_name))
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        # Fetch DNF data from results table (derived from race status)
        dnf_df = data_service.get_dnf_data(session_id)
        if is_data_empty(dnf_df):
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
        x="classified_position",
        y="driver_name",
        text="team_name",
        title="📌 DNF Timeline (Lap of Retirement)",
        color="status",
        labels={"lap_number": "Lap", "driver_name": "Driver"},
    )
    fig.update_traces(textposition="top center", marker=dict(size=10))
    st.plotly_chart(fig, use_container_width=True)

def plot_dnf_reasons(df):
    """Shows distribution of failure reasons (from status)."""
    if "status" not in df.columns or df["status"].isna().all():
        st.info("No DNF statuses available for this session.")
        return

    reason_counts = df["status"].value_counts().reset_index()
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
