import streamlit as st
import pandas as pd
from datetime import datetime

from frontend.components.race_visuals import show_race_results, show_position_changes, show_points_distribution, show_race_summary
from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def is_data_empty(data):
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def race_results():
    st.title("🏁 Race Results")

    try:
        years = data_service.get_available_years()
        default_year = st.session_state.get("selected_year", years[0])
        year = st.selectbox("Select Season", years, index=years.index(default_year), key="results_year")
        st.session_state["selected_year"] = year

        events = data_service.get_events(year)
        events_df = pd.DataFrame(events) if events else pd.DataFrame()
        if is_data_empty(events_df):
            st.warning("No events available for this season.")
            return

        event_options = {row["event_name"]: row["id"] for _, row in events_df.iterrows()}
        default_event_id = st.session_state.get("selected_event", next(iter(event_options.values())))
        selected_event = st.selectbox("Select Event", event_options.keys(),
                                      index=list(event_options.values()).index(default_event_id),
                                      key="results_event")
        event_id = event_options[selected_event]
        st.session_state["selected_event"] = event_id

        sessions = data_service.get_race_sessions(event_id)
        sessions_df = pd.DataFrame(sessions) if sessions else pd.DataFrame()
        if is_data_empty(sessions_df):
            st.warning("No race sessions available for this event.")
            return

        session_options = {row["name"]: row["id"] for _, row in sessions_df.iterrows()}
        default_session_id = st.session_state.get("selected_session", next(iter(session_options.values())))
        selected_session = st.selectbox("Select Session", session_options.keys(),
                                        index=list(session_options.values()).index(default_session_id))
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        results = data_service.get_race_results(session_id)
        results_df = pd.DataFrame(results) if results else pd.DataFrame()
        if is_data_empty(results_df):
            st.warning("No race results available for this session.")
            return

        tab1, tab2, tab3 = st.tabs(["Results Table", "Race Analysis", "Points & Stats"])

        with tab1:
            show_race_results(results_df)
            show_race_summary(results_df)

        with tab2:
            st.subheader("Position Changes")
            teams = results_df["team_name"].unique().tolist()
            selected_teams = st.multiselect("Filter by Teams", teams, default=teams)
            filtered_results = results_df[results_df["team_name"].isin(selected_teams)]

            if not is_data_empty(filtered_results):
                show_position_changes(filtered_results)
            else:
                st.warning("No data to display with the current filters.")

        with tab3:
            show_points_distribution(results_df)
            st.subheader("Race Statistics")
            col1, col2 = st.columns(2)

            with col1:
                team_points = results_df.groupby("team_name")["points"].sum().reset_index().sort_values("points", ascending=False)
                st.dataframe(team_points, use_container_width=True, hide_index=True)

            with col2:
                status_counts = results_df["status"].value_counts().reset_index()
                status_counts.columns = ["Status", "Count"]
                st.dataframe(status_counts, use_container_width=True, hide_index=True)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

race_results()