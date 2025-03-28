import sys
import os

# Ensure Python recognizes backend directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from backend.error_handling import ValidationError, DatabaseError
from frontend.components.navbar import create_navbar
from frontend.pages.home import home
from frontend.pages.season_overview import season_overview
from frontend.pages.race_results import race_results
from frontend.pages.lap_times import lap_times
from frontend.pages.standings import standings
from frontend.pages.performance import performance
from frontend.pages.race_analysis import race_analysis
from frontend.pages.race_replay import race_replay
from frontend.pages.event_schedule import event_schedule
from frontend.pages.dnf_analysis import dnf_analysis
from frontend.pages.driver_performance_comparison import get_driver_performance_data

# Set Page Configuration
st.set_page_config(
    page_title="F1 Dashboard",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Store current page in session state for persistent navigation
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Home"

selected_page = create_navbar()
if selected_page != st.session_state["current_page"]:
    st.session_state["current_page"] = selected_page

page = st.session_state["current_page"]

# Custom CSS for styling (moved to function for reusability)
def apply_styles():
    st.markdown("""
    <style>
        /* Main background and text colors */
        .main .block-container { background-color: #0e1117; color: #f0f2f6; }
        
        /* Sidebar styling */
        .sidebar .sidebar-content { background-color: #16171d; }
        
        /* Team colors */
        .mercedes {color: #00D2BE;} .redbull {color: #0600EF;}
        .ferrari {color: #DC0000;} .mclaren {color: #FF8700;}
        .alpine {color: #0090FF;} .aston_martin {color: #006F62;}
        .williams {color: #005AFF;} .alfa_tauri {color: #2B4562;}
        .alfa_romeo {color: #900000;} .haas {color: #FFFFFF;}

        /* Headers */
        h1, h2, h3 { font-weight: bold; }
        
        /* Button styling */
        .stButton>button {
            background-color: #e10600; color: white; font-weight: bold;
            border: none; border-radius: 5px; padding: 8px 16px;
        }
        .stButton>button:hover { background-color: #b80500; }

        /* Countdown styling */
        .countdown-container {
            display: flex; justify-content: center; text-align: center;
            margin: 20px 0;
        }
        .countdown-box {
            background-color: #e10600; color: white; border-radius: 5px;
            padding: 15px; margin: 0 10px; min-width: 80px;
        }
        .countdown-value { font-size: 32px; font-weight: bold; }
        .countdown-label { font-size: 14px; margin-top: 5px; }
        .countdown-event { text-align: center; font-size: 24px; margin-bottom: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

apply_styles()  # Apply styles dynamically

st.sidebar.image("https://www.formula1.com/etc/designs/fom-website/images/f1_logo.svg", width=200)
st.sidebar.title("F1 Dashboard")

# Persistent Top Navigation
  # Store current page in session state

# Create sidebar navigation as well
pages = [
    "Home", 
    "Event Schedule", 
    "Race Analysis", 
    "Race Replay", 
    "Season Overview", 
    "Race Results", 
    "Lap Times", 
    "Standings", 
    "Performance Analysis",
    "DNF Analysis",
    "Driver Performance Data"
]

selected_page = st.sidebar.radio("Navigation", pages, index=pages.index(st.session_state["current_page"]))

# Ensure both navigation systems sync
if selected_page != st.session_state["current_page"]:
    st.session_state["current_page"] = selected_page
    page = selected_page

# Load the selected page dynamically
page_mapping = {
    "Home": home,
    "Event Schedule": event_schedule,
    "Race Analysis": race_analysis,
    "Race Replay": race_replay,
    "Season Overview": season_overview,
    "Race Results": race_results,
    "Lap Times": lap_times,
    "Standings": standings,
    "Performance Analysis": performance,
    "DNF Analysis": dnf_analysis,
    "Driver Performance Data": get_driver_performance_data
}

# Call the selected page function if it exists
if page in page_mapping:
    try:
        page_mapping[page]()
    except (ValidationError, DatabaseError) as e:
        st.error(f"⚠️ Error loading page: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 🏎️ F1 Dashboard")
st.sidebar.markdown("© 2025 CheckmateLL")