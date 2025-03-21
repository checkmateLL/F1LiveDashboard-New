import streamlit as st
from datetime import datetime
import pandas as pd

def event_card(event_data, is_past=False):
    """
    Creates an event card that navigates to the appropriate page when clicked.
    """
    event_id = event_data.get('id', 'unknown')

    # Ensure Event Schedule is correctly referenced
    page_destination = "Analytics" if is_past else "Event Schedule"

    # Format date
    event_date = event_data.get("event_date", "TBA")
    try:
        date_obj = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
        formatted_date = date_obj.strftime("%d %b %Y")
    except:
        formatted_date = event_date

    # Country flag
    country_code = get_country_code(event_data.get('country', ''))
    flag_url = f"https://flagcdn.com/w40/{country_code}.png"  # Adjusted size

    # Display event card
    st.markdown(f"""
    <div class="event-card {'past-event' if is_past else 'future-event'}" 
         style="padding: 15px; border-radius: 8px; margin-bottom: 10px; background-color: #1e1e1e;">
        <h3>{event_data.get('event_name', 'Unknown Event')}</h3>
        <p>{event_data.get('country', '')} | Round {event_data.get('round_number', '?')}</p>
        <p>{formatted_date}</p>
    </div>
    """, unsafe_allow_html=True)

    # Display country flag
    st.image(flag_url, width=40)

    # Fix: Ensure navigation updates session state
    if st.button(f"View {event_data.get('event_name')}", key=f"btn_{event_id}"):
        st.session_state["selected_event"] = event_id
        st.session_state["page"] = page_destination
        st.rerun()  # Forces navigation to update


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
    
    # Convert event_date to datetime if it's a string
    if isinstance(events_df, pd.DataFrame) and 'event_date' in events_df.columns:
        events_df['event_date_dt'] = pd.to_datetime(events_df['event_date'], errors='coerce')
    
    # Populate grid with event cards
    for idx, event in events_df.iterrows():
        # Convert to dictionary for consistent handling
        if isinstance(event, pd.Series):
            event_dict = event.to_dict()
        else:
            event_dict = event
            
        # Check if it's a past event
        event_date = event_dict.get('event_date_dt', None)
        if event_date is None and 'event_date' in event_dict:
            try:
                event_date = pd.to_datetime(event_dict['event_date']).date()
            except:
                event_date = None
                
        is_past = (event_date is not None and event_date < current_date)
        
        # Place in appropriate column
        with cols[idx % 3]:
            # Create card and check if clicked
            card_clicked = event_card(event_dict, is_past)
            if card_clicked:
                selected_event = event_dict.get("id")
                # Store in session state for other components to use
                st.session_state['selected_event'] = selected_event
                st.session_state['selected_year'] = event_dict.get("year", datetime.now().year)
    
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