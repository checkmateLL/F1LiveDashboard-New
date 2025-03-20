import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from backend.data_service import F1DataService
from backend.error_handling import DatabaseError, ResourceNotFoundError

# Initialize data service
data_service = F1DataService()

st.title("Race Analysis")

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
                    hours = int(time_sections[0])
                    minutes = int(time_sections[1])
                    seconds = float(time_sections[2])
                    return hours * 3600 + minutes * 60 + seconds
                elif len(time_sections) == 2:  # minutes:seconds
                    minutes = int(time_sections[0])
                    seconds = float(time_sections[1])
                    return minutes * 60 + seconds
        
        return float(time_str)
    except (ValueError, IndexError, TypeError):
        return None

def format_seconds_to_time(seconds):
    """Format seconds to MM:SS.ms format."""
    if pd.isna(seconds):
        return None
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:.3f}"


def race_analysis():
    """Race Analysis Dashboard"""
    try:
        years = data_service.get_available_years()
        year = st.selectbox("Select Season", years)

        events = data_service.get_events(year)
        event_options = {event["event_name"]: event["id"] for event in events}
        selected_event = st.selectbox("Select Event", options=event_options.keys())

        event_id = event_options[selected_event]
        sessions = data_service.get_sessions(event_id)
        session_options = {session["name"]: session["id"] for session in sessions}
        
        selected_session = st.selectbox("Select Session", options=session_options.keys())
        session_id = session_options[selected_session]

        # Get lap data
        laps_df = data_service.get_lap_times(session_id)
        if laps_df.empty:
            st.warning("No lap data available for this session.")
            return
        
        # Convert time values
        laps_df['lap_time_sec'] = laps_df['lap_time'].apply(convert_time_to_seconds)
        laps_df['sector1_sec'] = laps_df['sector1_time'].apply(convert_time_to_seconds)
        laps_df['sector2_sec'] = laps_df['sector2_time'].apply(convert_time_to_seconds)
        laps_df['sector3_sec'] = laps_df['sector3_time'].apply(convert_time_to_seconds)

        # Race Analysis Tabs
        tabs = st.tabs(["Lap Time Analysis", "Tire Strategy", "Driver Comparison", "Sector Analysis", "Telemetry Analysis", "Race Overview"])

        # TAB 1: LAP TIME ANALYSIS
        with tabs[0]:
            show_lap_time_analysis(laps_df)

        # TAB 2: TIRE STRATEGY
        with tabs[1]:
            show_tire_strategy_analysis(laps_df)

        # TAB 3: DRIVER COMPARISON
        with tabs[2]:
            show_driver_comparison(laps_df)

        # TAB 4: SECTOR ANALYSIS
        with tabs[3]:
            show_sector_analysis(laps_df)

        # TAB 5: TELEMETRY
        with tabs[4]:
            show_telemetry_analysis(session_id)

        # TAB 6: RACE OVERVIEW
        with tabs[5]:
            show_race_overview(laps_df)

    except Exception as e:
        st.error(f"Error in race analysis: {e}")

def show_lap_time_analysis(laps_df):
    """Show lap time analysis visualization."""
    st.subheader("Lap Time Analysis")
    drivers = laps_df['driver_name'].unique().tolist()
    selected_drivers = st.multiselect("Select Drivers", drivers, default=drivers[:5])
    
    filtered_df = laps_df[laps_df['driver_name'].isin(selected_drivers)]
    view_type = st.radio("View Type", ["Lap Time Evolution", "Lap Time Distribution", "Gap to Fastest Lap"])

    if view_type == "Lap Time Evolution":
        fig = go.Figure()
        for driver in selected_drivers:
            driver_data = filtered_df[filtered_df['driver_name'] == driver]
            team_color = driver_data['team_color'].iloc[0]
            fig.add_trace(go.Scatter(
                x=driver_data['lap_number'],
                y=driver_data['lap_time_sec'],
                mode='lines+markers',
                name=driver,
                line=dict(color=team_color, width=2),
            ))

        fig.update_layout(title="Lap Time Evolution", xaxis_title="Lap Number", yaxis_title="Lap Time (seconds)")
        st.plotly_chart(fig, use_container_width=True)

