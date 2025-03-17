import streamlit as st
from backend.standings import get_driver_standings

def standings():
    st.title("🏆 Championship Standings")
    
    year = st.selectbox("Select Year", [2023, 2024, 2025])
    df = get_driver_standings(year)
    
    st.dataframe(df)
