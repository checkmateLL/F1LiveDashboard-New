import streamlit as st
from backend.performance import get_performance_data

def performance():
    st.title("📊 Performance Analysis")
    
    driver_id = st.selectbox("Select Driver", [1, 2, 3])  # Example
    df = get_performance_data(driver_id)
    
    st.line_chart(df[['time', 'speed']])
