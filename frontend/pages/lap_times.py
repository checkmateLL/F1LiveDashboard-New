import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError, ResourceNotFoundError

# Initialize data service
data_service = F1DataService()

st.title("⏱ Lap Times Analysis")

def lap_times():
    """Main function to display lap times analysis."""
    try:
        # Get available years
        years = data_service.get_available_years()
        
        # Determine default year from session state
        default_year = st.session_state.get("selected_year", years[0])
        year = st.selectbox("Select Season", options=years, index=years.index(default_year), key="laptimes_year")
        st.session_state["selected_year"] = year

        # Get events for the selected season
        events = data_service.get_events(year)
        event_options = {event["event_name"]: event["id"] for event in events}
        
        if not events or len(events) == 0:
            st.warning("No events available.")
            return
        
        # Determine default event from session state
        default_event = st.session_state.get("selected_event", next(iter(event_options.values())))
        selected_event = st.selectbox("Select Event", options=event_options.keys(), 
                              index=list(event_options.values()).index(default_event_id),
                              key="laptimes_event")
        event_id = event_options[selected_event]
        st.session_state["selected_event"] = event_id

        # Get sessions for the selected event
        sessions = data_service.get_sessions(event_id)
        session_options = {session["name"]: session["id"] for session in sessions}
        
        if not sessions:
            st.warning("No sessions available for this event.")
            return
        
        # Determine default session from session state
        default_session = st.session_state.get("selected_session", next(iter(session_options.values())))
        selected_session = st.selectbox("Select Session", options=session_options.keys(), index=list(session_options.keys()).index(default_session))
        session_id = session_options[selected_session]
        st.session_state["selected_session"] = session_id

        # Load lap times data
        laps_df = data_service.get_lap_times(session_id)
        if laps_df.empty:
            st.warning("No lap time data available for this session.")
            return

        # Convert lap and sector times to seconds
        laps_df["lap_time_sec"] = laps_df["lap_time"].apply(convert_time_to_seconds)
        laps_df["sector1_sec"] = laps_df["sector1_time"].apply(convert_time_to_seconds)
        laps_df["sector2_sec"] = laps_df["sector2_time"].apply(convert_time_to_seconds)
        laps_df["sector3_sec"] = laps_df["sector3_time"].apply(convert_time_to_seconds)

        # Create tabs for different analyses
        tab1, tab2, tab3, tab4 = st.tabs(["Lap Times", "Sector Analysis", "Tire Strategy", "Driver Comparison"])

        with tab1:
            show_lap_time_analysis(laps_df)

        with tab2:
            show_sector_analysis(laps_df)

        with tab3:
            show_tire_analysis(laps_df)

        with tab4:
            show_driver_comparison(laps_df)

    except (DatabaseError, ResourceNotFoundError) as e:
        st.error(f"Error fetching lap times: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")

def convert_time_to_seconds(time_str):
    """Convert lap time strings to seconds."""
    if not time_str or pd.isna(time_str):
        return None

    try:
        parts = time_str.split()
        if len(parts) >= 3:
            time_part = parts[2]
            if ":" in time_part:
                time_sections = time_part.split(":")
                if len(time_sections) == 3:  # hours:minutes:seconds
                    return int(time_sections[0]) * 3600 + int(time_sections[1]) * 60 + float(time_sections[2])
                elif len(time_sections) == 2:  # minutes:seconds
                    return int(time_sections[0]) * 60 + float(time_sections[1])
        
        return float(time_str)
    except (ValueError, IndexError, TypeError):
        return None

