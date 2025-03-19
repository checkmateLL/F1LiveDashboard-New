# frontend/pages/dnf_analysis.py

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from backend.db_connection import get_db_handler

st.set_page_config(layout="wide")

st.title("DNF (Did Not Finish) Analysis & Failure Trends (Optimized Query Execution & ID Handling)")

def get_dnf_data(session_id):
    """
    Retrieves data on DNFs, including lap of retirement and failure reasons.
    """
    session_id = int(session_id)  # Ensure session_id is integer
    query = """
        SELECT drivers.driver_name, drivers.team_name, dnfs.lap_number, dnfs.failure_reason
        FROM dnfs
        JOIN drivers ON dnfs.driver_id = drivers.driver_id
        WHERE dnfs.session_id = ?
        ORDER BY dnfs.lap_number
    """
    
    with get_db_handler() as db:
        df = db.execute_query(query, (session_id,))
    
    return df

def plot_dnf_timeline(df):
    """
    Visualizes DNFs over the race duration.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    for driver in df["driver_name"].unique():
        driver_df = df[df["driver_name"] == driver]
        ax.scatter(driver_df["lap_number"], [driver] * len(driver_df), label=driver, s=100)
    ax.set_xlabel("Lap Number")
    ax.set_title("DNF Timeline (When Each Driver Retired)")
    ax.legend()
    st.pyplot(fig)

def plot_dnf_reasons(df):
    """
    Shows distribution of failure reasons causing DNFs.
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.countplot(ax=ax, y=df["failure_reason"], order=df["failure_reason"].value_counts().index)
    ax.set_xlabel("Number of DNFs")
    ax.set_ylabel("Failure Reason")
    ax.set_title("DNF Causes Breakdown")
    st.pyplot(fig)

def plot_team_dnf_analysis(df):
    """
    Compares DNFs across teams to detect reliability issues.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.countplot(ax=ax, y=df["team_name"], order=df["team_name"].value_counts().index)
    ax.set_xlabel("Number of DNFs")
    ax.set_ylabel("Team")
    ax.set_title("DNFs Per Team")
    st.pyplot(fig)

# Fetch session data
with get_db_handler() as db:
    sessions = db.execute_query("SELECT DISTINCT session_id FROM dnfs")

session_list = [int(session["session_id"]) for session in sessions if isinstance(session, dict) and "session_id" in session]
selected_session = st.selectbox("Select Session", session_list if session_list else [0])

df = get_dnf_data(selected_session)

if not df.empty:
    plot_dnf_timeline(df)
    plot_dnf_reasons(df)
    plot_team_dnf_analysis(df)
    
    st.write("### DNF Data")
    st.dataframe(df)
else:
    st.warning("No DNF data available for this session.")