def show_tire_strategy_analysis(laps_df):
    """Show tire strategy analysis."""
    st.subheader("Tire Strategy Analysis")
    
    # Add filters in sidebar
    st.sidebar.subheader("Tire Strategy Filters")
    
    # Get unique drivers
    drivers = laps_df['driver_name'].unique().tolist()
    
    # Allow user to select drivers
    selected_drivers = st.sidebar.multiselect("Select Drivers (Tires)", drivers, default=drivers[:3] if len(drivers) > 3 else drivers)
    
    # Filter data
    filtered_df = laps_df[laps_df['driver_name'].isin(selected_drivers)]
    filtered_df = filtered_df[~(filtered_df['deleted'] == 1)]
    
    if filtered_df.empty:
        st.warning("No tire data available with the current filters.")
        return
    
    # Display options
    view_type = st.radio("View Type", ["Tire Degradation", "Pit Stop Strategy", "Stint Comparison"])
    
    if view_type == "Tire Degradation":
        # Create tire degradation visualization
        fig = go.Figure()
        
        # Create a color map for tire compounds
        compound_colors = {
            'S': 'red',
            'M': 'yellow',
            'H': 'white',
            'I': 'green',
            'W': 'blue'
        }
        
        # Add a scatter point for each lap
        for driver in selected_drivers:
            driver_data = filtered_df[filtered_df['driver_name'] == driver]
            if not driver_data.empty and not driver_data['lap_time_sec'].isna().all():
                team_color = driver_data['team_color'].iloc[0]
                
                # Group by stint
                stints = driver_data['stint'].unique()
                stints = [s for s in stints if pd.notna(s)]
                
                for stint in stints:
                    stint_data = driver_data[driver_data['stint'] == stint]
                    if not stint_data.empty:
                        # Get compound for this stint
                        compound = stint_data['compound'].iloc[0] if pd.notna(stint_data['compound'].iloc[0]) else 'Unknown'
                        
                        # Create a name for the legend that includes driver and compound
                        name = f"{driver} - {compound}"
                        
                        # Choose marker color based on compound
                        marker_color = compound_colors.get(compound, f"#{team_color}" if not team_color.startswith('#') else team_color)
                        
                        fig.add_trace(go.Scatter(
                            x=stint_data['tyre_life'],
                            y=stint_data['lap_time_sec'],
                            mode='lines+markers',
                            name=name,
                            line=dict(color=marker_color, width=2),
                            marker=dict(
                                size=8,
                                color=marker_color,
                                symbol='circle'
                            ),
                            hovertemplate=(
                                f"Driver: {driver}<br>" +
                                "Tire Life: %{x} laps<br>" +
                                "Lap Time: %{y:.3f}s<br>" +
                                f"Compound: {compound}<br>" +
                                "Lap: %{customdata[0]}"
                            ),
                            customdata=np.column_stack((stint_data['lap_number'],))
                        ))
        
        # Update layout
        fig.update_layout(
            title="Tire Degradation Analysis",
            xaxis_title="Tire Life (laps)",
            yaxis_title="Lap Time (seconds)",
            yaxis=dict(autorange="reversed"),  # Lower times at the top
            hovermode="closest",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
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
        
        # Show trendlines for degradation
        st.subheader("Tire Degradation Trendlines")
        
        # Calculate linear degradation for each stint
        degradation_data = []
        
        for driver in selected_drivers:
            driver_data = filtered_df[filtered_df['driver_name'] == driver]
            if not driver_data.empty:
                # Group by stint
                stints = driver_data['stint'].unique()
                stints = [s for s in stints if pd.notna(s)]
                
                for stint in stints:
                    stint_data = driver_data[driver_data['stint'] == stint]
                    if len(stint_data) > 5:  # Need enough points for a meaningful trendline
                        compound = stint_data['compound'].iloc[0] if pd.notna(stint_data['compound'].iloc[0]) else 'Unknown'
                        
                        # Calculate linear regression for degradation
                        x = stint_data['tyre_life'].values
                        y = stint_data['lap_time_sec'].values
                        
                        # Remove NaN values
                        valid_indices = ~np.isnan(x) & ~np.isnan(y)
                        x = x[valid_indices]
                        y = y[valid_indices]
                        
                        if len(x) > 1:  # Need at least 2 points for regression
                            # Calculate linear regression
                            try:
                                coeffs = np.polyfit(x, y, 1)
                                slope = coeffs[0]  # Seconds per lap degradation
                                
                                degradation_data.append({
                                    'Driver': driver,
                                    'Stint': int(stint),
                                    'Compound': compound,
                                    'Laps': len(stint_data),
                                    'Degradation (s/lap)': f"{slope:.4f}",
                                    'Degradation Value': slope,
                                    '10-Lap Effect (s)': f"{slope * 10:.2f}"
                                })
                            except:
                                pass  # Skip if regression fails
        
        if degradation_data:
            deg_df = pd.DataFrame(degradation_data)
            
            # Sort by degradation value (highest first, which is most negative)
            deg_df = deg_df.sort_values('Degradation Value', ascending=True)
            
            # Display dataframe
            st.dataframe(
                deg_df.drop('Degradation Value', axis=1),
                use_container_width=True,
                hide_index=True
            )
            
            # Create bar chart
            fig = go.Figure()
            
            for _, row in deg_df.iterrows():
                compound = row['Compound']
                marker_color = compound_colors.get(compound, 'gray')
                
                fig.add_trace(go.Bar(
                    x=[f"{row['Driver']} (Stint {row['Stint']})"],
                    y=[row['Degradation Value']],
                    name=f"{row['Driver']} - {compound}",
                    marker_color=marker_color,
                    text=f"{row['Degradation Value']:.4f}",
                    hovertemplate=(
                        "Driver: %{x}<br>" +
                        "Degradation: %{y:.4f} s/lap<br>" +
                        f"Compound: {compound}<br>" +
                        f"Stint Length: {row['Laps']} laps"
                    )
                ))
            
            fig.update_layout(
                title="Tire Degradation Comparison",
                xaxis_title="Driver and Stint",
                yaxis_title="Degradation Rate (s/lap)",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("""
            ### Understanding Tire Degradation
            - **Negative values** indicate increasing lap times (normal degradation)
            - **Larger negative values** indicate faster degradation
            - The **10-Lap Effect** column shows how much time would be lost over 10 laps at current degradation rates
            """)
        else:
            st.info("Not enough data to calculate meaningful degradation trends.")
    
    elif view_type == "Pit Stop Strategy":
        # Analyze pit stop strategy
        st.subheader("Pit Stop Analysis")
        
        # Identify pit stops (changes in stint)
        pit_stops = []
        
        for driver in selected_drivers:
            driver_data = filtered_df[filtered_df['driver_name'] == driver]
            if not driver_data.empty:
                # Group by stint
                stints = driver_data['stint'].unique()
                stints = [s for s in stints if pd.notna(s)]
                
                # Get compounds for each stint
                for i, stint in enumerate(stints):
                    if i == 0:  # First stint, no pit stop before it
                        continue
                    
                    # Get data for this stint
                    stint_data = driver_data[driver_data['stint'] == stint]
                    if stint_data.empty:
                        continue
                    
                    # Find the first lap of this stint
                    first_lap = stint_data['lap_number'].min()
                    
                    # Find the compound for this stint
                    new_compound = stint_data['compound'].iloc[0] if pd.notna(stint_data['compound'].iloc[0]) else 'Unknown'
                    
                    # Find the compound for the previous stint
                    prev_stint_data = driver_data[driver_data['stint'] == stints[i-1]]
                    old_compound = prev_stint_data['compound'].iloc[0] if not prev_stint_data.empty and pd.notna(prev_stint_data['compound'].iloc[0]) else 'Unknown'
                    
                    # Calculate the lap of pit entry (should be the lap before first_lap)
                    pit_lap = first_lap - 1
                    
                    pit_stops.append({
                        'Driver': driver,
                        'Pit Stop': i,
                        'Lap': int(pit_lap),
                        'Old Compound': old_compound,
                        'New Compound': new_compound,
                        'Stint Length': len(prev_stint_data)
                    })
        
        if pit_stops:
            # Create pit stop table
            pit_df = pd.DataFrame(pit_stops)
            
            # Sort by lap
            pit_df = pit_df.sort_values('Lap')
            
            # Display dataframe
            st.dataframe(
                pit_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Create pit stop timeline
            fig = go.Figure()
            
            for driver in selected_drivers:
                driver_pit_stops = pit_df[pit_df['Driver'] == driver]
                if not driver_pit_stops.empty:
                    driver_info = filtered_df[filtered_df['driver_name'] == driver].iloc[0]
                    team_color = driver_info['team_color']
                    
                    fig.add_trace(go.Scatter(
                        x=driver_pit_stops['Lap'],
                        y=[driver] * len(driver_pit_stops),
                        mode='markers',
                        name=driver,
                        marker=dict(
                            color=f"#{team_color}" if not team_color.startswith('#') else team_color,
                            size=15,
                            symbol='square'
                        ),
                        hovertemplate=(
                            "Driver: %{y}<br>" +
                            "Pit Stop: Lap %{x}<br>" +
                            "Changed from %{customdata[0]} to %{customdata[1]}"
                        ),
                        customdata=np.column_stack((
                            driver_pit_stops['Old Compound'], 
                            driver_pit_stops['New Compound']
                        ))
                    ))
            
            # Update layout
            fig.update_layout(
                title="Pit Stop Timeline",
                xaxis_title="Lap Number",
                yaxis_title="Driver",
                hovermode="closest",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Create a chart of pit window
            pit_window = pd.DataFrame({
                'Lap': range(1, int(filtered_df['lap_number'].max()) + 1)
            })
            
            # Count pit stops by lap
            pit_counts = pit_df['Lap'].value_counts().reset_index()
            pit_counts.columns = ['Lap', 'Count']
            
            # Merge with pit window
            pit_window = pit_window.merge(pit_counts, on='Lap', how='left')
            pit_window['Count'] = pit_window['Count'].fillna(0)
            
            # Create bar chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=pit_window['Lap'],
                y=pit_window['Count'],
                marker_color='orangered',
                name='Pit Stops',
                hovertemplate=(
                    "Lap: %{x}<br>" +
                    "Pit Stops: %{y}"
                )
            ))
            
            fig.update_layout(
                title="Pit Stop Windows",
                xaxis_title="Lap Number",
                yaxis_title="Number of Pit Stops",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No pit stops detected in the data.")
    
    elif view_type == "Stint Comparison":
        # Show stint summary
        st.subheader("Stint Summary")
        
        # Calculate stint information
        stint_summary = []
        for driver in selected_drivers:
            driver_data = filtered_df[filtered_df['driver_name'] == driver]
            if not driver_data.empty:
                # Group by stint
                stints = driver_data['stint'].unique()
                stints = [s for s in stints if pd.notna(s)]
                
                for stint in stints:
                    stint_data = driver_data[driver_data['stint'] == stint]
                    if len(stint_data) > 1:  # Only include stints with at least 2 laps
                        compound = stint_data['compound'].iloc[0] if pd.notna(stint_data['compound'].iloc[0]) else 'Unknown'
                        
                        # Calculate stint statistics
                        stint_length = len(stint_data)
                        lap_times = stint_data['lap_time_sec'].dropna()
                        if len(lap_times) > 0:
                            min_lap_time = lap_times.min()
                            max_lap_time = lap_times.max()
                            avg_lap_time = lap_times.mean()
                            degradation = (max_lap_time - min_lap_time) / stint_length if stint_length > 0 else 0
                            
                            stint_summary.append({
                                'Driver': driver,
                                'Stint': int(stint),
                                'Compound': compound,
                                'Laps': stint_length,
                                'Min Time': format_seconds_to_time(min_lap_time),
                                'Avg Time': format_seconds_to_time(avg_lap_time),
                                'Deg/Lap': f"{degradation:.3f}s",
                                'Lap Range': f"{int(stint_data['lap_number'].min())}-{int(stint_data['lap_number'].max())}"
                            })
        
        if stint_summary:
            stint_df = pd.DataFrame(stint_summary)
            st.dataframe(stint_df, use_container_width=True, hide_index=True)
            
            # Create a Gantt-like chart to show stint structure
            fig = go.Figure()
            
            # Create a color map for compounds
            compound_colors = {
                'S': 'red',
                'M': 'gold',
                'H': 'white',
                'I': 'green',
                'W': 'blue',
                'Unknown': 'gray'
            }
            
            # Add a bar for each stint
            for _, stint in stint_df.iterrows():
                driver_stint = f"{stint['Driver']} (Stint {stint['Stint']})"
                
                # Get the lap range
                lap_range = stint['Lap Range'].split('-')
                start_lap = int(lap_range[0])
                end_lap = int(lap_range[1])
                
                # Get compound color
                color = compound_colors.get(stint['Compound'], 'gray')
                
                fig.add_trace(go.Bar(
                    x=[end_lap - start_lap + 1],  # Width = number of laps
                    y=[driver_stint],
                    orientation='h',
                    marker_color=color,
                    name=f"{stint['Driver']} - {stint['Compound']}",
                    hovertemplate=(
                        "Driver: %{y}<br>" +
                        "Compound: " + stint['Compound'] + "<br>" +
                        "Stint Length: %{x} laps<br>" +
                        "Lap Range: " + stint['Lap Range'] + "<br>" +
                        "Avg Time: " + stint['Avg Time']
                    ),
                    customdata=np.column_stack((stint['Compound'],))
                ))
                
                # Add a text annotation for the compound
                fig.add_annotation(
                    x=start_lap + (end_lap - start_lap) / 2,
                    y=driver_stint,
                    text=stint['Compound'],
                    showarrow=False,
                    font=dict(
                        color='black' if stint['Compound'] in ['M', 'I'] else 'white',
                        size=12
                    )
                )
            
            # Update layout
            fig.update_layout(
                title="Race Stint Structure",
                xaxis_title="Stint Length (laps)",
                yaxis_title="Driver & Stint",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=False,
                height=500,
                barmode='relative'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add compound legend
            st.markdown("""
            ### Compound Colors
            - <span style="color:red">■</span> **Soft (S)**
            - <span style="color:gold">■</span> **Medium (M)**
            - <span style="color:white">■</span> **Hard (H)**
            - <span style="color:green">■</span> **Intermediate (I)**
            - <span style="color:blue">■</span> **Wet (W)**
            """, unsafe_allow_html=True)
        else:
            st.info("No valid stint data to display.")


def show_driver_comparison(laps_df):
    """Show driver comparison visualization."""
    st.subheader("Driver Comparison")
    
    # Get unique drivers
    drivers = laps_df['driver_name'].unique().tolist()
    
    # Create two columns for driver selection
    col1, col2 = st.columns(2)
    
    with col1:
        driver1 = st.selectbox("Select Driver 1", drivers, index=0 if len(drivers) > 0 else 0)
    
    with col2:
        remaining_drivers = [d for d in drivers if d != driver1]
        driver2 = st.selectbox("Select Driver 2", remaining_drivers, index=0 if len(remaining_drivers) > 0 else 0)
    
    # Filter data for the selected drivers
    driver1_data = laps_df[laps_df['driver_name'] == driver1].copy()
    driver2_data = laps_df[laps_df['driver_name'] == driver2].copy()
    
    # Filter out deleted laps
    driver1_data = driver1_data[~(driver1_data['deleted'] == 1)]
    driver2_data = driver2_data[~(driver2_data['deleted'] == 1)]
    
    if driver1_data.empty or driver2_data.empty:
        st.warning("Insufficient data for comparison.")
        return
    
    # Calculate lap time differences
    st.subheader("Lap Time Comparison")
    
    # Create a dataframe for comparison
    common_laps = set(driver1_data['lap_number']) & set(driver2_data['lap_number'])
    comparison_data = []
    
    for lap in common_laps:
        lap1 = driver1_data[driver1_data['lap_number'] == lap].iloc[0]
        lap2 = driver2_data[driver2_data['lap_number'] == lap].iloc[0]
        
        if pd.notna(lap1['lap_time_sec']) and pd.notna(lap2['lap_time_sec']):
            time_diff = lap1['lap_time_sec'] - lap2['lap_time_sec']
            
            comparison_data.append({
                'Lap': int(lap),
                f"{driver1} Time": format_seconds_to_time(lap1['lap_time_sec']),
                f"{driver2} Time": format_seconds_to_time(lap2['lap_time_sec']),
                'Difference': f"{time_diff:.3f}s" if time_diff >= 0 else f"{time_diff:.3f}s",
                'Delta': time_diff,
                f"{driver1} Compound": lap1['compound'],
                f"{driver2} Compound": lap2['compound']
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        
        # Create a visualization of the lap time delta
        fig = go.Figure()
        
        # Add a zero line
        fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="grey")
        
        # Add the delta trace
        driver1_color = driver1_data['team_color'].iloc[0]
        driver2_color = driver2_data['team_color'].iloc[0]
        
        fig.add_trace(go.Bar(
            x=comparison_df['Lap'],
            y=comparison_df['Delta'],
            name=f"{driver1} vs {driver2} Delta",
            marker_color=[f"#{driver1_color}" if d > 0 else f"#{driver2_color}" for d in comparison_df['Delta']],
            hovertemplate=(
                "Lap: %{x}<br>" +
                "Delta: %{y:.3f}s<br>" +
                f"{driver1} Time: %{{customdata[0]}}<br>" +
                f"{driver2} Time: %{{customdata[1]}}<br>" +
                f"{driver1} Tire: %{{customdata[2]}}<br>" +
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
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show the comparison table
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        
        # Calculate overall statistics
        positive_deltas = comparison_df[comparison_df['Delta'] > 0]['Delta']
        negative_deltas = comparison_df[comparison_df['Delta'] < 0]['Delta']
        
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
            f"Average Delta", 
            f"{comparison_df['Delta'].mean():.3f}s"
        )
        
        col4.metric(
            f"Largest Delta", 
            f"{comparison_df['Delta'].abs().max():.3f}s"
        )
        
        # Add a race position visualization
        st.subheader("Race Position Comparison")
        
        # Get position data (if available)
        if 'position' in driver1_data.columns and 'position' in driver2_data.columns:
            # Create position dataframe
            position_data = []
            
            for lap in sorted(common_laps):
                lap1 = driver1_data[driver1_data['lap_number'] == lap].iloc[0]
                lap2 = driver2_data[driver2_data['lap_number'] == lap].iloc[0]
                
                if pd.notna(lap1['position']) and pd.notna(lap2['position']):
                    position_data.append({
                        'Lap': int(lap),
                        f"{driver1} Position": int(lap1['position']),
                        f"{driver2} Position": int(lap2['position']),
                        'Position Delta': int(lap2['position']) - int(lap1['position'])
                    })
            
            if position_data:
                position_df = pd.DataFrame(position_data)
                
                # Create a line chart of positions
                fig = go.Figure()
                
                # Add position traces
                fig.add_trace(go.Scatter(
                    x=position_df['Lap'],
                    y=position_df[f"{driver1} Position"],
                    mode='lines+markers',
                    name=driver1,
                    line=dict(color=f"#{driver1_color}" if not driver1_color.startswith('#') else driver1_color, width=2),
                    marker=dict(size=8)
                ))
                
                fig.add_trace(go.Scatter(
                    x=position_df['Lap'],
                    y=position_df[f"{driver2} Position"],
                    mode='lines+markers',
                    name=driver2,
                    line=dict(color=f"#{driver2_color}" if not driver2_color.startswith('#') else driver2_color, width=2),
                    marker=dict(size=8)
                ))
                
                # Update layout
                fig.update_layout(
                    title=f"Race Position Comparison",
                    xaxis_title="Lap Number",
                    yaxis_title="Position",
                    yaxis=dict(
                        autorange="reversed",  # Position 1 at the top
                        dtick=1  # Show all position numbers
                    ),
                    hovermode="closest",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No common laps available for comparison.")


def show_sector_analysis(laps_df):
    """Show sector time analysis visualization."""
    st.subheader("Sector Analysis")
    
    # Add filters in sidebar
    st.sidebar.subheader("Sector Analysis Filters")
    
    # Get unique drivers
    drivers = laps_df['driver_name'].unique().tolist()
    
    # Allow user to select drivers
    selected_drivers = st.sidebar.multiselect("Select Drivers (Sectors)", drivers, default=drivers[:3] if len(drivers) > 3 else drivers)
    
    # Select which sector to analyze
    sector = st.selectbox("Select Sector", ["All Sectors", "Sector 1", "Sector 2", "Sector 3"])
    
    # Map sector selection to dataframe column
    sector_map = {
        "Sector 1": "sector1_sec",
        "Sector 2": "sector2_sec", 
        "Sector 3": "sector3_sec"
    }
    
    # Filter data
    filtered_df = laps_df[laps_df['driver_name'].isin(selected_drivers)]
    filtered_df = filtered_df[~(filtered_df['deleted'] == 1)]
    
    if filtered_df.empty:
        st.warning("No sector data available with the current filters.")
        return
    
    if sector == "All Sectors":
        # Show breakdown of lap time by sector
        st.subheader("Lap Time Breakdown by Sector")
        
        # Create stacked bar chart of best sector times
        best_sectors = {}
        
        for driver in selected_drivers:
            driver_data = filtered_df[filtered_df['driver_name'] == driver]
            
            best_s1 = driver_data['sector1_sec'].min() if not driver_data['sector1_sec'].isna().all() else np.nan
            best_s2 = driver_data['sector2_sec'].min() if not driver_data['sector2_sec'].isna().all() else np.nan
            best_s3 = driver_data['sector3_sec'].min() if not driver_data['sector3_sec'].isna().all() else np.nan
            
            best_sectors[driver] = {
                'Sector 1': best_s1,
                'Sector 2': best_s2,
                'Sector 3': best_s3,
                'Team Color': driver_data['team_color'].iloc[0]
            }
        
        # Create a dataframe for visualization
        sector_bars = []
        
        for driver, sectors in best_sectors.items():
            sector_bars.append({
                'Driver': driver,
                'Sector': 'Sector 1',
                'Time': sectors['Sector 1'],
                'Team Color': sectors['Team Color']
            })
            sector_bars.append({
                'Driver': driver,
                'Sector': 'Sector 2',
                'Time': sectors['Sector 2'],
                'Team Color': sectors['Team Color']
            })
            sector_bars.append({
                'Driver': driver,
                'Sector': 'Sector 3',
                'Time': sectors['Sector 3'],
                'Team Color': sectors['Team Color']
            })
        
        sector_df = pd.DataFrame(sector_bars)
        
        # Create stacked bar chart
        fig = go.Figure()
        
        for sector_name in ['Sector 1', 'Sector 2', 'Sector 3']:
            sector_data = sector_df[sector_df['Sector'] == sector_name]
            
            fig.add_trace(go.Bar(
                x=sector_data['Driver'],
                y=sector_data['Time'],
                name=sector_name,
                hovertemplate=(
                    "Driver: %{x}<br>" +
                    f"{sector_name}: %{{y:.3f}}s"
                )
            ))
        
        # Update layout
        fig.update_layout(
            title="Best Sector Times Comparison",
            xaxis_title="Driver",
            yaxis_title="Time (seconds)",
            barmode='stack',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show ideal lap calculation
        st.subheader("Ideal Lap Calculation")
        
        ideal_laps = []
        for driver in selected_drivers:
            driver_data = filtered_df[filtered_df['driver_name'] == driver]
            
            best_s1 = driver_data['sector1_sec'].min() if not driver_data['sector1_sec'].isna().all() else np.nan
            best_s2 = driver_data['sector2_sec'].min() if not driver_data['sector2_sec'].isna().all() else np.nan
            best_s3 = driver_data['sector3_sec'].min() if not driver_data['sector3_sec'].isna().all() else np.nan
            
            if not (np.isnan(best_s1) or np.isnan(best_s2) or np.isnan(best_s3)):
                ideal_time = best_s1 + best_s2 + best_s3
                
                # Find actual best lap
                best_lap_time = driver_data['lap_time_sec'].min() if not driver_data['lap_time_sec'].isna().all() else np.nan
                
                if not np.isnan(best_lap_time):
                    improvement = best_lap_time - ideal_time
                    
                    ideal_laps.append({
                        'Driver': driver,
                        'Best Sector 1': format_seconds_to_time(best_s1),
                        'Best Sector 2': format_seconds_to_time(best_s2),
                        'Best Sector 3': format_seconds_to_time(best_s3),
                        'Ideal Lap': format_seconds_to_time(ideal_time),
                        'Actual Best': format_seconds_to_time(best_lap_time),
                        'Potential Gain': f"+{improvement:.3f}s"
                    })
        
        if ideal_laps:
            ideal_df = pd.DataFrame(ideal_laps)
            st.dataframe(ideal_df, use_container_width=True, hide_index=True)
    else:
        # Single sector analysis
        sector_col = sector_map[sector]
        
        # Filter for valid sector data
        sector_df = filtered_df[pd.notna(filtered_df[sector_col])]
        
        if sector_df.empty:
            st.warning(f"No valid {sector} data available with the current filters.")
            return
        
        # Create sector time visualization
        fig = go.Figure()
        
        # Add a line for each driver
        for driver in selected_drivers:
            driver_data = sector_df[sector_df['driver_name'] == driver]
            if not driver_data.empty and not driver_data[sector_col].isna().all():
                team_color = driver_data['team_color'].iloc[0]
                
                fig.add_trace(go.Scatter(
                    x=driver_data['lap_number'],
                    y=driver_data[sector_col],
                    mode='lines+markers',
                    name=driver,
                    line=dict(color=f"#{team_color}" if not team_color.startswith('#') else team_color, width=2),
                    marker=dict(
                        size=8,
                        color=f"#{team_color}" if not team_color.startswith('#') else team_color,
                        symbol='circle'
                    ),
                    hovertemplate=(
                        f"Driver: {driver}<br>" +
                        "Lap: %{x}<br>" +
                        f"{sector} Time: %{{y:.3f}}s<br>" +
                        "Compound: %{customdata[0]}"
                    ),
                    customdata=np.column_stack((driver_data['compound'],))
                ))
        
        # Update layout
        fig.update_layout(
            title=f"{sector} Times",
            xaxis_title="Lap Number",
            yaxis_title=f"{sector} Time (seconds)",
            yaxis=dict(autorange="reversed"),  # Lower times at the top
            hovermode="closest",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
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
            driver_data = sector_df[sector_df['driver_name'] == driver]
            if not driver_data.empty and not driver_data[sector_col].isna().all():
                best_sector = driver_data.loc[driver_data[sector_col].idxmin()]
                best_sectors.append({
                    'Driver': best_sector['driver_name'],
                    'Lap': int(best_sector['lap_number']),
                    f'{sector} Time': f"{best_sector[sector_col]:.3f}s",
                    'Time_Sec': best_sector[sector_col],
                    'Compound': best_sector['compound'],
                    'Team': best_sector['team_name']
                })
        
        if best_sectors:
            # Sort by sector time
            best_sectors_df = pd.DataFrame(best_sectors).sort_values('Time_Sec')
            
            # Calculate delta to fastest
            if not best_sectors_df.empty:
                fastest_time = best_sectors_df['Time_Sec'].min()
                best_sectors_df['Delta'] = best_sectors_df['Time_Sec'].apply(
                    lambda x: f"+{(x - fastest_time):.3f}s" if x > fastest_time else "Leader"
                )
            
            # Display dataframe without the Time_Sec column
            st.dataframe(
                best_sectors_df.drop('Time_Sec', axis=1),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(f"No valid {sector} times to display.")


def show_telemetry_analysis(session_id, db):
    """Show telemetry data analysis for selected driver and lap."""
    st.subheader("Telemetry Analysis")
    
    # Get drivers for this session
    drivers_df = db.execute_query(
        """
        SELECT DISTINCT d.id, d.full_name as driver_name, d.abbreviation, 
            t.name as team_name, t.team_color
        FROM telemetry tel
        JOIN drivers d ON tel.driver_id = d.id
        JOIN teams t ON d.team_id = t.id
        WHERE tel.session_id = ?
        ORDER BY t.name, d.full_name
        """,
        params=(session_id,)
    )
    
    if drivers_df.empty:
        st.warning("No telemetry data available for this session.")
        return
    
    # Allow user to select a driver
    driver_options = drivers_df['driver_name'].tolist()
    selected_driver = st.selectbox("Select Driver", driver_options)
    
    # Get the driver ID
    driver_id = int(drivers_df[drivers_df['driver_name'] == selected_driver]['id'].iloc[0])
    driver_abbr = drivers_df[drivers_df['driver_name'] == selected_driver]['abbreviation'].iloc[0]
    driver_team_color = drivers_df[drivers_df['driver_name'] == selected_driver]['team_color'].iloc[0]
    
    # Get laps for this driver in this session
    laps_df = db.execute_query(
        """
        SELECT DISTINCT lap_number
        FROM telemetry
        WHERE session_id = ? AND driver_id = ?
        ORDER BY lap_number
        """,
        params=(session_id, driver_id)
    )
    
    if laps_df.empty:
        st.warning(f"No lap telemetry data for {selected_driver}. Please check if telemetry is available in the database.")
        st.write("Available laps in database:", db.execute_query("SELECT DISTINCT lap_number FROM telemetry WHERE session_id = ?", (session_id,)))
        return
    
    # Allow user to select a lap
    lap_options = laps_df['lap_number'].tolist()
    selected_lap = st.selectbox("Select Lap", lap_options)
    
    # Add comparison option
    st.subheader("Driver Comparison")
    compare_enabled = st.checkbox("Compare with another driver")
    
    comparison_driver_id = None
    if compare_enabled:
        # Get other drivers
        other_drivers = drivers_df[drivers_df['driver_name'] != selected_driver]
        if not other_drivers.empty:
            comparison_driver = st.selectbox("Compare with", other_drivers['driver_name'].tolist())
            comparison_driver_id = other_drivers[other_drivers['driver_name'] == comparison_driver]['id'].iloc[0]
    
    # Get telemetry data
    telemetry_df = db.execute_query(
        """
        SELECT time, session_time, speed, rpm, gear, throttle, brake, drs,
            x, y, z, d.full_name as driver_name, t.team_color
        FROM telemetry tel
        JOIN drivers d ON tel.driver_id = d.id
        JOIN teams t ON d.team_id = t.id
        WHERE tel.session_id = ? AND tel.driver_id = ? AND tel.lap_number = ?
        ORDER BY tel.time
        """,
        params=(session_id, driver_id, selected_lap)
    )
    
    # Get comparison telemetry if enabled
    comparison_df = None
    if compare_enabled and comparison_driver_id:
        comparison_df = db.execute_query(
            """
            SELECT time, session_time, speed, rpm, gear, throttle, brake, drs,
                x, y, z, d.full_name as driver_name, t.team_color
            FROM telemetry tel
            JOIN drivers d ON tel.driver_id = d.id
            JOIN teams t ON d.team_id = t.id
            WHERE tel.session_id = ? AND tel.driver_id = ? AND tel.lap_number = ?
            ORDER BY tel.time
            """,
            params=(session_id, comparison_driver_id, selected_lap)
        )
    
    if telemetry_df.empty:
        st.warning(f"No telemetry data available for {selected_driver} in lap {selected_lap}.")
        st.write("Available telemetry in database:", db.execute_query("SELECT * FROM telemetry WHERE session_id = ? AND driver_id = ?", (session_id, driver_id)))
        return
    
    # Create tabs for different telemetry views
    tel_tab1, tel_tab2, tel_tab3, tel_tab4 = st.tabs(["Speed & Throttle", "Braking & DRS", "Gears", "Track Map"])
    
    with tel_tab1:
        # Show speed telemetry
        show_telemetry_chart(telemetry_df, 'speed', "Speed Telemetry", comparison_df)
        
        # Show throttle telemetry
        show_telemetry_chart(telemetry_df, 'throttle', "Throttle Telemetry", comparison_df)
        
        # Show speed vs distance visualization if compared
        if comparison_df is not None and not comparison_df.empty:
            st.subheader("Speed vs Distance Comparison")
            
            # Calculate distance based on position
            if 'x' in telemetry_df.columns and 'y' in telemetry_df.columns:
                # Calculate distance for main driver
                telemetry_df['distance'] = calculate_distance(telemetry_df)
                
                # Calculate distance for comparison driver
                comparison_df['distance'] = calculate_distance(comparison_df)
                
                # Create comparison chart
                fig = go.Figure()
                
                # Add speed vs distance trace for main driver
                fig.add_trace(go.Scatter(
                    x=telemetry_df['distance'],
                    y=telemetry_df['speed'],
                    mode='lines',
                    name=selected_driver,
                    line=dict(color=f"#{driver_team_color}" if not driver_team_color.startswith('#') else driver_team_color, width=3)
                ))
                
                # Add speed vs distance trace for comparison driver
                comparison_driver_color = comparison_df['team_color'].iloc[0]
                fig.add_trace(go.Scatter(
                    x=comparison_df['distance'],
                    y=comparison_df['speed'],
                    mode='lines',
                    name=comparison_df['driver_name'].iloc[0],
                    line=dict(color=f"#{comparison_driver_color}" if not comparison_driver_color.startswith('#') else comparison_driver_color, width=3, dash='dash')
                ))
                
                # Update layout
                fig.update_layout(
                    title="Speed vs Distance Comparison",
                    xaxis_title="Distance (m)",
                    yaxis_title="Speed (km/h)",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    with tel_tab2:
        # Show brake telemetry
        show_telemetry_chart(telemetry_df, 'brake', "Brake Telemetry", comparison_df)
        
        # Show DRS telemetry
        show_telemetry_chart(telemetry_df, 'drs', "DRS Telemetry", comparison_df)
        
        # Find DRS activation points
        drs_activations = []
        for i in range(1, len(telemetry_df)):
            if telemetry_df['drs'].iloc[i] > telemetry_df['drs'].iloc[i-1]:
                drs_activations.append(i)
        
        # Show DRS activation points on a speed chart
        fig = go.Figure()
        
        # Add the speed trace
        fig.add_trace(go.Scatter(
            x=telemetry_df['session_time'],
            y=telemetry_df['speed'],
            mode='lines',
            name='Speed',
            line=dict(color=f"#{driver_team_color}" if not driver_team_color.startswith('#') else driver_team_color, width=3)
        ))
        
        # Add DRS activation markers
        for idx in drs_activations:
            if idx < len(telemetry_df):
                fig.add_trace(go.Scatter(
                    x=[telemetry_df['session_time'].iloc[idx]],
                    y=[telemetry_df['speed'].iloc[idx]],
                    mode='markers',
                    marker=dict(
                        size=10,
                        color='green',
                        symbol='star'
                    ),
                    name='DRS Activation'
                ))
        
        # Update layout
        fig.update_layout(
            title="Speed and DRS Activation Points",
            xaxis_title="Time",
            yaxis_title="Speed (km/h)",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tel_tab3:
        # Show gear shifts telemetry
        show_telemetry_chart(telemetry_df, 'gear', "Gear Shifts", comparison_df)
        
        # Show RPM telemetry
        show_telemetry_chart(telemetry_df, 'rpm', "Engine RPM", comparison_df)
        
        # Count gear shifts
        gear_shifts = 0
        for i in range(1, len(telemetry_df)):
            if telemetry_df['gear'].iloc[i] != telemetry_df['gear'].iloc[i-1]:
                gear_shifts += 1
        
        # Display gear statistics
        st.subheader("Gear Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        col1.metric("Total Gear Shifts", gear_shifts)
        
        # Calculate time spent in each gear
        if 'gear' in telemetry_df.columns and 'time' in telemetry_df.columns:
            gear_times = {}
            
            for i in range(1, len(telemetry_df)):
                gear = telemetry_df['gear'].iloc[i]
                if pd.notna(gear):
                    gear = int(gear)
                    if gear not in gear_times:
                        gear_times[gear] = 0
                    
                    # Add time difference between points
                    gear_times[gear] += 1  # Simplified as 1 unit per datapoint
            
            # Calculate percentage of time in each gear
            total_time = sum(gear_times.values())
            
            if total_time > 0:
                for gear, time in gear_times.items():
                    gear_times[gear] = (time / total_time) * 100
                
                # Find most used gear
                most_used_gear = max(gear_times, key=gear_times.get)
                col2.metric("Most Used Gear", most_used_gear)
                col3.metric("% in Most Used Gear", f"{gear_times[most_used_gear]:.1f}%")
                
                # Create gear distribution chart
                gear_data = pd.DataFrame({
                    'Gear': list(gear_times.keys()),
                    'Percentage': list(gear_times.values())
                })
                
                fig = px.bar(
                    gear_data,
                    x='Gear',
                    y='Percentage',
                    title='Time Spent in Each Gear',
                    color='Gear',
                    color_continuous_scale=px.colors.sequential.Plasma
                )
                
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    with tel_tab4:
        # Show track map if x, y coordinates are available
        if 'x' in telemetry_df.columns and 'y' in telemetry_df.columns:
            # Find braking points (where brake > 0)
            braking_points = []
            for i in range(len(telemetry_df)):
                if pd.notna(telemetry_df['brake'].iloc[i]) and telemetry_df['brake'].iloc[i] > 0:
                    braking_points.append((i, 'red', 'Braking Point'))
            
            # Show track map with highlighted points
            show_track_map(telemetry_df, braking_points, comparison_df)
            
            # Add description of the track map
            st.info("""
            **Track Map Legend:**
            - **Blue Line**: The racing line taken by the main driver
            - **Red Points**: Braking points
            - **Dashed Line**: Comparison driver (if selected)
            
            This visualization shows the driver's path around the track with key points highlighted.
            """)
        else:
            st.warning("Track map data (x, y coordinates) not available for this lap.")
        
        # Additional track statistics
        st.subheader("Lap Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        # Calculate maximum speed
        max_speed = telemetry_df['speed'].max() if 'speed' in telemetry_df.columns else None
        if max_speed is not None:
            col1.metric("Maximum Speed", f"{max_speed:.1f} km/h")
        
        # Calculate average speed
        avg_speed = telemetry_df['speed'].mean() if 'speed' in telemetry_df.columns else None
        if avg_speed is not None:
            col2.metric("Average Speed", f"{avg_speed:.1f} km/h")
        
        # Count braking points
        braking_count = sum(1 for b in telemetry_df['brake'] if pd.notna(b) and b > 0)
        col3.metric("Braking Points", braking_count)


def show_telemetry_chart(telemetry_df, metric='speed', title=None, compare_with=None):
    """
    Display telemetry data chart.
    
    Parameters:
    - telemetry_df: DataFrame containing telemetry data
    - metric: The telemetry metric to visualize (speed, throttle, brake, etc.)
    - title: Optional title for the chart
    - compare_with: Optional second telemetry DataFrame to compare with
    """
    if telemetry_df is None or len(telemetry_df) == 0:
        st.warning("No telemetry data available.")
        return
    
    # Ensure required columns exist
    required_cols = ['time', 'session_time', metric]
    missing_cols = [col for col in required_cols if col not in telemetry_df.columns]
    
    if missing_cols:
        st.warning(f"Missing required columns for telemetry visualization: {', '.join(missing_cols)}")
        return
    
    # Format column names for display
    metric_display = metric.capitalize()
    if metric_display == 'Rpm':
        metric_display = 'RPM'
    
    # Set default title if not provided
    if title is None:
        title = f"{metric_display} Telemetry"
    
    # Create basic figure
    fig = go.Figure()
    
    # Add main telemetry line
    driver_name = telemetry_df.get('driver_name', ['Driver 1'])[0] if 'driver_name' in telemetry_df.columns else 'Driver 1'
    driver_color = telemetry_df.get('team_color', ['#e10600'])[0] if 'team_color' in telemetry_df.columns else '#e10600'
    
    # Format driver_color if needed
    if not driver_color.startswith('#'):
        driver_color = f"#{driver_color}"
    
    # Add the main driver's telemetry
    fig.add_trace(go.Scatter(
        x=telemetry_df['session_time'] if 'session_time' in telemetry_df.columns else telemetry_df['time'],
        y=telemetry_df[metric],
        mode='lines',
        name=driver_name,
        line=dict(color=driver_color, width=3)
    ))
    
    # Add comparison telemetry if provided
    if compare_with is not None and len(compare_with) > 0:
        compare_driver = compare_with.get('driver_name', ['Driver 2'])[0] if 'driver_name' in compare_with.columns else 'Driver 2'
        compare_color = compare_with.get('team_color', ['#0600EF'])[0] if 'team_color' in compare_with.columns else '#0600EF'
        
        # Format compare_color if needed
        if not compare_color.startswith('#'):
            compare_color = f"#{compare_color}"
        
        fig.add_trace(go.Scatter(
            x=compare_with['session_time'] if 'session_time' in compare_with.columns else compare_with['time'],
            y=compare_with[metric],
            mode='lines',
            name=compare_driver,
            line=dict(color=compare_color, width=3, dash='dash')
        ))
    
    # Update layout for better appearance
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title=metric_display,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=400
    )
    
    # Add special y-axis configurations based on metric
    if metric == 'speed':
        fig.update_layout(yaxis=dict(title="Speed (km/h)"))
    elif metric == 'throttle':
        fig.update_layout(yaxis=dict(title="Throttle %", range=[0, 100]))
    elif metric == 'brake':
        fig.update_layout(yaxis=dict(title="Brake", range=[0, 1]))
    elif metric == 'rpm':
        fig.update_layout(yaxis=dict(title="RPM"))
    elif metric == 'gear':
        fig.update_layout(yaxis=dict(title="Gear", dtick=1))
    elif metric == 'drs':
        fig.update_layout(yaxis=dict(title="DRS", range=[-0.5, 1.5], dtick=1))
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True)


def show_track_map(telemetry_df, highlight_points=None, comparison_df=None):
    """
    Display a track map (x, y coordinates) with optional highlight points.
    
    Parameters:
    - telemetry_df: DataFrame containing x and y coordinates
    - highlight_points: Optional list of tuples (index, color, label) to highlight specific points
    - comparison_df: Optional second telemetry DataFrame to compare with
    """
    if telemetry_df is None or len(telemetry_df) == 0:
        return
    
    # Check if x and y coordinates are present
    if 'x' not in telemetry_df.columns or 'y' not in telemetry_df.columns:
        return
    
    # Create a track map visualization
    fig = go.Figure()
    
    # Add the track outline
    driver_color = telemetry_df.get('team_color', ['#e10600'])[0] if 'team_color' in telemetry_df.columns else '#e10600'
    if not driver_color.startswith('#'):
        driver_color = f"#{driver_color}"
    
    fig.add_trace(go.Scatter(
        x=telemetry_df['x'],
        y=telemetry_df['y'],
        mode='lines',
        line=dict(color=driver_color, width=3),
        name='Track'
    ))
    
    # Add comparison line if provided
    if comparison_df is not None and len(comparison_df) > 0 and 'x' in comparison_df.columns and 'y' in comparison_df.columns:
        compare_color = comparison_df.get('team_color', ['#0600EF'])[0] if 'team_color' in comparison_df.columns else '#0600EF'
        if not compare_color.startswith('#'):
            compare_color = f"#{compare_color}"
        
        fig.add_trace(go.Scatter(
            x=comparison_df['x'],
            y=comparison_df['y'],
            mode='lines',
            line=dict(color=compare_color, width=3, dash='dash'),
            name='Comparison'
        ))
    
    # Add highlight points if provided
    if highlight_points:
        for idx, color, label in highlight_points:
            if idx < len(telemetry_df):
                fig.add_trace(go.Scatter(
                    x=[telemetry_df['x'].iloc[idx]],
                    y=[telemetry_df['y'].iloc[idx]],
                    mode='markers',
                    marker=dict(size=10, color=color),
                    name=label
                ))
    
    # Update layout
    fig.update_layout(
        title="Track Map",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(
            showgrid=False,
            showticklabels=False
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            scaleanchor="x",
            scaleratio=1
        ),
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)


def calculate_distance(telemetry_df):
    """Calculate cumulative distance from x,y coordinates."""
    x = telemetry_df['x'].values
    y = telemetry_df['y'].values
    
    # Calculate distances between consecutive points
    dx = np.diff(x)
    dy = np.diff(y)
    distances = np.sqrt(dx**2 + dy**2)
    
    # Prepend a zero (first point has no distance)
    distances = np.insert(distances, 0, 0)
    
    # Calculate cumulative distance
    cum_distance = np.cumsum(distances)
    
    return cum_distance

def show_race_overview(laps_df, session_id, db):
    """Show race overview visualization."""
    st.subheader("Race Overview")
    
    # Get race results
    results_df = db.execute_query(
        """
        SELECT r.position, r.grid_position, r.points, r.status, r.race_time,
            d.full_name as driver_name, d.abbreviation, d.driver_number,
            t.name as team_name, t.team_color
        FROM results r
        JOIN drivers d ON r.driver_id = d.id
        JOIN teams t ON d.team_id = t.id
        WHERE r.session_id = ?
        ORDER BY r.position
        """,
        params=(session_id,)
    )
    
    if results_df.empty:
        st.warning("No race results available.")
        return
    
    # Create formatted table
    show_race_results(results_df)
    
    # Show position changes visualization
    st.subheader("Position Changes: Grid to Finish")
    show_position_changes(results_df)
    
    # Show race summary
    show_race_summary(results_df)
    
    # Show points distribution
    show_points_distribution(results_df)
    
    # Show race position timeline
    st.subheader("Race Position Timeline")
    
    # Organize lap data by position
    race_positions = {}
    
    # Get all drivers with position data
    drivers = laps_df['driver_name'].unique()
    
    # Initialize positions dictionary
    for driver in drivers:
        race_positions[driver] = []
    
    # Get max lap number
    max_lap = laps_df['lap_number'].max()
    
    # Collect position data for each lap
    for lap_num in range(1, int(max_lap) + 1):
        lap_data = laps_df[laps_df['lap_number'] == lap_num]
        
        for driver in drivers:
            driver_lap = lap_data[lap_data['driver_name'] == driver]
            
            if not driver_lap.empty and pd.notna(driver_lap['position'].iloc[0]):
                position = int(driver_lap['position'].iloc[0])
                race_positions[driver].append({'lap': lap_num, 'position': position})
            elif race_positions[driver]:  # Use previous position if available
                prev_position = race_positions[driver][-1]['position']
                race_positions[driver].append({'lap': lap_num, 'position': prev_position})
    
    # Create race timeline visualization
    fig = go.Figure()
    
    # Add a line for each driver
    for driver, positions in race_positions.items():
        if not positions:
            continue
            
        # Get driver color
        driver_data = laps_df[laps_df['driver_name'] == driver]
        if driver_data.empty:
            continue
            
        team_color = driver_data['team_color'].iloc[0]
        
        # Create position data
        laps = [p['lap'] for p in positions]
        pos = [p['position'] for p in positions]
        
        fig.add_trace(go.Scatter(
            x=laps,
            y=pos,
            mode='lines',
            name=driver,
            line=dict(color=f"#{team_color}" if not team_color.startswith('#') else team_color, width=2)
        ))
    
    # Update layout
    fig.update_layout(
        title="Race Position Timeline",
        xaxis_title="Lap Number",
        yaxis_title="Position",
        yaxis=dict(
            autorange="reversed",  # P1 at the top
            dtick=1  # Show every position
        ),
        hovermode="closest",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show battle analyzer
    st.subheader("Driver Battle Analyzer")
    
    # Create dropdown to select drivers to analyze
    driver1, driver2 = st.columns(2)
    
    with driver1:
        selected_driver1 = st.selectbox("Select Driver 1", drivers, key="battle_d1")
    
    with driver2:
        remaining_drivers = [d for d in drivers if d != selected_driver1]
        selected_driver2 = st.selectbox("Select Driver 2", remaining_drivers, key="battle_d2")
    
    # Calculate proximity between the two drivers
    st.caption("Analyzing lap time when drivers were close to each other on track")
    
    # Extract position data for the two drivers
    driver1_positions = race_positions.get(selected_driver1, [])
    driver2_positions = race_positions.get(selected_driver2, [])
    
    # Find laps where drivers were close to each other
    battle_laps = []
    
    for i in range(min(len(driver1_positions), len(driver2_positions))):
        d1_pos = driver1_positions[i]
        d2_pos = driver2_positions[i]
        
        # If they're on the same lap
        if d1_pos['lap'] == d2_pos['lap']:
            # Check if they're within 3 positions of each other
            position_gap = abs(d1_pos['position'] - d2_pos['position'])
            
            if position_gap <= 3:
                battle_laps.append({
                    'Lap': d1_pos['lap'], 
                    f'{selected_driver1} Position': d1_pos['position'],
                    f'{selected_driver2} Position': d2_pos['position'],
                    'Position Gap': position_gap
                })
    
    if battle_laps:
        battles_df = pd.DataFrame(battle_laps)
        
        # Show battle laps
        st.dataframe(battles_df, use_container_width=True, hide_index=True)
        
        # Create visualization of battle
        fig = go.Figure()
        
        # Get driver colors
        driver1_data = laps_df[laps_df['driver_name'] == selected_driver1]
        driver2_data = laps_df[laps_df['driver_name'] == selected_driver2]
        
        if not driver1_data.empty and not driver2_data.empty:
            driver1_color = driver1_data['team_color'].iloc[0]
            driver2_color = driver2_data['team_color'].iloc[0]
            
            # Add position traces for the battle
            fig.add_trace(go.Scatter(
                x=battles_df['Lap'],
                y=battles_df[f'{selected_driver1} Position'],
                mode='lines+markers',
                name=selected_driver1,
                line=dict(color=f"#{driver1_color}" if not driver1_color.startswith('#') else driver1_color, width=2)
            ))
            
            fig.add_trace(go.Scatter(
                x=battles_df['Lap'],
                y=battles_df[f'{selected_driver2} Position'],
                mode='lines+markers',
                name=selected_driver2,
                line=dict(color=f"#{driver2_color}" if not driver2_color.startswith('#') else driver2_color, width=2)
            ))
            
            # Update layout
            fig.update_layout(
                title=f"Battle: {selected_driver1} vs {selected_driver2}",
                xaxis_title="Lap Number",
                yaxis_title="Position",
                yaxis=dict(
                    autorange="reversed",  # P1 at the top
                    dtick=1
                ),
                hovermode="closest",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Get lap time data for these battle laps
            lap_times = []
            battle_lap_numbers = battles_df['Lap'].tolist()
            
            for lap_num in battle_lap_numbers:
                d1_lap = laps_df[(laps_df['driver_name'] == selected_driver1) & (laps_df['lap_number'] == lap_num)]
                d2_lap = laps_df[(laps_df['driver_name'] == selected_driver2) & (laps_df['lap_number'] == lap_num)]
                
                if not d1_lap.empty and not d2_lap.empty:
                    if pd.notna(d1_lap['lap_time_sec'].iloc[0]) and pd.notna(d2_lap['lap_time_sec'].iloc[0]):
                        lap_times.append({
                            'Lap': int(lap_num),
                            f'{selected_driver1} Time': format_seconds_to_time(d1_lap['lap_time_sec'].iloc[0]),
                            f'{selected_driver2} Time': format_seconds_to_time(d2_lap['lap_time_sec'].iloc[0]),
                            'Delta': d1_lap['lap_time_sec'].iloc[0] - d2_lap['lap_time_sec'].iloc[0],
                            f'{selected_driver1} Compound': d1_lap['compound'].iloc[0] if pd.notna(d1_lap['compound'].iloc[0]) else 'Unknown',
                            f'{selected_driver2} Compound': d2_lap['compound'].iloc[0] if pd.notna(d2_lap['compound'].iloc[0]) else 'Unknown'
                        })
            
            if lap_times:
                lap_times_df = pd.DataFrame(lap_times)
                
                # Show the lap time comparison
                st.subheader("Lap Time Comparison During Battle")
                st.dataframe(lap_times_df, use_container_width=True, hide_index=True)
                
                # Add visualization of lap time delta
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=lap_times_df['Lap'],
                    y=lap_times_df['Delta'],
                    marker_color=[f"#{driver1_color}" if d > 0 else f"#{driver2_color}" for d in lap_times_df['Delta']],
                    hovertemplate=(
                        "Lap: %{x}<br>" +
                        "Delta: %{y:.3f}s<br>" +
                        f"{selected_driver1}: %{{customdata[0]}} ({selected_driver1} {'faster' if selected_driver1 == selected_driver2 else 'slower'})<br>" +
                        f"{selected_driver2}: %{{customdata[1]}}"
                    ),
                    customdata=np.column_stack((
                        lap_times_df[f'{selected_driver1} Compound'],
                        lap_times_df[f'{selected_driver2} Compound']
                    ))
                ))
                
                # Add zero line for reference
                fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="white")
                
                fig.update_layout(
                    title="Lap Time Delta During Battle",
                    xaxis_title="Lap Number",
                    yaxis_title="Time Delta (seconds)",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Add insights
                faster_driver = selected_driver1 if lap_times_df['Delta'].mean() < 0 else selected_driver2
                st.info(f"During this battle, {faster_driver} was generally faster with an average delta of {abs(lap_times_df['Delta'].mean()):.3f}s per lap.")
    else:
        st.info(f"No battle detected between {selected_driver1} and {selected_driver2} (they were never within 3 positions of each other).")


def show_race_results(results_df):
    """Display formatted race results table with team colors."""
    if results_df is None or len(results_df) == 0:
        st.warning("No race results available.")
        return
    
    # Create formatted table
    st.subheader("🏁 Race Results")
    
    # Add position change column
    if 'grid_position' in results_df.columns and 'position' in results_df.columns:
        results_df['position_change'] = results_df['grid_position'] - results_df['position']
        
    # Format the dataframe for display
    display_df = results_df.copy()
    
    # Rename columns for better display
    column_map = {
        'position': 'Pos',
        'driver_name': 'Driver',
        'team_name': 'Team',
        'grid_position': 'Grid',
        'points': 'Points',
        'race_time': 'Time',
        'status': 'Status',
        'position_change': 'Δ Pos'
    }
    
    # Select and rename columns
    cols_to_show = [col for col in column_map.keys() if col in display_df.columns]
    display_df = display_df[cols_to_show]
    display_df = display_df.rename(columns=column_map)
    
    # Format position change column with arrows and colors
    if 'Δ Pos' in display_df.columns:
        display_df['Δ Pos'] = display_df['Δ Pos'].apply(
            lambda x: f"🔼 {x}" if x > 0 else (f"🔽 {abs(x)}" if x < 0 else "◯")
        )
    
    # Display the formatted table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


def show_position_changes(results_df):
    """Create a visual chart showing position changes from grid to finish."""
    if results_df is None or len(results_df) == 0:
        return
    
    if not ('grid_position' in results_df.columns and 'position' in results_df.columns):
        return
    
    # Sort by final position
    df = results_df.sort_values('position')
    
    # Create figure
    fig = go.Figure()
    
    # Add a line for each driver
    for i, row in df.iterrows():
        if pd.isna(row['grid_position']) or pd.isna(row['position']):
            continue
            
        team_color = row['team_color']
        if not team_color.startswith('#'):
            team_color = f"#{team_color}"
            
        fig.add_trace(go.Scatter(
            x=['Start', 'Finish'],
            y=[row['grid_position'], row['position']],
            mode='lines+markers',
            name=row['driver_name'],
            line=dict(color=team_color, width=3),
            marker=dict(size=10),
            hovertemplate="Position: %{y}<br>Driver: " + row['driver_name']
        ))
    
    # Update layout
    fig.update_layout(
        title="Grid to Finish Position Changes",
        xaxis_title="Race Progress",
        yaxis_title="Position",
        yaxis=dict(
            autorange="reversed",
            dtick=1,
            gridcolor='rgba(150, 150, 150, 0.2)'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_points_distribution(results_df):
    """Show pie chart of points distribution by team."""
    if results_df is None or len(results_df) == 0 or 'points' not in results_df.columns:
        return
    
    # Group by team and sum points
    team_points = results_df.groupby(['team_name', 'team_color'])['points'].sum().reset_index()
    
    # Filter teams with points
    team_points = team_points[team_points['points'] > 0]
    
    if len(team_points) == 0:
        return
    
    # Create team color mapping with proper formatting
    color_map = {}
    for _, row in team_points.iterrows():
        team_color = row['team_color']
        if not team_color.startswith('#'):
            team_color = f"#{team_color}"
        color_map[row['team_name']] = team_color
    
    # Create pie chart
    fig = px.pie(
        team_points, 
        values='points', 
        names='team_name',
        color='team_name',
        color_discrete_map=color_map,
        title="Points Distribution by Team"
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show points table
    st.subheader("Team Points in this Race")
    team_points = team_points.sort_values('points', ascending=False)
    
    # Format points table
    display_df = team_points[['team_name', 'points']].copy()
    display_df.columns = ['Team', 'Points']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def show_race_summary(results_df):
    """Display a comprehensive race summary with key statistics."""
    if results_df is None or len(results_df) == 0:
        return
    
    st.subheader("Race Summary")
    
    # Create 4 columns for key stats
    cols = st.columns(4)
    
    # Stats to show
    if 'position' in results_df.columns and len(results_df) > 0:
        winner = results_df[results_df['position'] == 1]
        if len(winner) > 0:
            cols[0].metric("Winner", winner['driver_name'].iloc[0])
    
    if 'position_change' in results_df.columns:
        # Best recovery
        best_recovery = results_df[results_df['position_change'] > 0].sort_values('position_change', ascending=False)
        if len(best_recovery) > 0:
            cols[1].metric("Best Recovery", 
                          f"{best_recovery['driver_name'].iloc[0]} (+{best_recovery['position_change'].iloc[0]})")
    
    # Number of finishers
    if 'status' in results_df.columns:
        finishers = results_df[results_df['status'] == 'Finished'].shape[0]
        cols[2].metric("Finishers", f"{finishers}/{len(results_df)}")
    
    # Points leader (if points exist)
    if 'points' in results_df.columns:
        points_leader = results_df.sort_values('points', ascending=False)
        if len(points_leader) > 0 and points_leader['points'].iloc[0] > 0:
            cols[3].metric("Most Points", 
                          f"{points_leader['driver_name'].iloc[0]} ({points_leader['points'].iloc[0]})")
    
    # Show grid vs finish stats
    if 'grid_position' in results_df.columns and 'position' in results_df.columns:
        st.subheader("Grid vs Finish Insights")
        
        # Calculate averages and improvements
        valid_positions = results_df[pd.notna(results_df['grid_position']) & pd.notna(results_df['position'])]
        
        if not valid_positions.empty:
            avg_grid = valid_positions['grid_position'].mean()
            avg_finish = valid_positions['position'].mean()
            improvements = valid_positions[valid_positions['position_change'] > 0]
            drops = valid_positions[valid_positions['position_change'] < 0]
            
            # Display in 3 columns
            col1, col2, col3 = st.columns(3)
            
            col1.metric("Avg Grid Position", f"{avg_grid:.1f}")
            col1.metric("Avg Finish Position", f"{avg_finish:.1f}")
            
            col2.metric("Drivers Improved", f"{len(improvements)}/{len(valid_positions)}")
            col2.metric("Avg Improvement", f"+{improvements['position_change'].mean():.1f}" if not improvements.empty else "0")
            
            col3.metric("Drivers Lost Positions", f"{len(drops)}/{len(valid_positions)}")
            col3.metric("Avg Positions Lost", f"{abs(drops['position_change'].mean()):.1f}" if not drops.empty else "0")
    
    # Show status breakdown
    if 'status' in results_df.columns:
        status_counts = results_df['status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        
        if not status_counts.empty:
            st.subheader("Race Status Breakdown")
            
            # Create a bar chart of status
            fig = px.bar(
                status_counts,
                x='Status',
                y='Count',
                title="Race Status Breakdown",
                color='Status'
            )
            
            fig.update_layout(
                xaxis_title="Status",
                yaxis_title="Number of Drivers",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)


def show_session_overview(laps_df, session_id, session_type, db):
    """Display overview of qualifying or sprint shootout session."""
    st.subheader("Session Overview")
    
    # Get session results
    results_df = db.execute_query(
        """
        SELECT r.position, r.q1_time, r.q2_time, r.q3_time, r.status,
            d.full_name as driver_name, d.abbreviation, d.driver_number,
            t.name as team_name, t.team_color
        FROM results r
        JOIN drivers d ON r.driver_id = d.id
        JOIN teams t ON d.team_id = t.id
        WHERE r.session_id = ?
        ORDER BY r.position
        """,
        params=(session_id,)
    )
    
    if results_df.empty:
        st.warning("No session results available.")
        return
    
    # Create formatted table for qualifying results
    st.subheader("Session Results")
    
    # Format the dataframe for display
    display_df = results_df.copy()
    
    # Rename columns for better display
    column_map = {
        'position': 'Pos',
        'driver_name': 'Driver',
        'team_name': 'Team',
        'q1_time': 'Q1',
        'q2_time': 'Q2',
        'q3_time': 'Q3',
        'status': 'Status'
    }
    
    # Select and rename columns
    cols_to_show = [col for col in column_map.keys() if col in display_df.columns]
    display_df = display_df[cols_to_show]
    display_df = display_df.rename(columns=column_map)
    
    # Display the formatted table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Show gap to pole visualization
    if session_type in ['qualifying', 'sprint_qualifying', 'sprint_shootout']:
        st.subheader("Gap to Pole Position")
        
        # Analyze fastest laps
        fastest_laps = {}
        
        # Get qualifying segments based on session type
        segments = ['Q1', 'Q2', 'Q3'] if session_type == 'qualifying' else ['Q1', 'Q2']
        
        for segment in segments:
            # Convert string times to seconds
            if segment in display_df.columns:
                display_df[f'{segment}_seconds'] = display_df[segment].apply(convert_string_time_to_seconds)
        
        # Create a visualization of gaps to pole for each segment
        for segment in segments:
            sec_col = f'{segment}_seconds'
            if sec_col in display_df.columns:
                # Filter to non-null times
                segment_data = display_df[pd.notna(display_df[sec_col])].copy()
                
                if not segment_data.empty:
                    # Sort by time
                    segment_data = segment_data.sort_values(sec_col)
                    
                    # Calculate gap to pole
                    pole_time = segment_data[sec_col].min()
                    segment_data['gap_to_pole'] = segment_data[sec_col] - pole_time
                    
                    # Create bar chart of gaps
                    fig = go.Figure()
                    
                    for _, row in segment_data.iterrows():
                        team_color = results_df[results_df['driver_name'] == row['Driver']]['team_color'].iloc[0]
                        if not team_color.startswith('#'):
                            team_color = f"#{team_color}"
                        
                        fig.add_trace(go.Bar(
                            x=[row['gap_to_pole']],
                            y=[row['Driver']],
                            orientation='h',
                            name=row['Driver'],
                            marker_color=team_color,
                            text=f"+{row['gap_to_pole']:.3f}s" if row['gap_to_pole'] > 0 else "POLE",
                            textposition='outside',
                            hovertemplate=(
                                "Driver: %{y}<br>" +
                                f"Time: {row[segment]}<br>" +
                                f"Gap to Pole: {'+' if row['gap_to_pole'] > 0 else ''}{row['gap_to_pole']:.3f}s"
                            )
                        ))
                    
                    # Update layout
                    fig.update_layout(
                        title=f"{segment} - Gap to Pole",
                        xaxis_title="Gap (seconds)",
                        yaxis_title="Driver",
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        showlegend=False,
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
    
    # Show track evolution if we have enough data
    if len(laps_df) > 0:
        st.subheader("Track Evolution")
        
        # Get lap times for each driver
        lap_times = laps_df.groupby(['lap_number']).agg({
            'lap_time_sec': 'min',  # Fastest lap time per lap number
        }).reset_index()
        
        # Remove any invalid times
        lap_times = lap_times[pd.notna(lap_times['lap_time_sec'])]
        
        if not lap_times.empty:
            # Create a line chart showing evolution of lap times
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=lap_times['lap_number'],
                y=lap_times['lap_time_sec'],
                mode='lines+markers',
                name="Fastest Lap Time",
                line=dict(color='orangered', width=2)
            ))
            
            # Add a trend line 
            try:
                from scipy import stats
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    lap_times['lap_number'], 
                    lap_times['lap_time_sec']
                )
                
                x_trend = np.array([lap_times['lap_number'].min(), lap_times['lap_number'].max()])
                y_trend = intercept + slope * x_trend
                
                fig.add_trace(go.Scatter(
                    x=x_trend,
                    y=y_trend,
                    mode='lines',
                    name=f"Trend (Slope: {slope:.4f})",
                    line=dict(color='white', width=2, dash='dash')
                ))
                
                # Calculate lap time improvement per lap
                improvement_per_lap = -slope  # Negative slope means times are decreasing
                total_improvement = -slope * (lap_times['lap_number'].max() - lap_times['lap_number'].min())
                
                # Show improvement stats
                st.metric("Track Evolution Rate", f"{improvement_per_lap:.4f} sec/lap")
                st.metric("Total Improvement", f"{total_improvement:.3f} seconds")
                
                # Add trend description
                if slope < 0:
                    st.success(f"The track got faster by {improvement_per_lap:.4f} seconds per lap")
                elif slope > 0:
                    st.error(f"The track got slower by {-improvement_per_lap:.4f} seconds per lap")
                else:
                    st.info("No significant track evolution detected")
                
            except:
                # Skip trend line if there's an error
                pass
            
            # Update layout
            fig.update_layout(
                title="Track Evolution - Fastest Lap Time per Lap Number",
                xaxis_title="Lap Number",
                yaxis_title="Lap Time (seconds)",
                yaxis=dict(autorange="reversed"),  # Lower times at the top
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)


def convert_string_time_to_seconds(time_str):
    """Convert lap time strings from results (e.g., '1:30.123') to seconds."""
    if not time_str or pd.isna(time_str):
        return None
    
    try:
        if isinstance(time_str, str) and ":" in time_str:
            parts = time_str.split(":")
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
        return float(time_str)
    except (ValueError, TypeError):
        return None


def show_long_run_analysis(laps_df):
    """Analyze long runs in practice sessions."""
    st.subheader("Long Run Analysis")
    
    # Get unique drivers
    drivers = laps_df['driver_name'].unique().tolist()
    
    # Allow user to select drivers
    selected_drivers = st.multiselect("Select Drivers", drivers, default=drivers[:3] if len(drivers) > 3 else drivers)
    
    # Filter data
    filtered_df = laps_df[laps_df['driver_name'].isin(selected_drivers)]
    filtered_df = filtered_df[~(filtered_df['deleted'] == 1)]
    
    if filtered_df.empty:
        st.warning("No data available with the current filters.")
        return
    
    # Identify long runs (consecutive laps with same compound)
    long_runs = []
    
    for driver in selected_drivers:
        driver_data = filtered_df[filtered_df['driver_name'] == driver]
        
        if driver_data.empty:
            continue
            
        # Group by stint
        stints = driver_data['stint'].unique()
        stints = [s for s in stints if pd.notna(s)]
        
        for stint in stints:
            stint_data = driver_data[driver_data['stint'] == stint]
            
            if len(stint_data) >= 3:  # Consider a long run as 3+ consecutive laps
                compound = stint_data['compound'].iloc[0] if pd.notna(stint_data['compound'].iloc[0]) else 'Unknown'
                
                # Calculate stint statistics
                lap_times = stint_data['lap_time_sec'].dropna()
                if len(lap_times) > 0:
                    min_lap_time = lap_times.min()
                    max_lap_time = lap_times.max()
                    avg_lap_time = lap_times.mean()
                    
                    # Calculate simple linear degradation
                    laps = np.arange(len(lap_times))
                    try:
                        from scipy import stats
                        slope, intercept, r_value, p_value, std_err = stats.linregress(
                            range(len(lap_times)), 
                            lap_times
                        )
                        degradation = slope  # seconds per lap
                    except:
                        degradation = (max_lap_time - min_lap_time) / len(lap_times)
                    
                    long_runs.append({
                        'Driver': driver,
                        'Stint': int(stint),
                        'Compound': compound,
                        'Laps': len(stint_data),
                        'Avg Time': format_seconds_to_time(avg_lap_time),
                        'Min Time': format_seconds_to_time(min_lap_time),
                        'Degradation': f"{degradation:.4f}s/lap",
                        'Degradation Value': degradation,
                        'Lap Range': f"{int(stint_data['lap_number'].min())}-{int(stint_data['lap_number'].max())}",
                        'Team Color': stint_data['team_color'].iloc[0]
                    })
    
    if long_runs:
        # Create a dataframe of long runs
        long_runs_df = pd.DataFrame(long_runs)
        
        # Sort by average pace
        long_runs_df = long_runs_df.sort_values('Min Time')
        
        # Display the long runs table
        st.dataframe(long_runs_df.drop('Team Color', axis=1), use_container_width=True, hide_index=True)
        
        # Create a visualization of long run degradation
        fig = go.Figure()
        
        # Create a color map for compounds
        compound_colors = {
            'S': 'red',
            'M': 'yellow',
            'H': 'white',
            'I': 'green',
            'W': 'blue',
            'Unknown': 'gray'
        }
        
        for _, run in long_runs_df.iterrows():
            # Choose color based on compound
            if run['Compound'] in compound_colors:
                color = compound_colors[run['Compound']]
            else:
                team_color = run['Team Color']
                color = f"#{team_color}" if not team_color.startswith('#') else team_color
            
            fig.add_trace(go.Bar(
                x=[run['Driver'] + f" (Stint {run['Stint']})"],
                y=[run['Degradation Value']],
                name=f"{run['Driver']} - {run['Compound']}",
                marker_color=color,
                text=run['Degradation'],
                hovertemplate=(
                    "Driver: %{x}<br>" +
                    "Degradation: %{y:.4f}s/lap<br>" +
                    f"Compound: {run['Compound']}<br>" +
                    f"Laps: {run['Laps']}<br>" +
                    f"Lap Range: {run['Lap Range']}"
                )
            ))
        
        # Update layout
        fig.update_layout(
            title="Tire Degradation Comparison",
            xaxis_title="Driver and Stint",
            yaxis_title="Degradation Rate (s/lap)",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show a race pace simulation
        st.subheader("Race Pace Simulation")
        
        # Estimate race pace for each driver/compound over a typical race distance
        race_length = st.slider("Simulate Race Length (laps)", min_value=10, max_value=70, value=50)
        
        # Create pace simulation chart
        fig = go.Figure()
        
        for _, run in long_runs_df.iterrows():
            driver = run['Driver']
            compound = run['Compound']
            degradation = run['Degradation Value']
            min_time = run['Min Time']
            
            # Parse min_time string back to seconds (format is "M:SS.mmm")
            try:
                min_time_parts = min_time.split(':')
                min_time_sec = int(min_time_parts[0]) * 60 + float(min_time_parts[1])
            except:
                # If parsing fails, skip this run
                continue
            
            # Calculate projected lap times
            laps = list(range(1, race_length + 1))
            projected_times = [min_time_sec + degradation * (lap - 1) for lap in laps]

            # Choose color based on compound
            if compound in compound_colors:
                color = compound_colors[compound]
            else:
                team_color = run['Team Color']
                color = f"#{team_color}" if not team_color.startswith('#') else team_color
            
            # Create the trace
            fig.add_trace(go.Scatter(
                x=laps,
                y=projected_times,
                mode='lines',
                name=f"{driver} - {compound}",
                line=dict(color=color, width=2),
                hovertemplate=(
                    "Driver: " + driver + "<br>" +
                    "Compound: " + compound + "<br>" +
                    "Lap: %{x}<br>" +
                    "Projected Time: %{y:.3f}s<br>" +
                    f"Degradation: {degradation:.4f}s/lap"
                )
            ))
        
        # Update layout
        fig.update_layout(
            title="Race Pace Simulation",
            xaxis_title="Lap Number",
            yaxis_title="Projected Lap Time (seconds)",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Calculate cumulative race times
        st.subheader("Race Time Projection")
        
        # Calculate cumulative times for each long run
        cumulative_times = {}
        
        for _, run in long_runs_df.iterrows():
            driver = run['Driver']
            compound = run['Compound']
            degradation = run['Degradation Value']
            
            # Parse min_time string back to seconds
            try:
                min_time = run['Min Time']
                min_time_parts = min_time.split(':')
                min_time_sec = int(min_time_parts[0]) * 60 + float(min_time_parts[1])
            except:
                # If parsing fails, skip this run
                continue
            
            # Calculate cumulative race time
            lap_times = [min_time_sec + degradation * lap for lap in list(range(race_length))]
            cumulative_time = sum(lap_times)
            
            # Store in dictionary
            key = f"{driver} - {compound}"
            cumulative_times[key] = {
                'Driver': driver,
                'Compound': compound,
                'Total Time': cumulative_time,
                'Formatted Time': format_race_time(cumulative_time),
                'Avg Lap': cumulative_time / race_length,
                'Team Color': run['Team Color']
            }
        
        if cumulative_times:
            # Create a dataframe for display
            cumulative_df = pd.DataFrame(cumulative_times.values())
            
            # Sort by total time
            cumulative_df = cumulative_df.sort_values('Total Time')
            
            # Add gap to fastest
            if len(cumulative_df) > 0:
                fastest_time = cumulative_df['Total Time'].min()
                cumulative_df['Gap'] = cumulative_df['Total Time'] - fastest_time
                cumulative_df['Gap'] = cumulative_df['Gap'].apply(lambda x: f"+{x:.3f}s" if x > 0 else "Leader")
            
            # Create a formatted dataframe for display
            display_df = cumulative_df[['Driver', 'Compound', 'Formatted Time', 'Avg Lap', 'Gap']].copy()
            display_df.columns = ['Driver', 'Compound', 'Projected Race Time', 'Avg Lap Time', 'Gap']
            
            # Display the table
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Create a bar chart of race times
            fig = go.Figure()
            
            for _, row in cumulative_df.iterrows():
                # Choose color based on compound
                if row['Compound'] in compound_colors:
                    color = compound_colors[row['Compound']]
                else:
                    team_color = row['Team Color']
                    color = f"#{team_color}" if not team_color.startswith('#') else team_color
                
                fig.add_trace(go.Bar(
                    x=[f"{row['Driver']} - {row['Compound']}"],
                    y=[row['Total Time']],
                    marker_color=color,
                    text=row['Formatted Time'],
                    hovertemplate=(
                        "Driver: " + row['Driver'] + "<br>" +
                        "Compound: " + row['Compound'] + "<br>" +
                        "Projected Race Time: " + row['Formatted Time'] + "<br>" +
                        "Gap: " + row['Gap']
                    )
                ))
            
            # Update layout
            fig.update_layout(
                title=f"Projected Race Time ({race_length} laps)",
                xaxis_title="Driver - Compound",
                yaxis_title="Total Race Time (seconds)",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No long runs detected (3+ lap stints). Try selecting different drivers or sessions.")


def format_race_time(seconds):
    """Format race time in MM:SS.mmm format."""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:.3f}"