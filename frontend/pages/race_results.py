import streamlit as st
from backend.results import get_race_results

def race_results():
    st.title("🏁 Race Results")
    
    session_id = st.selectbox("Select Session", [1, 2, 3])  # Example sessions
    df = get_race_results(session_id)
    
    st.dataframe(df)
