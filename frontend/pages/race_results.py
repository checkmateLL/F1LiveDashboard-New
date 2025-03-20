import streamlit as st
import pandas as pd
from datetime import datetime

from frontend.components.race_visuals import show_race_results, show_position_changes, show_points_distribution, show_race_summary
from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def race_results():
    """Race Results Dashboard."""
    st.title("🏁 Race Results")

    try:
        # Get available years
        years = data_service.get_available_years()
        default_year = st.session_state.get("selected_year", years[0])
        year = st.selectbox("Select Season", years, index=years.index(default_year))
        st.session_state["selected_year"] = year

        # Get events for the selected year
        events_df = data_service.get_events(year)
        if events_df.empty:
            st.warning("No events available for this season.")
            return

        # Default to the first available event
        event_options = {event["event_name"]: event["id"] for event in events_df}
        default_event_id = st.session_state.get("selected_event", next(iter(event_options.values())))
        selected_event = st.selectbox("Select Event", event_options.keys(), index=list(event_options.values()).index(default_event_id))
        event_id = event_options[selected_event]
        st.session_state["selected_event"] = event_id

        # Get race sessions for the selected event
        sessions_df = data_service.get_race_sessions(event_id)
        if sessions_df.empty:
            st.warning("No race sessions available for this event.")
            return

        # Default to first race session
        session_options = {session["name"]: session["id"] for session in sessions_df}
        default_session_id = st.session_state.get("selected_session", next(iter(session_options.values())))
        selected_session = st.selectbox("Select Session", session_options.keys(), index=list(session_options.values()).index(default_session_id))
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        # Get race results
        results_df = data_service.get_race_results(session_id)
        if results_df.empty:
            st.warning("No race results available for this session.")
            return

        # Create tabs for different analyses
        tab1, tab2, tab3 = st.tabs(["Results Table", "Race Analysis", "Points & Stats"])

        with tab1:
            show_race_results(results_df)
            show_race_summary(results_df)

        with tab2:
            show_position_changes(results_df)

            # Add filters
            st.subheader("Filters")

            teams = results_df["team_name"].unique().tolist()
            selected_teams = st.multiselect("Filter by Teams", teams, default=teams)

            filtered_results = results_df[results_df["team_name"].isin(selected_teams)] if selected_teams else results_df

            if not filtered_results.empty:
                show_position_changes(filtered_results)
            else:
                st.warning("No data to display with the current filters.")

        with tab3:
            show_points_distribution(results_df)

            # Display race statistics
            st.subheader("Race Statistics")

            col1, col2 = st.columns(2)

            with col1:
                # Points by team
                team_points = results_df.groupby("team_name")["points"].sum().reset_index().sort_values("points", ascending=False)
                st.subheader("Team Points in this Race")
                st.dataframe(team_points, use_container_width=True, hide_index=True)

            with col2:
                # Status summary (finishers, retirements, etc.)
                status_counts = results_df["status"].value_counts().reset_index()
                status_counts.columns = ["Status", "Count"]
                st.subheader("Race Status Summary")
                st.dataframe(status_counts, use_container_width=True, hide_index=True)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

race_results()