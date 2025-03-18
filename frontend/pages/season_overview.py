import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

from frontend.components.event_cards import event_cards_grid
from backend.db_connection import get_db_handler

def season_overview():
    st.title("📅 F1 Season Overview")    
    
    try:

        with get_db_handler() as db:

            # Get available years from the database
            years_df = db.execute_query("SELECT DISTINCT year FROM events ORDER BY year DESC")
            years = years_df['year'].tolist() if not years_df.empty else [2025, 2024, 2023]
            
            # Allow user to select a season
            year = st.selectbox("Select Season", years, index=0)
            
            # Get all events for the selected season
            events_df = db.execute_query(
                """
                SELECT id, round_number, country, location, official_event_name, 
                    event_name, event_date, event_format
                FROM events
                WHERE year = ?
                ORDER BY round_number
                """,                
                params=(year,)
            )
            
            # Display a season map visualization
            if not events_df.empty:
                display_season_map(events_df)
            
            # Season format overview
            display_season_format(events_df, year)
            
            # Display events in a grid
            st.subheader("Season Calendar")
            selected_event = event_cards_grid(events_df)
            
            # If an event is selected, show detailed information
            if selected_event or ('selected_event' in st.session_state and st.session_state['selected_event']):
                event_id = selected_event if selected_event else st.session_state['selected_event']
                display_event_details(event_id)
    
    except Exception as e:
        st.error(f"Error loading season overview: {e}")


def display_season_map(events_df):
    """Display a world map with all race locations."""
    st.subheader("Season Map")
    
    # Convert event locations to lat/lon
    # In a real implementation, you would have this data in your database
    # For now, use a mock mapping
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
    
    # Add coordinates to events dataframe
    events_with_coords = []
    
    for _, event in events_df.iterrows():
        location = event['location']
        coords = location_to_coords.get(location, (0, 0))  # Default to (0,0) if not found
        
        events_with_coords.append({
            **event.to_dict(),
            'lat': coords[0],
            'lon': coords[1],
            'round': f"Round {event['round_number']}"
        })
    
    map_df = pd.DataFrame(events_with_coords)
    
    # Create a world map visualization
    fig = px.scatter_geo(
        map_df,
        lat='lat',
        lon='lon',
        hover_name='event_name',
        hover_data={
            'round': True,
            'event_date': True,
            'lat': False,
            'lon': False
        },
        size=[20] * len(map_df),  # Fixed size for all points
        color='round_number',
        color_continuous_scale=px.colors.sequential.Plasma,
        projection='natural earth',
        title=f"{events_df['year'].iloc[0] if not events_df.empty else ''} F1 Season Map"
    )
    
    # Update map layout for better appearance
    fig.update_layout(
        geo=dict(
            showland=True,
            landcolor='rgb(30, 30, 30)',
            countrycolor='rgb(60, 60, 60)',
            coastlinecolor='rgb(80, 80, 80)',
            showocean=True,
            oceancolor='rgb(20, 20, 50)',
            showlakes=False,
            showrivers=False,
            showframe=False,
            showcountries=True,
            projection_type='natural earth'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        coloraxis_showscale=False,
        height=500
    )
    
    # Update trace hover template
    fig.update_traces(
        hovertemplate='<b>%{hovertext}</b><br>%{customdata[0]}<br>Date: %{customdata[1]}'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_season_format(events_df, year):
    """Display information about the season format (sprint races, etc.)."""
    st.subheader("Season Format")
    
    # Count the number of events by format
    if 'event_format' in events_df.columns:
        format_counts = events_df['event_format'].value_counts().reset_index()
        format_counts.columns = ['Format', 'Count']
        
        col1, col2 = st.columns([2, 3])
        
        with col1:
            for _, row in format_counts.iterrows():
                st.metric(f"{row['Format']} Events", row['Count'])
            
            # Add total races metric
            st.metric("Total Events", len(events_df))
        
        with col2:
            # Create a simple pie chart of event formats
            fig = px.pie(
                format_counts,
                values='Count',
                names='Format',
                title=f"{year} Season Format Distribution",
                color_discrete_sequence=px.colors.sequential.Plasma
            )
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Event format information not available.")

def display_event_details(event_id, db):
    """Display detailed information about a specific event."""
    # Get event details
    event_df = db.execute_query(
        """
        SELECT id, year, round_number, country, location, official_event_name, 
               event_name, event_date, event_format
        FROM events
        WHERE id = ?
        """,        
        params=(event_id,)
    )
    
    if event_df.empty:
        st.warning("Event not found.")
        return
    
    event = event_df.iloc[0]
    
    # Get sessions for this event
    sessions_df = db.execute_query(
        """
        SELECT id, name, date, session_type, total_laps
        FROM sessions
        WHERE event_id = ?
        ORDER BY date
        """,        
        params=(event_id,)
    )
    
    # Display event information
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
        # Display a placeholder image for the circuit
        # In a real implementation, you would have actual circuit images
        st.image("https://via.placeholder.com/400x200?text=Circuit+Layout", 
                 caption=f"{event['location']} Circuit")
    
    # Display sessions
    st.subheader("Sessions")
    
    if not sessions_df.empty:
        # Format the session table for display
        display_df = sessions_df.copy()
        
        # Convert dates to a more readable format
        if 'date' in display_df.columns:
            display_df['date'] = pd.to_datetime(display_df['date'], errors='coerce')
            display_df['formatted_date'] = display_df['date'].dt.strftime('%d %b %Y, %H:%M')
        
        # Rename columns for better display
        display_df = display_df.rename(columns={
            'name': 'Session',
            'formatted_date': 'Date & Time',
            'session_type': 'Type',
            'total_laps': 'Laps'
        })
        
        if 'date' in display_df.columns:
            display_df = display_df.drop('date', axis=1)
        
        if 'id' in display_df.columns:
            display_df = display_df.drop('id', axis=1)
        
        # Display the sessions table
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Add buttons to view session results
        st.subheader("View Session Data")
        session_cols = st.columns(len(sessions_df) if len(sessions_df) <= 5 else 5)
        
        for i, (_, session) in enumerate(sessions_df.iterrows()):
            col_idx = i % 5
            with session_cols[col_idx]:
                if st.button(f"View {session['name']}", key=f"btn_session_{session['id']}"):
                    # Store selection in session state and redirect to appropriate page
                    session_type = session['session_type']
                    st.session_state['selected_session'] = session['id']
                    
                    if session_type == 'race':
                        st.session_state['page'] = 'Race Results'
                    elif session_type in ['qualifying', 'sprint_shootout', 'sprint_qualifying']:
                        st.session_state['page'] = 'Lap Times'
                    elif session_type == 'sprint':
                        st.session_state['page'] = 'Race Results'
                    else:  # practice sessions
                        st.session_state['page'] = 'Telemetry Analysis'
                    
                    st.experimental_rerun()
    else:
        st.info("No sessions available for this event.")