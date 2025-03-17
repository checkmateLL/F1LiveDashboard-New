import streamlit as st
from backend.telemetry import get_telemetry

def telemetry():
    st.title("📡 Telemetry Analysis")
    
    session_id = st.selectbox("Select Session", [1, 2, 3])  # Example
    df = get_telemetry(session_id)
    
    st.line_chart(df[['time', 'speed']])
