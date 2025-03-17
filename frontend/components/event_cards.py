import streamlit as st
from datetime import datetime
import pandas as pd

def event_card(event_data, is_past=False):
    """
    Creates a visually appealing event card for F1 events.
    
    Parameters:
    - event_data: Dict containing event information (name, date, round, country, etc.)
    - is_past: Boolean indicating if this is a past event (for visual styling)
    """
    # Format date
    event_date = event_data.get("event_date", "TBA")
    if isinstance(event_date, str) and event_date != "TBA":
        try:
            date_obj = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime("%d %b %Y")
        except:
            formatted_date = event_date
    else:
        formatted_date = "TBA"
    
    # Determine card style based on past/future
    card_style = "past-event" if is_past else "future-event"
    
    # Create the card
    with st.container():
        st.markdown(f"""
        <div class="event-card {card_style}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3>{event_data.get('event_name', 'Unknown Event')}</h3>
                    <p>{event_data.get('country', '')} | Round {event_data.get('round_number', '?')}</p>
                    <p>{formatted_date}</p>
                </div>
                <div>
                    <img src="https://flagcdn.com/32x24/{get_country_code(event_data.get('country', ''))}.png" 
                         alt="{event_data.get('country', '')}" 
                         style="border-radius: 5px;">
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Return True if clicked, False otherwise
    return st.button(f"View {event_data.get('event_name', 'event')}", key=f"btn_{event_data.get('id', 'unknown')}")

def event_cards_grid(events_df, key_prefix=""):
    """
    Creates a grid of event cards from a dataframe of events.
    Returns the selected event ID if any card is clicked.
    """
    if events_df is None or len(events_df) == 0:
        st.warning("No events to display.")
        return None
    
    # Get current date to determine past/future
    current_date = datetime.now().date()
    
    # Create a 3-column grid
    cols = st.columns(3)
    selected_event = None
    
    # Populate grid with event cards
    for idx, event in events_df.iterrows():
        event_date = pd.to_datetime(event["event_date"]).date() if pd.notna(event["event_date"]) else None
        is_past = (event_date is not None and event_date < current_date)
        
        with cols[idx % 3]:
            event_dict = event.to_dict()
            if event_cards_grid(event_dict, is_past):
                selected_event = event_dict.get("id")
    
    return selected_event

def get_country_code(country_name):
    """Maps country names to 2-letter ISO country codes for flag display."""
    country_map = {
        "Australia": "au",
        "Austria": "at",
        "Azerbaijan": "az",
        "Bahrain": "bh",
        "Belgium": "be",
        "Brazil": "br",
        "Canada": "ca",
        "China": "cn",
        "France": "fr",
        "Germany": "de",
        "Hungary": "hu",
        "Italy": "it",
        "Japan": "jp",
        "Mexico": "mx",
        "Monaco": "mc",
        "Netherlands": "nl",
        "Portugal": "pt",
        "Qatar": "qa",
        "Saudi Arabia": "sa",
        "Singapore": "sg",
        "Spain": "es",
        "United Arab Emirates": "ae",
        "United Kingdom": "gb",
        "United States": "us",
        "Miami": "us",
        "Las Vegas": "us",
        "Abu Dhabi": "ae",
        "Emilia Romagna": "it"
    }
    
    return country_map.get(country_name, "xx").lower()