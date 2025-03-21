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

def is_data_empty(data):
    """Check if data is empty, whether it's a DataFrame or list/dict."""
    if isinstance(data, pd.DataFrame):
        return data.empty
    return not bool(data)

def get_pit_stop_data(session_id):
    """
    Retrieves historical pit stop and race pace data for ML-based strategy simulation.
    """
    session_id = int(session_id)  # Ensure session_id is integer
    query = """
        SELECT l.lap_number, d.full_name as driver_name, l.lap_time, l.compound, 
               COUNT(DISTINCT l.stint) - 1 as total_stops,
               MAX(l.tyre_life) as stint_length, 
               r.position as classified_position
        FROM laps l
        JOIN drivers d ON l.driver_id = d.id
        LEFT JOIN results r ON l.driver_id = r.driver_id AND l.session_id = r.session_id
        WHERE l.session_id = ?
        GROUP BY l.driver_id
        ORDER BY l.lap_number, d.full_name
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

if not is_data_empty(df):
    model = train_pit_strategy_model(df)
    plot_pit_strategy_simulation(df, model)
    
    st.write("### Pit Stop Strategy Data")
    st.dataframe(df)
else:
    st.warning("No pit stop strategy data available for this session.")
