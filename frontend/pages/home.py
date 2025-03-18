import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

from frontend.components.countdown import get_next_event, display_countdown
from frontend.components.event_cards import event_card
from backend.db_connection import get_db_handler

def home():
    st.title("🏎️ F1 Dashboard - Home")    

    try:
        with get_db_handler() as db:
            current_year = datetime.now().year
            events_df = db.execute_query(
                "SELECT id, round_number, country, location, event_name, event_date FROM events WHERE year = ? ORDER BY event_date",
                params=(current_year,)
            )

            today = datetime.now()

            # Convert event dates to datetime
            if 'event_date' in events_df.columns:
                events_df['event_date_dt'] = pd.to_datetime(events_df['event_date'], errors='coerce')

                past_events = events_df[events_df['event_date_dt'] < today].sort_values(by='event_date_dt', ascending=False)
                upcoming_events = events_df[events_df['event_date_dt'] >= today].sort_values(by='event_date_dt')

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Recent Events")
                    for _, event in past_events.iterrows():
                        event_dict = event.to_dict()
                        event_card(event_dict, is_past=True)

                with col2:
                    st.subheader("Upcoming Events")
                    for _, event in upcoming_events.iterrows():
                        event_dict = event.to_dict()
                        event_card(event_dict, is_past=False)

    except Exception as e:
        st.error(f"Error loading home page: {e}")
 