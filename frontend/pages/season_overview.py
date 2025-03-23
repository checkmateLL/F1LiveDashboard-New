import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from frontend.components.event_cards import event_cards_grid
from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def is_data_empty(data):
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def season_overview():
    st.title("📅 F1 Season Overview")

    try:
        available_years = data_service.get_available_years()
        if not available_years:
            st.warning("No years available in the database.")
            return

        available_years = [row['year'] for row in available_years] if not isinstance(available_years, list) else available_years
        default_year = st.session_state.get("selected_year", available_years[0])

        selected_year = st.selectbox("Select Season", available_years, index=available_years.index(default_year))
        st.session_state["selected_year"] = selected_year

        events_df = data_service.get_events(selected_year)

        if is_data_empty(events_df):
            st.warning("No events available for this season.")
            return

        events_df = pd.DataFrame(events_df) if not isinstance(events_df, pd.DataFrame) else events_df

        display_season_map(events_df, selected_year)
        display_season_format(events_df, selected_year)

        st.subheader("Season Calendar")
        selected_event = event_cards_grid(events_df)

        if selected_event:
            st.session_state["selected_event"] = selected_event

        event_id = st.session_state.get("selected_event", None)
        if event_id:
            display_event_details(event_id)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def display_season_map(events_df, selected_year):
    st.subheader("Season Map")

    if is_data_empty(events_df):
        st.warning("No event data available for map visualization.")
        return

    location_to_coords = {
        "Melbourne": (-37.8136, 144.9631),
        "Sakhir": (26.0325, 50.5106),
        "Jeddah": (21.5433, 39.1728),
        "Shanghai": (31.3389, 121.2198),
        "Miami": (25.9581, -80.2389),
        "Imola": (44.3439, 11.7167),
        "Monaco": (43.7347, 7.4206),
        "Montreal": (45.5017, -73.5673),
        "Barcelona": (41.57, 2.2611),
        "Spielberg": (47.2197, 14.7647),
        "Silverstone": (52.0786, -1.0169),
        "Budapest": (47.5830, 19.2526),
        "Spa": (50.4372, 5.9719),
        "Zandvoort": (52.3888, 4.5454),
        "Monza": (45.6156, 9.2811),
        "Baku": (40.3724, 49.8533),
        "Singapore": (1.2914, 103.8647),
        "Austin": (30.1328, -97.6411),
        "Mexico City": (19.4042, -99.0907),
        "São Paulo": (-23.7014, -46.6969),
        "Las Vegas": (36.1147, -115.1728),
        "Lusail": (25.4710, 51.4549),
        "Yas Marina": (24.4672, 54.6031)
    }

    events_df["lat"] = events_df["location"].map(lambda loc: location_to_coords.get(loc, (None, None))[0])
    events_df["lon"] = events_df["location"].map(lambda loc: location_to_coords.get(loc, (None, None))[1])

    map_df = events_df.dropna(subset=["lat", "lon"])

    if is_data_empty(map_df):
        st.warning("No valid location data available for map visualization.")
        return

    unique_events = map_df['event_name'].unique()
    colors = px.colors.qualitative.Dark24
    color_map = {event: colors[i % len(colors)] for i, event in enumerate(unique_events)}

    map_df['round_number'] = map_df['round_number'].astype(str)

    fig = px.scatter_geo(
        map_df,
        lat="lat",
        lon="lon",
        hover_name="event_name",
        color="event_name",
        color_discrete_map=color_map,
        hover_data=["round_number"],
        projection="natural earth",
        title=f"{selected_year} F1 Season Map"
    )

    st.plotly_chart(fig, use_container_width=True)

def display_season_format(events_df, year):
    st.subheader("Season Format")

    if is_data_empty(events_df) or "event_format" not in events_df.columns:
        st.info("No event format information available.")
        return

    format_counts = events_df["event_format"].value_counts().reset_index()
    format_counts.columns = ["Format", "Count"]

    col1, col2 = st.columns([2, 3])
    with col1:
        for _, row in format_counts.iterrows():
            st.metric(f"{row['Format']} Events", row["Count"])
        st.metric("Total Events", len(events_df))

    with col2:
        fig = px.pie(
            format_counts,
            values="Count",
            names="Format",
            title=f"{year} Season Format Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)

def display_event_details(event_id):
    if not event_id:
        return

    event = data_service.get_event_by_id(event_id)
    if event is None:
        st.warning("Event not found.")
        return

    sessions = data_service.get_sessions(event_id)

    st.subheader(f"Event Details: {event['event_name']}")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        ### {event['official_event_name']}
        - **Round**: {event['round_number']}
        - **Country**: {event['country']}
        - **Location**: {event['location']}
        - **Date**: {pd.to_datetime(event['event_date']).strftime('%d %b %Y') if pd.notna(event['event_date']) else 'TBA'}
        - **Format**: {event['event_format']}
        """)

    with col2:
        st.image("https://via.placeholder.com/400x200?text=Circuit+Layout", caption=f"{event['location']} Circuit")

    st.subheader("Sessions")

    if not is_data_empty(sessions):
        sessions_df = pd.DataFrame(sessions) if not isinstance(sessions, pd.DataFrame) else sessions
        st.dataframe(sessions_df[["name", "session_type", "total_laps"]].rename(columns={"name": "Session", "session_type": "Type", "total_laps": "Laps"}), use_container_width=True, hide_index=True)
    else:
        st.info("No sessions available for this event.")

season_overview()
