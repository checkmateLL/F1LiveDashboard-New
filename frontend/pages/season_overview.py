import streamlit as st
import pandas as pd
import sqlite3

# Function to fetch event schedule
def season_overview():
    st.title("🏁 Season Overview")

    conn = sqlite3.connect("f1_data.db")

    # Select season
    year = st.selectbox("Select Season", [2023, 2024, 2025], index=2)

    # Query events
    events = pd.read_sql_query(
        "SELECT round_number, event_name, event_date FROM events WHERE year = ? ORDER BY event_date",
        conn,
        params=(year,)
    )

    st.subheader("Event Schedule")
    st.dataframe(events)

    # Select event and show sessions
    selected_event = st.selectbox("Select Event", events["event_name"].tolist())
    
    if selected_event:
        event_id = pd.read_sql_query(
            "SELECT id FROM events WHERE year = ? AND event_name = ?",
            conn,
            params=(year, selected_event)
        )["id"].iloc[0]

        sessions = pd.read_sql_query(
            "SELECT name, date, session_type FROM sessions WHERE event_id = ?",
            conn,
            params=(event_id,)
        )

        if sessions.empty:
            st.warning("No sessions found for this event.")
        else:
            st.subheader("Sessions")
            st.dataframe(sessions)

    conn.close()

# Run page function
season_overview()