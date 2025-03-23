import streamlit as st
from datetime import datetime
import pandas as pd

def get_next_event(events_df):
    """
    Get the next event from a dataframe of events.
    Returns the next event data as a dict or None if no future events.
    """
    if events_df is None or len(events_df) == 0:
        return None

    events_df['event_date_dt'] = pd.to_datetime(events_df['event_date'], errors='coerce')
    now = pd.Timestamp(datetime.now())

    future_events = events_df[events_df['event_date_dt'] > now].sort_values(by='event_date_dt')

    if future_events.empty:
        return None

    next_event = future_events.iloc[0].to_dict()
    return next_event

def display_countdown(event):
    """
    Display a countdown timer to the next event with enhanced styling and error handling.
    """
    if event is None or 'event_date_dt' not in event:
        st.warning("No upcoming events scheduled.")
        return

    now = pd.Timestamp(datetime.now())
    event_time = event['event_date_dt']

    if pd.isna(event_time):
        st.error("Invalid event date.")
        return

    time_left = event_time - now

    if time_left.total_seconds() <= 0:
        st.warning("Event has already started!")
        return

    days = time_left.days
    hours, remainder = divmod(time_left.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    st.markdown(f"""
    <div style="padding: 15px; border-radius: 10px; background-color: #333; color: white; text-align: center; margin-bottom: 20px;">
        <h2>{event.get('event_name', 'Next Event')} - {event.get('country', '')}</h2>
        <p style="font-size: 18px;">{event_time.strftime('%d %b %Y, %H:%M')}</p>
    </div>
    <div style="display: flex; justify-content: center; gap: 15px;">
        <div style="background-color: #444; padding: 10px; border-radius: 8px; width: 80px;">
            <div style="font-size: 24px;">{days}</div>
            <div>DAYS</div>
        </div>
        <div style="background-color: #444; padding: 10px; border-radius: 8px; width: 80px;">
            <div style="font-size: 24px;">{hours}</div>
            <div>HOURS</div>
        </div>
        <div style="background-color: #444; padding: 10px; border-radius: 8px; width: 80px;">
            <div style="font-size: 24px;">{minutes}</div>
            <div>MINUTES</div>
        </div>
        <div style="background-color: #444; padding: 10px; border-radius: 8px; width: 80px;">
            <div style="font-size: 24px;">{seconds}</div>
            <div>SECONDS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
