import streamlit as st

def create_navbar():
    """Creates a horizontal navigation bar and returns the selected page."""
    
    # Container for horizontal nav
    with st.container():
        cols = st.columns([1, 1, 1, 1, 1, 1, 1, 1])
        
        # Nav items with icons
        selected = None
        
        if cols[0].button("🏠 Home"):
            selected = "Home"
        if cols[1].button("📊 Analytics"):  # Changed from "Live"
            selected = "Analytics"
        if cols[2].button("📽️ Race Replay"):  # New button for Race Replay
            selected = "Race Replay"
        if cols[3].button("📅 Season"):
            selected = "Season Overview"
        if cols[4].button("🏁 Results"):
            selected = "Race Results"
        if cols[5].button("⏱️ Lap Times"):
            selected = "Lap Times"
        if cols[6].button("📡 Telemetry"):
            selected = "Telemetry Analysis"
        if cols[7].button("🏆 Standings"):
            selected = "Standings"
    
    # If nothing selected from navbar, use sidebar
    if not selected:
        selected = st.sidebar.radio(
            "Navigation",
            [
                "Home", 
                "Analytics", 
                "Race Replay",
                "Season Overview", 
                "Race Results", 
                "Lap Times", 
                "Telemetry Analysis", 
                "Standings", 
                "Performance Analysis"
            ]
        )
    
    # Add separating line below navbar
    st.markdown("""<hr style="height:2px;border:none;color:#333;background-color:#333;" />""", unsafe_allow_html=True)
    
    return selected

# Helper function for creating formatted section titles
def section_title(title, icon=""):
    """Creates a consistently formatted section title."""
    st.markdown(f"## {icon} {title}", unsafe_allow_html=True)
    st.markdown("---")