import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def show_telemetry(df):
    st.subheader("📡 Telemetry Data")
    st.line_chart(df[['time', 'speed']])
