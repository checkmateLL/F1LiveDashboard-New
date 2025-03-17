import streamlit as st
from backend.lap_times import get_lap_times

def lap_times():
    st.title("⏱ Lap Times")
    
    session_id = st.selectbox("Select Session", [1, 2, 3])  # Example
    df = get_lap_times(session_id)
    
    st.dataframe(df)
