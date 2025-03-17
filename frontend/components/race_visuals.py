import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def show_race_results(df):
    st.subheader("🏁 Race Results")
    st.dataframe(df)