def show_lap_time_analysis(laps_df):
    """Show lap time analysis visualization."""
    st.subheader("Lap Time Analysis")
    
    # Sidebar filters
    st.sidebar.subheader("Lap Time Filters")
    
    # Get unique drivers
    drivers = laps_df["driver_name"].unique().tolist()
    
    # Allow user to select drivers
    selected_drivers = st.sidebar.multiselect("Select Drivers", drivers, default=drivers[:5] if len(drivers) > 5 else drivers)
    
    # Filter for deleted laps
    include_deleted = st.sidebar.checkbox("Include Deleted Laps", value=False)
    
    # Apply filters
    filtered_df = laps_df[laps_df["driver_name"].isin(selected_drivers)]
    if not include_deleted:
        filtered_df = filtered_df[~(filtered_df["deleted"] == 1)]
    
    if filtered_df.empty:
        st.warning("No data available with the current filters.")
        return
    
    # Create lap time visualization
    fig = go.Figure()
    
    # Add a line for each driver
    for driver in selected_drivers:
        driver_data = filtered_df[filtered_df["driver_name"] == driver]
        if not driver_data.empty:
            team_color = driver_data["team_color"].iloc[0]
            
            fig.add_trace(go.Scatter(
                x=driver_data["lap_number"],
                y=driver_data["lap_time_sec"],
                mode="lines+markers",
                name=driver,
                line=dict(color=team_color, width=2),
                marker=dict(
                    size=8,
                    color=team_color,
                    symbol="circle"
                ),
                hovertemplate=(
                    f"Driver: {driver}<br>"
                    "Lap: %{x}<br>"
                    "Time: %{y:.3f}s<br>"
                    "Tire: %{customdata[0]}<br>"
                    "Tire Life: %{customdata[1]}"
                ),
                customdata=np.column_stack((
                    driver_data["compound"], 
                    driver_data["tyre_life"]
                ))
            ))
    
    # Update layout
    fig.update_layout(
        title="Lap Times Evolution",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        yaxis=dict(autorange="reversed"),  # Lower times at the top
        hovermode="closest",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500
    )
    
    # Update y-axis to show time in a readable format
    fig.update_yaxes(
        tickvals=[60, 90, 120, 150, 180],
        ticktext=["1:00", "1:30", "2:00", "2:30", "3:00"]
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show fastest laps
    st.subheader("Fastest Laps")
    
    # Get fastest lap for each driver
    fastest_laps = []
    for driver in selected_drivers:
        driver_data = filtered_df[filtered_df["driver_name"] == driver]
        if not driver_data.empty and not driver_data["lap_time_sec"].isna().all():
            fastest_lap = driver_data.loc[driver_data["lap_time_sec"].idxmin()]
            fastest_laps.append({
                "Driver": fastest_lap["driver_name"],
                "Lap": int(fastest_lap["lap_number"]),
                "Time": format_seconds_to_time(fastest_lap["lap_time_sec"]),
                "Time_Sec": fastest_lap["lap_time_sec"],
                "Compound": fastest_lap["compound"],
                "Tire Life": int(fastest_lap["tyre_life"]) if pd.notna(fastest_lap["tyre_life"]) else None,
                "Team": fastest_lap["team_name"]
            })
    
    if fastest_laps:
        # Sort by lap time
        fastest_laps_df = pd.DataFrame(fastest_laps).sort_values("Time_Sec")
        
        # Calculate delta to fastest
        if not fastest_laps_df.empty:
            fastest_time = fastest_laps_df["Time_Sec"].min()
            fastest_laps_df["Delta"] = fastest_laps_df["Time_Sec"].apply(
                lambda x: f"+{(x - fastest_time):.3f}s" if x > fastest_time else "Leader"
            )
        
        # Display dataframe without the Time_Sec column
        st.dataframe(
            fastest_laps_df.drop("Time_Sec", axis=1),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No valid lap times to display.")


def show_sector_analysis(laps_df):
    """Show sector time analysis visualization."""
    st.subheader("Sector Analysis")
    
    # Sidebar filters
    st.sidebar.subheader("Sector Analysis Filters")
    
    # Get unique drivers
    drivers = laps_df["driver_name"].unique().tolist()
    
    # Allow user to select drivers
    selected_drivers = st.sidebar.multiselect("Select Drivers (Sectors)", drivers, default=drivers[:3] if len(drivers) > 3 else drivers)
    
    # Select sector
    sector = st.selectbox("Select Sector", ["Sector 1", "Sector 2", "Sector 3"])
    
    # Map sector selection to dataframe column
    sector_map = {
        "Sector 1": "sector1_sec",
        "Sector 2": "sector2_sec",
        "Sector 3": "sector3_sec"
    }
    
    sector_col = sector_map[sector]
    
    # Apply filtering
    filtered_df = laps_df[laps_df["driver_name"].isin(selected_drivers)]
    filtered_df = filtered_df[~(filtered_df["deleted"] == 1)]
    filtered_df = filtered_df[pd.notna(filtered_df[sector_col])]
    
    if filtered_df.empty:
        st.warning("No sector data available with the current filters.")
        return
    
    # Create sector time visualization
    fig = go.Figure()
    
    # Add a line for each driver
    for driver in selected_drivers:
        driver_data = filtered_df[filtered_df["driver_name"] == driver]
        if not driver_data.empty and not driver_data[sector_col].isna().all():
            team_color = driver_data["team_color"].iloc[0]
            
            fig.add_trace(go.Scatter(
                x=driver_data["lap_number"],
                y=driver_data[sector_col],
                mode="lines+markers",
                name=driver,
                line=dict(color=team_color, width=2),
                marker=dict(
                    size=8,
                    color=team_color,
                    symbol="circle"
                ),
                hovertemplate=(
                    f"Driver: {driver}<br>"
                    "Lap: %{x}<br>"
                    f"{sector} Time: %{{y:.3f}}s<br>"
                    "Tire: %{customdata[0]}"
                ),
                customdata=np.column_stack((driver_data["compound"],))
            ))
    
    # Update layout
    fig.update_layout(
        title=f"{sector} Times",
        xaxis_title="Lap Number",
        yaxis_title=f"{sector} Time (seconds)",
        yaxis=dict(autorange="reversed"),  # Lower times at the top
        hovermode="closest",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show best sector times
    st.subheader(f"Best {sector} Times")
    
    # Get best sector time for each driver
    best_sectors = []
    for driver in selected_drivers:
        driver_data = filtered_df[filtered_df["driver_name"] == driver]
        if not driver_data.empty and not driver_data[sector_col].isna().all():
            best_sector = driver_data.loc[driver_data[sector_col].idxmin()]
            best_sectors.append({
                "Driver": best_sector["driver_name"],
                "Lap": int(best_sector["lap_number"]),
                f"{sector} Time": f"{best_sector[sector_col]:.3f}s",
                "Time_Sec": best_sector[sector_col],
                "Compound": best_sector["compound"],
                "Team": best_sector["team_name"]
            })
    
    if best_sectors:
        # Sort by sector time
        best_sectors_df = pd.DataFrame(best_sectors).sort_values("Time_Sec")
        
        # Calculate delta to fastest
        if not best_sectors_df.empty:
            fastest_time = best_sectors_df["Time_Sec"].min()
            best_sectors_df["Delta"] = best_sectors_df["Time_Sec"].apply(
                lambda x: f"+{(x - fastest_time):.3f}s" if x > fastest_time else "Leader"
            )
        
        # Display dataframe without the Time_Sec column
        st.dataframe(
            best_sectors_df.drop("Time_Sec", axis=1),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info(f"No valid {sector} times to display.")


def show_tire_analysis(laps_df):
    """Show tire and stint analysis visualization."""
    st.subheader("Tire and Stint Analysis")
    
    # Sidebar filters
    st.sidebar.subheader("Tire Analysis Filters")
    
    # Get unique drivers
    drivers = laps_df["driver_name"].unique().tolist()
    
    # Allow user to select drivers
    selected_drivers = st.sidebar.multiselect("Select Drivers (Tires)", drivers, default=drivers[:3] if len(drivers) > 3 else drivers)
    
    # Filter data
    filtered_df = laps_df[laps_df["driver_name"].isin(selected_drivers)]
    filtered_df = filtered_df[~(filtered_df["deleted"] == 1)]
    
    if filtered_df.empty:
        st.warning("No tire data available with the current filters.")
        return
    
    # Create tire degradation visualization
    fig = go.Figure()
    
    # Create a color map for tire compounds
    compound_colors = {
        "S": "red",
        "M": "yellow",
        "H": "white",
        "I": "green",
        "W": "blue"
    }
    
    # Add a scatter point for each lap
    for driver in selected_drivers:
        driver_data = filtered_df[filtered_df["driver_name"] == driver]
        if not driver_data.empty and not driver_data["lap_time_sec"].isna().all():
            team_color = driver_data["team_color"].iloc[0]
            
            # Group by stint
            stints = driver_data["stint"].unique()
            
            for stint in stints:
                stint_data = driver_data[driver_data["stint"] == stint]
                if not stint_data.empty:
                    # Get compound for this stint
                    compound = stint_data["compound"].iloc[0] if pd.notna(stint_data["compound"].iloc[0]) else "Unknown"
                    
                    # Create a name for the legend that includes driver and compound
                    name = f"{driver} - {compound}"
                    
                    # Choose marker color based on compound
                    marker_color = compound_colors.get(compound, team_color)
                    
                    fig.add_trace(go.Scatter(
                        x=stint_data["tyre_life"],
                        y=stint_data["lap_time_sec"],
                        mode="lines+markers",
                        name=name,
                        line=dict(color=marker_color, width=2),
                        marker=dict(
                            size=8,
                            color=marker_color,
                            symbol="circle"
                        ),
                        hovertemplate=(
                            f"Driver: {driver}<br>"
                            "Tire Life: %{x} laps<br>"
                            "Lap Time: %{y:.3f}s<br>"
                            f"Compound: {compound}<br>"
                            "Lap: %{customdata[0]}"
                        ),
                        customdata=np.column_stack((stint_data["lap_number"],))
                    ))
    
    # Update layout
    fig.update_layout(
        title="Tire Degradation Analysis",
        xaxis_title="Tire Life (laps)",
        yaxis_title="Lap Time (seconds)",
        yaxis=dict(autorange="reversed"),  # Lower times at the top
        hovermode="closest",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show stint summary
    st.subheader("Stint Summary")
    
    # Calculate stint information
    stint_summary = []
    for driver in selected_drivers:
        driver_data = filtered_df[filtered_df["driver_name"] == driver]
        if not driver_data.empty:
            # Group by stint
            stints = driver_data["stint"].unique()
            stints = [s for s in stints if pd.notna(s)]
            
            for stint in stints:
                stint_data = driver_data[driver_data["stint"] == stint]
                if len(stint_data) > 1:  # Only include stints with at least 2 laps
                    compound = stint_data["compound"].iloc[0] if pd.notna(stint_data["compound"].iloc[0]) else "Unknown"
                    
                    # Calculate stint statistics
                    stint_length = len(stint_data)
                    min_lap_time = stint_data["lap_time_sec"].min()
                    max_lap_time = stint_data["lap_time_sec"].max()
                    avg_lap_time = stint_data["lap_time_sec"].mean()
                    degradation = (max_lap_time - min_lap_time) / stint_length if stint_length > 0 else 0
                    
                    stint_summary.append({
                        "Driver": driver,
                        "Stint": int(stint),
                        "Compound": compound,
                        "Laps": stint_length,
                        "Min Time": format_seconds_to_time(min_lap_time),
                        "Avg Time": format_seconds_to_time(avg_lap_time),
                        "Deg/Lap": f"{degradation:.3f}s"
                    })
    
    if stint_summary:
        stint_df = pd.DataFrame(stint_summary)
        st.dataframe(stint_df, use_container_width=True, hide_index=True)
    else:
        st.info("No valid stint data to display.")


def show_driver_comparison(laps_df):
    """Show driver comparison visualization."""
    st.subheader("Driver Comparison")
    
    # Get unique drivers
    drivers = laps_df["driver_name"].unique().tolist()
    
    # Create two columns for driver selection
    col1, col2 = st.columns(2)
    
    with col1:
        driver1 = st.selectbox("Select Driver 1", drivers, index=0 if len(drivers) > 0 else 0)
    
    with col2:
        remaining_drivers = [d for d in drivers if d != driver1]
        driver2 = st.selectbox("Select Driver 2", remaining_drivers, index=0 if len(remaining_drivers) > 0 else 0)
    
    # Filter data for the selected drivers
    driver1_data = laps_df[laps_df["driver_name"] == driver1].copy()
    driver2_data = laps_df[laps_df["driver_name"] == driver2].copy()
    
    # Filter out deleted laps
    driver1_data = driver1_data[~(driver1_data["deleted"] == 1)]
    driver2_data = driver2_data[~(driver2_data["deleted"] == 1)]
    
    if driver1_data.empty or driver2_data.empty:
        st.warning("Insufficient data for comparison.")
        return
    
    # Calculate lap time differences
    st.subheader("Lap Time Comparison")
    
    # Create a dataframe for comparison
    common_laps = set(driver1_data["lap_number"]) & set(driver2_data["lap_number"])
    comparison_data = []
    
    for lap in common_laps:
        lap1 = driver1_data[driver1_data["lap_number"] == lap].iloc[0]
        lap2 = driver2_data[driver2_data["lap_number"] == lap].iloc[0]
        
        if pd.notna(lap1["lap_time_sec"]) and pd.notna(lap2["lap_time_sec"]):
            time_diff = lap1["lap_time_sec"] - lap2["lap_time_sec"]
            
            comparison_data.append({
                "Lap": int(lap),
                f"{driver1} Time": format_seconds_to_time(lap1["lap_time_sec"]),
                f"{driver2} Time": format_seconds_to_time(lap2["lap_time_sec"]),
                "Difference": f"{time_diff:.3f}s",
                "Delta": time_diff,
                f"{driver1} Compound": lap1["compound"],
                f"{driver2} Compound": lap2["compound"]
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        
        # Create a visualization of the lap time delta
        fig = go.Figure()
        
        # Add a zero line
        fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="grey")
        
        # Add the delta trace
        driver1_color = driver1_data["team_color"].iloc[0]
        driver2_color = driver2_data["team_color"].iloc[0]
        
        fig.add_trace(go.Bar(
            x=comparison_df["Lap"],
            y=comparison_df["Delta"],
            name=f"{driver1} vs {driver2} Delta",
            marker_color=[driver1_color if d > 0 else driver2_color for d in comparison_df["Delta"]],
            hovertemplate=(
                "Lap: %{x}<br>"
                "Delta: %{y:.3f}s<br>"
                f"{driver1} Time: %{{customdata[0]}}<br>"
                f"{driver2} Time: %{{customdata[1]}}<br>"
                f"{driver1} Tire: %{{customdata[2]}}<br>"
                f"{driver2} Tire: %{{customdata[3]}}"
            ),
            customdata=np.column_stack((
                comparison_df[f"{driver1} Time"],
                comparison_df[f"{driver2} Time"],
                comparison_df[f"{driver1} Compound"],
                comparison_df[f"{driver2} Compound"]
            ))
        ))
        
        # Update layout
        fig.update_layout(
            title=f"Lap Time Delta: {driver1} vs {driver2}",
            xaxis_title="Lap Number",
            yaxis_title="Time Delta (seconds)",
            hovermode="closest",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show the comparison table
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        
        # Calculate overall statistics
        positive_deltas = comparison_df[comparison_df["Delta"] > 0]["Delta"]
        negative_deltas = comparison_df[comparison_df["Delta"] < 0]["Delta"]
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric(
            f"Laps Where {driver1} Faster", 
            len(negative_deltas)
        )
        
        col2.metric(
            f"Laps Where {driver2} Faster", 
            len(positive_deltas)
        )
        
        col3.metric(
            "Average Delta", 
            f"{comparison_df['Delta'].mean():.3f}s"
        )
        
        col4.metric(
            "Largest Delta", 
            f"{comparison_df['Delta'].abs().max():.3f}s"
        )
    else:
        st.info("No common laps available for comparison.")


def format_seconds_to_time(seconds):
    """Format seconds to MM:SS.ms format, ensuring valid formatting."""
    if seconds is None or pd.isna(seconds) or seconds < 0:
        return "N/A"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes:02}:{remaining_seconds:06.3f}"

lap_times()