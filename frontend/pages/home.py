import streamlit as st
import pandas as pd
from datetime import datetime

from frontend.components.countdown import get_next_event, display_countdown
from frontend.components.event_cards import event_card
from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def home():
    """Home Page - Displays recent and upcoming events with countdown."""
    st.title("🏎️ F1 Dashboard - Home")

    try:
        # Store selected year in session state
        current_year = datetime.now().year
        if "selected_year" not in st.session_state:
            st.session_state["selected_year"] = current_year

        # Fetch all events for the selected year
        events_df = data_service.get_events(st.session_state["selected_year"])
        if not events_df or len(events_df) == 0:
            st.warning("No events available for this season.")
            return

        today = datetime.now()

        # Convert event dates to datetime
        events_df["event_date_dt"] = pd.to_datetime(events_df["event_date"], errors="coerce")

        # Separate past & upcoming events
        past_events = events_df[events_df["event_date_dt"] < today].sort_values(by="event_date_dt", ascending=False)
        upcoming_events = events_df[events_df["event_date_dt"] >= today].sort_values(by="event_date_dt")

        # Event Countdown
        next_event = get_next_event(events_df)
        if next_event:
            display_countdown(next_event)
        else:
            st.info("No upcoming events available.")

        # Display recent & upcoming events
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Recent Events")
            for _, event in past_events.iterrows():
                event_card(event.to_dict(), is_past=True)

        with col2:
            st.subheader("Upcoming Events")
            for _, event in upcoming_events.iterrows():
                event_card(event.to_dict(), is_past=False)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

home()