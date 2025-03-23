import streamlit as st
import pandas as pd
import numpy as np


def is_data_empty(data):
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)


def ensure_dataframe(data):
    if not isinstance(data, pd.DataFrame):
        try:
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error converting data to DataFrame: {e}")
            return pd.DataFrame()
    return data


def show_race_results(results_df):
    results_df = ensure_dataframe(results_df)

    if is_data_empty(results_df):
        st.warning("No race results available.")
        return

    st.subheader("🏁 Race Results")

    required_columns = ['position', 'driver_name', 'team_name', 'grid_position', 'points', 'race_time', 'status']
    missing_columns = [col for col in required_columns if col not in results_df.columns]
    if missing_columns:
        st.warning(f"Missing columns: {', '.join(missing_columns)}")
        return

    display_df = results_df.rename(columns={
        'position': 'Pos',
        'driver_name': 'Driver',
        'team_name': 'Team',
        'grid_position': 'Grid',
        'points': 'Points',
        'race_time': 'Time',
        'status': 'Status'
    })

    display_df['Δ Pos'] = results_df['grid_position'] - results_df['position']

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def show_position_changes(results_df):
    results_df = ensure_dataframe(results_df)

    if is_data_empty(results_df):
        st.warning("No data available for position changes.")
        return

    required_columns = ['grid_position', 'position', 'driver_name', 'team_color']
    missing_columns = [col for col in required_columns if col not in results_df.columns]
    if missing_columns:
        st.warning(f"Missing columns: {', '.join(missing_columns)}")
        return

    try:
        import plotly.graph_objects as go

        df = results_df.dropna(subset=['grid_position', 'position']).sort_values('position')

        fig = go.Figure()

        for _, row in df.iterrows():
            team_color = row['team_color']
            team_color = team_color if team_color.startswith('#') else f"#{team_color}"

            fig.add_trace(go.Scatter(
                x=['Start', 'Finish'],
                y=[row['grid_position'], row['position']],
                mode='lines+markers',
                name=row['driver_name'],
                line=dict(color=team_color, width=3),
                marker=dict(size=10),
                hovertemplate="Position: %{y}<br>Driver: " + row['driver_name']
            ))

        fig.update_layout(
            title="Grid to Finish Position Changes",
            xaxis_title="Race Progress",
            yaxis_title="Position",
            yaxis=dict(autorange="reversed", dtick=1, gridcolor='rgba(150,150,150,0.2)'),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            legend=dict(orientation="h", y=1.02, x=1, yanchor="bottom", xanchor="right"),
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating position changes chart: {e}")


def show_points_distribution(results_df):
    results_df = ensure_dataframe(results_df)

    if is_data_empty(results_df) or 'points' not in results_df.columns:
        st.warning("Points data not available.")
        return

    try:
        import plotly.express as px

        team_points = results_df.groupby('team_name')['points'].sum().reset_index()
        team_points = team_points[team_points['points'] > 0]

        if is_data_empty(team_points):
            st.warning("No points data to display.")
            return

        fig = px.pie(
            team_points,
            values='points',
            names='team_name',
            title="Points Distribution by Team"
        )

        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )

        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating points distribution chart: {e}")


def show_race_summary(results_df):
    results_df = ensure_dataframe(results_df)

    if is_data_empty(results_df):
        st.warning("No race summary data available.")
        return

    st.subheader("Race Summary")

    cols = st.columns(4)

    winner = results_df.query('position == 1')
    if not winner.empty:
        cols[0].metric("Winner", winner['driver_name'].iloc[0])

    results_df['position_change'] = results_df['grid_position'] - results_df['position']
    best_recovery = results_df[results_df['position_change'] > 0].sort_values('position_change', ascending=False)
    if not best_recovery.empty:
        cols[1].metric("Best Recovery", f"{best_recovery['driver_name'].iloc[0]} (+{best_recovery['position_change'].iloc[0]})")

    finishers = results_df.query('status == "Finished"').shape[0]
    cols[2].metric("Finishers", f"{finishers}/{len(results_df)}")

    points_leader = results_df.sort_values('points', ascending=False)
    if not points_leader.empty and points_leader['points'].iloc[0] > 0:
        cols[3].metric("Most Points", f"{points_leader['driver_name'].iloc[0]} ({points_leader['points'].iloc[0]})")
