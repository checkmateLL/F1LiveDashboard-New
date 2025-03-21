import streamlit as st
import pandas as pd
import plotly.express as px
import time

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError

# Initialize data service
data_service = F1DataService()

def is_data_empty(data):
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def race_replay():
    """Race Replay Visualization."""
    st.title("📽️ Race Replay")

    try:
        # Get available years
        available_years = data_service.get_available_years()
        
        # Make sure available_years is a list
        if not isinstance(available_years, list):
            try:
                available_years = [row['year'] for row in available_years]
            except:
                available_years = [2025]  # Default if we can't process
                
        if len(available_years) == 0:
            st.warning("No years available in the database.")
            return
        
        # Get default year from session state or use first year
        default_year = st.session_state.get("selected_year", available_years[0])
        
        # Make sure default_year is in available_years
        if default_year not in available_years:
            default_year = available_years[0]
            
        selected_year = st.selectbox("Select Season", available_years, 
                             index=available_years.index(default_year),
                             key="replay_year")
        st.session_state["selected_year"] = selected_year

        # Get all events for the selected season
        events_df = data_service.get_events(selected_year)
        
        if is_data_empty(events_df):
            st.warning("No events available for this season.")
            return
            
        # Convert to DataFrame if needed
        if not isinstance(events_df, pd.DataFrame):
            try:
                events_df = pd.DataFrame(events_df)
            except:
                st.warning("Could not process events data.")
                return

        # Default to first available event or the one stored in session state
        event_options = {}
        for idx, event in events_df.iterrows():
            event_options[event["event_name"]] = event["id"]
            
        if not event_options:
            st.warning("No events available for this season.")
            return
            
        # Default to event stored in session state or first event
        default_event_id = st.session_state.get("selected_event", None)
        default_index = 0
        
        if default_event_id is not None:
            # Find the index of the default event
            event_ids = list(event_options.values())
            if default_event_id in event_ids:
                default_index = event_ids.index(default_event_id)
        
        selected_event = st.selectbox("Select Event", list(event_options.keys()), index=default_index)
        event_id = event_options[selected_event]
        st.session_state["selected_event"] = event_id

        # Get race sessions for the selected event
        sessions_df = data_service.get_race_sessions(event_id)
        
        if is_data_empty(sessions_df):
            st.warning("No race sessions available for this event.")
            return
            
        # Convert to DataFrame if needed
        if not isinstance(sessions_df, pd.DataFrame):
            try:
                sessions_df = pd.DataFrame(sessions_df)
            except:
                st.warning("Could not process session data.")
                return

        # Create session options
        session_options = {}
        for idx, session in sessions_df.iterrows():
            session_options[session["name"]] = session["id"]
            
        if not session_options:
            st.warning("No sessions available.")
            return
            
        # Default to session stored in session state or first session
        default_session_id = st.session_state.get("selected_session", None)
        default_session_index = 0
        
        if default_session_id is not None:
            # Find the index of the default session
            session_ids = list(session_options.values())
            if default_session_id in session_ids:
                default_session_index = session_ids.index(default_session_id)
                
        selected_session = st.selectbox("Select Session", list(session_options.keys()), index=default_session_index)
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        # Fetch lap data for replay
        laps_df = data_service.get_laps(session_id)
        
        if is_data_empty(laps_df):
            st.warning("No lap data available for this session.")
            return
            
        # Convert to DataFrame if needed
        if not isinstance(laps_df, pd.DataFrame):
            try:
                laps_df = pd.DataFrame(laps_df)
            except:
                st.warning("Could not process lap data.")
                return

        # Check if required columns are present
        required_cols = ['lap_number', 'x', 'y', 'driver_name']
        missing_cols = [col for col in required_cols if col not in laps_df.columns]
        
        if missing_cols:
            st.warning(f"Missing required replay data: {', '.join(missing_cols)}")
            st.info("This feature requires position data (x, y coordinates) for the race.")
            return

        # Convert lap number to a timeline
        lap_numbers = sorted(laps_df["lap_number"].unique())
        
        if not lap_numbers:
            st.warning("No lap numbers found in the data.")
            return
            
        lap = st.slider("Select Lap to Replay", min_value=min(lap_numbers), max_value=max(lap_numbers), value=min(lap_numbers))

        # Filter for the selected lap
        lap_data = laps_df[laps_df["lap_number"] == lap]

        if is_data_empty(lap_data):
            st.warning(f"No data available for lap {lap}.")
            return

        # Plot positions for the lap
        try:
            fig = px.scatter(
                lap_data,
                x="x", y="y", 
                color="driver_name",
                text="driver_abbreviation" if "driver_abbreviation" in lap_data.columns else None,
                title=f"Race Replay - Lap {lap}",
                labels={"x": "Track X Position", "y": "Track Y Position"}
            )
    
            # Add hover data if columns are available
            hover_data = []
            for col in ["team_name", "position", "compound"]:
                if col in lap_data.columns:
                    hover_data.append(col)
                    
            if hover_data:
                fig.update_traces(hovertemplate="%{hovertext}", hovertext=[
                    "<br>".join([f"{col}: {row[col]}" for col in hover_data if pd.notna(row[col])])
                    for _, row in lap_data.iterrows()
                ])
    
            fig.update_traces(textposition="top center")
            fig.update_layout(height=600)
    
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating track position plot: {e}")

        # Live Replay Simulation
        if st.button("Start Replay"):
            st.info("Starting race replay simulation...")
            progress_bar = st.progress(0)
            
            for i, lap_num in enumerate(lap_numbers):
                # Update progress
                progress = int((i / len(lap_numbers)) * 100)
                progress_bar.progress(progress)
                
                # Get data for this lap
                lap_data = laps_df[laps_df["lap_number"] == lap_num]
                
                if is_data_empty(lap_data):
                    continue

                try:
                    # Create the visualization
                    fig = px.scatter(
                        lap_data,
                        x="x", y="y", 
                        color="driver_name",
                        text="driver_abbreviation" if "driver_abbreviation" in lap_data.columns else None,
                        title=f"Race Replay - Lap {lap_num}",
                        labels={"x": "Track X Position", "y": "Track Y Position"}
                    )
                    
                    # Add hover data if columns are available
                    hover_data = []
                    for col in ["team_name", "position", "compound"]:
                        if col in lap_data.columns:
                            hover_data.append(col)
                            
                    if hover_data:
                        fig.update_traces(hovertemplate="%{hovertext}", hovertext=[
                            "<br>".join([f"{col}: {row[col]}" for col in hover_data if pd.notna(row[col])])
                            for _, row in lap_data.iterrows()
                        ])
            
                    fig.update_traces(textposition="top center")
                    fig.update_layout(height=600)
                    
                    # Create a placeholder for the chart
                    chart_placeholder = st.empty()
                    
                    # Update the chart
                    chart_placeholder.plotly_chart(fig, use_container_width=True)
                    
                    # Wait before showing next lap (adjust for speed)
                    time.sleep(1.5)  # Simulates replay speed
                except Exception as e:
                    st.error(f"Error in replay for lap {lap_num}: {e}")
                    break
                    
            # Complete the progress bar
            progress_bar.progress(100)
            st.success("Race replay complete!")

    except DatabaseError as e:
        st.error(f"⚠️ Database error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

race_replay()