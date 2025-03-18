import sys
import os

# Ensure Python recognizes backend directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from frontend.components.navbar import create_navbar
from frontend.pages.home import home
from frontend.pages.season_overview import season_overview
from frontend.pages.race_results import race_results
from frontend.pages.lap_times import lap_times
from frontend.pages.telemetry import telemetry
from frontend.pages.standings import standings
from frontend.pages.performance import performance
from frontend.pages.analytics import analytics  # Renamed from 'live'
from frontend.pages.race_replay import race_replay  # New page

# Set Page Configuration
st.set_page_config(
    page_title="F1 Dashboard",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for styling
st.markdown("""
<style>
    /* Main background and text colors */
    .main .block-container {
        background-color: #0e1117;
        color: #f0f2f6;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #16171d;
    }
    
    /* Team colors for visual elements */
    .mercedes {color: #00D2BE;}
    .redbull {color: #0600EF;}
    .ferrari {color: #DC0000;}
    .mclaren {color: #FF8700;}
    .alpine {color: #0090FF;}
    .aston_martin {color: #006F62;}
    .williams {color: #005AFF;}
    .alfa_tauri {color: #2B4562;}
    .alfa_romeo {color: #900000;}
    .haas {color: #FFFFFF;}
    
    /* Headers styling */
    h1, h2, h3 {
        font-weight: bold;
    }
    
    /* Card styling */
    .event-card {
        border: 1px solid #333;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        background-color: #1e1e1e;
        transition: transform 0.3s;
        cursor: pointer;
    }
    
    .event-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #e10600;
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 5px;
        padding: 8px 16px;
    }
    
    .stButton>button:hover {
        background-color: #b80500;
    }
    
    /* Countdown styling */
    .countdown-container {
        display: flex;
        justify-content: center;
        text-align: center;
        margin: 20px 0;
    }
    .countdown-box {
        background-color: #e10600;
        color: white;
        border-radius: 5px;
        padding: 15px;
        margin: 0 10px;
        min-width: 80px;
    }
    .countdown-value {
        font-size: 32px;
        font-weight: bold;
    }
    .countdown-label {
        font-size: 14px;
        margin-top: 5px;
    }
    .countdown-event {
        text-align: center;
        font-size: 24px;
        margin-bottom: 10px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.image("https://www.formula1.com/etc/designs/fom-website/images/f1_logo.svg", width=200)
st.sidebar.title("F1 Dashboard")

# Top Navigation
page = create_navbar()

# Load the selected page
if page == "Home":
    home()
elif page == "Analytics":
    analytics()
elif page == "Race Replay":
    race_replay()
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

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 🏎️ F1 Dashboard")
st.sidebar.markdown("© 2025 CheckmateLL")