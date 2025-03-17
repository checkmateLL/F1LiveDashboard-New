import sys
import os

# Ensure Python recognizes backend directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from frontend.pages.season_overview import season_overview
from frontend.pages.race_results import race_results
from frontend.pages.lap_times import lap_times
from frontend.pages.telemetry import telemetry
from frontend.pages.standings import standings
from frontend.pages.performance import performance
from frontend.pages.home import home  # Ensure Home Page is included

# Set Page Configuration
st.set_page_config(
    page_title="F1 Live Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar Navigation
st.sidebar.title("🏎️ F1 Dashboard Navigation")
page = st.sidebar.radio(
    "Select Page",
    ["Home", "Season Overview", "Race Results", "Lap Times", "Telemetry Analysis", "Standings", "Performance Analysis"]
)

# Load the selected page
if page == "Home":
    home()
elif page == "Season Overview":
    season_overview()
elif page == "Race Results":
    race_results()
elif page == "Lap Times":
    lap_times()
elif page == "Telemetry Analysis":
    telemetry()
elif page == "Standings":
    standings()
elif page == "Performance Analysis":
    performance()
