import streamlit as st
from datetime import datetime
import pandas as pd

def event_card(event_data, is_past=False):
    """
    Creates an event card that navigates to the appropriate page when clicked.
    """
    event_id = event_data.get('id', 'unknown')

    page_destination = "Analytics" if is_past else "Event Schedule"

    event_date = event_data.get("event_date", "TBA")
    try:
        date_obj = pd.to_datetime(event_date)
        formatted_date = date_obj.strftime("%d %b %Y") if pd.notna(date_obj) else "TBA"
    except Exception:
        formatted_date = "TBA"

    country_code = get_country_code(event_data.get('country', ''))
    flag_url = f"https://flagcdn.com/w40/{country_code}.png"

    st.markdown(f"""
    <div class="event-card {'past-event' if is_past else 'future-event'}" 
         style="padding: 15px; border-radius: 8px; margin-bottom: 10px; background-color: #1e1e1e;">
        <h3>{event_data.get('event_name', 'Unknown Event')}</h3>
        <p>{event_data.get('country', '')} | Round {event_data.get('round_number', '?')}</p>
        <p>{formatted_date}</p>
    </div>
    """, unsafe_allow_html=True)

    st.image(flag_url, width=40)

    if st.button(f"View {event_data.get('event_name')}", key=f"btn_{event_id}"):
        st.session_state["selected_event"] = event_id
        st.session_state["page"] = page_destination
        st.rerun()


def event_cards_grid(events_df, key_prefix=""):
    if events_df is None or len(events_df) == 0:
        st.warning("No events to display.")
        return None

    current_date = pd.Timestamp(datetime.now().date())

    cols = st.columns(3)
    selected_event = None

    if isinstance(events_df, pd.DataFrame) and 'event_date' in events_df.columns:
        events_df['event_date_dt'] = pd.to_datetime(events_df['event_date'], errors='coerce')

    for idx, event in events_df.iterrows():
        event_dict = event.to_dict() if isinstance(event, pd.Series) else event

        event_date = event_dict.get('event_date_dt')
        if pd.isna(event_date):
            is_past = False
        else:
            is_past = event_date.date() < current_date.date()

        with cols[idx % 3]:
            card_clicked = event_card(event_dict, is_past)
            if card_clicked:
                selected_event = event_dict.get("id")
                st.session_state['selected_event'] = selected_event
                st.session_state['selected_year'] = event_dict.get("year", datetime.now().year)

    return selected_event


def get_country_code(country_name):
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