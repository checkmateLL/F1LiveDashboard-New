# frontend/pages/pit_stop_strategy.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler
from sklearn.ensemble import RandomForestRegressor

st.set_page_config(layout="wide")

st.title("Pit Stop Strategy Optimization (ML-Based Simulation)")

def get_pit_stop_data(session_id):
    """
    Retrieves historical pit stop and race pace data for ML-based strategy simulation.
    """
    session_id = int(session_id)  # Ensure session_id is integer
    query = """
        SELECT laps.lap_number, drivers.driver_name, laps.lap_time, laps.compound, 
               pit_stops.total_stops, pit_stops.stint_length, results.classified_position
        FROM laps
        JOIN drivers ON laps.driver_id = drivers.driver_id
        JOIN pit_stops ON laps.driver_id = pit_stops.driver_id AND laps.session_id = pit_stops.session_id
        JOIN results ON laps.driver_id = results.driver_id AND laps.session_id = results.session_id
        WHERE laps.session_id = ?
        ORDER BY laps.lap_number, drivers.driver_name
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (session_id,))
    
    return df

def train_pit_strategy_model(df):
    """
    Trains a Random Forest model to predict race time based on pit stop strategy.
    """
    df = df.dropna()
    X = df[["total_stops", "stint_length"]]
    y = df["lap_time"]
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    return model

def simulate_pit_strategy(model, total_stops, stint_length):
    """
    Uses trained model to predict lap time based on pit stop strategy.
    """
    return model.predict([[total_stops, stint_length]])[0]

def plot_pit_strategy_simulation(df, model):
    """
    Simulates 1-stop, 2-stop, and 3-stop strategies and compares race outcomes.
    """
    strategy_options = [1, 2, 3]
    stint_lengths = [df["stint_length"].mean()] * len(strategy_options)
    predictions = [simulate_pit_strategy(model, stops, stint) for stops, stint in zip(strategy_options, stint_lengths)]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x=strategy_options, y=predictions, ax=ax)
    ax.set_xlabel("Pit Stop Strategy (Total Stops)")
    ax.set_ylabel("Predicted Average Lap Time (s)")
    ax.set_title("Pit Stop Strategy Simulation & Lap Time Impact")
    st.pyplot(fig)

# Fetch session data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM laps")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
selected_session = st.selectbox("Select Session", session_list if session_list else [0])

df = get_pit_stop_data(selected_session)

if not df.empty:
    model = train_pit_strategy_model(df)
    plot_pit_strategy_simulation(df, model)
    
    st.write("### Pit Stop Strategy Data")
    st.dataframe(df)
else:
    st.warning("No pit stop strategy data available for this session.")
