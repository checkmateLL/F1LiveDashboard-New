import streamlit as st
import pandas as pd
from datetime import datetime
from frontend.components.countdown import get_next_event, display_countdown
from backend.data_service import F1DataService

# Initialize data service
data_service = F1DataService()

def home():
    st.title("🏠 F1 Dashboard Home")

    years = data_service.get_available_years()
    year = st.selectbox("Select Season", years)

    events = data_service.get_events(year)
    events_df = pd.DataFrame(events) if events else pd.DataFrame()

    if not events_df.empty:
        events_df['event_date'] = pd.to_datetime(events_df['event_date'], errors='coerce')
        today = pd.Timestamp(datetime.now().date())

        # Identify current event
        events_df['end_date'] = events_df['event_date'] + pd.Timedelta(days=3)
        current_event = events_df[(events_df['event_date'] <= today) & (events_df['end_date'] >= today)]

        if not current_event.empty:
            current_event_info = current_event.iloc[0].to_dict()
            st.subheader("🚦 Current Event")
            st.markdown(f"""
                <div style="padding: 15px; border-radius: 8px; background-color: #228b22; color: white;">
                    <h2>{current_event_info['event_name']}</h2>
                    <p>{current_event_info['country']} | Round {current_event_info['round_number']}</p>
                    <p>{current_event_info['event_date'].strftime('%d %b %Y')} - {(current_event_info['end_date']).strftime('%d %b %Y')}</p>
                </div>
            """, unsafe_allow_html=True)

            sessions = data_service.get_sessions(current_event_info['id'])
            sessions_df = pd.DataFrame(sessions) if sessions else pd.DataFrame()
            sessions_df['date'] = pd.to_datetime(sessions_df['date'], errors='coerce')
            current_session = sessions_df[(sessions_df['date'].dt.date == today.date())]

            if not current_session.empty:
                current_session_info = current_session.iloc[0].to_dict()
                st.markdown(f"""
                    <div style="padding: 10px; border-radius: 8px; background-color: #444; color: white; margin-top: 10px;">
                        <h4>Current Session: {current_session_info['name']}</h4>
                        <p>{current_session_info['session_type'].title()} - {current_session_info['date'].strftime('%H:%M')}</p>
                    </div>
                """, unsafe_allow_html=True)

        next_event = get_next_event(events_df)
        if next_event:
            st.subheader("⏳ Next Event Countdown")
            display_countdown(next_event)
        else:
            st.warning("No upcoming events found.")
    else:
        st.error("No events data available for selected year.")

    st.markdown("---")
    st.subheader("All Events")
    if events_df.empty:
        st.warning("No events found.")
    else:
        st.dataframe(events_df[['round_number', 'event_name', 'country', 'event_date']])

if __name__ == "__main__":
    home()