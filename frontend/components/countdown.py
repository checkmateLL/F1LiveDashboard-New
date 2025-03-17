import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

def get_next_event(events_df):
    """
    Get the next event from a dataframe of events.
    Returns the next event data as a dict or None if no future events.
    """
    if events_df is None or len(events_df) == 0:
        return None
    
    # Convert event dates to datetime objects
    events_df['event_date_dt'] = pd.to_datetime(events_df['event_date'], errors='coerce')
    
    # Get current date
    now = datetime.now()
    
    # Filter to only future events
    future_events = events_df[events_df['event_date_dt'] > now].sort_values(by='event_date_dt')
    
    if len(future_events) == 0:
        return None
    
    # Return the next event
    next_event = future_events.iloc[0].to_dict()
    return next_event

def display_countdown(event):
    """
    Display a countdown timer to the next event.
    """
    if event is None or 'event_date_dt' not in event:
        st.warning("No upcoming events scheduled.")
        return
    
    now = datetime.now()
    event_time = event['event_date_dt']
    
    if isinstance(event_time, pd.Timestamp):
        event_time = event_time.to_pydatetime()
    
    time_left = event_time - now
    
    # If event is in the past
    if time_left.total_seconds() <= 0:
        st.warning("Event has already started!")
        return
    
    # Calculate days, hours, minutes and seconds
    days = time_left.days
    hours = time_left.seconds // 3600
    minutes = (time_left.seconds // 60) % 60
    seconds = time_left.seconds % 60
    
    # Create a nice-looking countdown display
    st.markdown("""
    <style>
    .countdown-container {
        display: flex;
        justify-content: center;
        text-align: center;
        margin: 20px 0;
    }
    .countdown-box {
        background-color: #e10600;
        color: white;
        border-radius: 5px;
        padding: 15px;
        margin: 0 10px;
        min-width: 80px;
    }
    .countdown-value {
        font-size: 32px;
        font-weight: bold;
    }
    .countdown-label {
        font-size: 14px;
        margin-top: 5px;
    }
    .countdown-event {
        text-align: center;
        font-size: 24px;
        margin-bottom: 10px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Event name and date
    st.markdown(f"""
    <div class="countdown-event">
        {event.get('event_name', 'Next Event')} - {event.get('country', '')}
    </div>
    <div style="text-align: center; margin-bottom: 20px;">
        {event_time.strftime('%d %b %Y, %H:%M')}
    </div>
    """, unsafe_allow_html=True)
    
    # Countdown boxes
    st.markdown(f"""
    <div class="countdown-container">
        <div class="countdown-box">
            <div class="countdown-value">{days}</div>
            <div class="countdown-label">DAYS</div>
        </div>
        <div class="countdown-box">
            <div class="countdown-value">{hours}</div>
            <div class="countdown-label">HOURS</div>
        </div>
        <div class="countdown-box">
            <div class="countdown-value">{minutes}</div>
            <div class="countdown-label">MINUTES</div>
        </div>
        <div class="countdown-box">
            <div class="countdown-value">{seconds}</div>
            <div class="countdown-label">SECONDS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)