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
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def season_overview():
    """Displays the full season calendar and race details."""
    st.title("📅 F1 Season Overview")

    try:
        # Store selected year in session state
        available_years = data_service.get_available_years()
        if not available_years:
            st.warning("No years available in the database.")
            return
            
        # Make sure available_years is a list
        if not isinstance(available_years, list):
            try:
                available_years = [row['year'] for row in available_years]
            except:
                st.warning("Could not process available years data.")
                return
                
        if len(available_years) == 0:
            st.warning("No years available in the database.")
            return
            
        # Get default year from session state or use first year
        default_year = st.session_state.get("selected_year", available_years[0])
        
        # Make sure default_year is in available_years
        if default_year not in available_years:
            default_year = available_years[0]
            
        selected_year = st.selectbox("Select Season", available_years, index=available_years.index(default_year))
        st.session_state["selected_year"] = selected_year

        # Fetch all events for the selected season
        events_df = data_service.get_events(selected_year)
        
        # Check if events data is empty
        if is_data_empty(events_df):
            st.warning("No events available for this season.")
            return
            
        # Convert to DataFrame if it's not already
        if not isinstance(events_df, pd.DataFrame):
            try:
                events_df = pd.DataFrame(events_df)
            except:
                st.warning("Could not process events data.")
                return

        # Display a season map visualization
        display_season_map(events_df)

        # Season format overview
        display_season_format(events_df, selected_year)

        # Display events in a grid format
        st.subheader("Season Calendar")
        selected_event = event_cards_grid(events_df)

        # Store selected event in session state
        if selected_event:
            st.session_state["selected_event"] = selected_event

        # Display event details if an event is selected
        event_id = st.session_state.get("selected_event", None)
        if event_id:
            display_event_details(event_id)

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

def display_season_map(events_df):
    """Display a world map with all race locations."""
    st.subheader("Season Map")

    # Check if events_df is valid
    if is_data_empty(events_df):
        st.warning("No event data available for map visualization.")
        return
        
    # Ensure required columns exist
    if 'location' not in events_df.columns:
        st.warning("Location data missing for map visualization.")
        return

    # Latitude & Longitude Mapping for Locations
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

    # Assign coordinates
    events_df["lat"] = events_df["location"].map(lambda loc: location_to_coords.get(loc, (None, None))[0])
    events_df["lon"] = events_df["location"].map(lambda loc: location_to_coords.get(loc, (None, None))[1])

    # Drop events with missing coordinates
    map_df = events_df.dropna(subset=["lat", "lon"])
    
    if is_data_empty(map_df):
        st.warning("No valid location data available for map visualization.")
        return

    try:
        # Get year value safely
        year = events_df['year'].iloc[0] if 'year' in events_df.columns else "F1 Season"
    
        fig = px.scatter_geo(
            map_df,
            lat="lat",
            lon="lon",
            hover_name="event_name",
            color="round_number",
            projection="natural earth",
            title=f"{year} F1 Season Map"
        )
    
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating season map: {e}")

def display_season_format(events_df, year):
    """Display season format information (sprint races, etc.)."""
    st.subheader("Season Format")

    # Check if events_df is valid
    if is_data_empty(events_df):
        st.info("No event format data available.")
        return

    if "event_format" in events_df.columns:
        try:
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
        except Exception as e:
            st.error(f"Error displaying season format: {e}")
    else:
        st.info("No event format information available.")

def display_event_details(event_id):
    """Displays event details and sessions."""
    if not event_id:
        return
        
    try:
        event = data_service.get_event_by_id(event_id)
        if event is None:
            st.warning("Event not found.")
            return
    
        sessions = data_service.get_sessions(event_id)
    
        # Display event info
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
    
        # Display sessions
        st.subheader("Sessions")
    
        if not is_data_empty(sessions):
            # Convert to DataFrame if needed
            if not isinstance(sessions, pd.DataFrame):
                try:
                    sessions_df = pd.DataFrame(sessions)
                except:
                    st.warning("Could not process sessions data.")
                    return
            else:
                sessions_df = sessions
                
            # Create display dataframe
            display_cols = ["name", "session_type", "total_laps"]
            display_df = sessions_df[[col for col in display_cols if col in sessions_df.columns]]
            
            # Rename columns
            rename_dict = {
                "name": "Session",
                "session_type": "Type",
                "total_laps": "Laps"
            }
            display_df = display_df.rename(columns={k: v for k, v in rename_dict.items() if k in display_df.columns})
    
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No sessions available for this event.")
    except Exception as e:
        st.error(f"Error displaying event details: {e}")

season_overview()