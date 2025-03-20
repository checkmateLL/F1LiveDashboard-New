import streamlit as st

def create_navbar():
    """Creates a styled horizontal navigation bar and returns the selected page."""

    # Ensure session state stores navigation
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Home"

    # Define navigation options
    nav_items = {
        "🏠 Home": "Home",
        "🏎️ Race Analysis": "Race Analysis",
        "📽️ Race Replay": "Race Replay",
        "📅 Season Overview": "Season Overview",
        "🏁 Results": "Race Results",
        "🏆 Standings": "Standings",
        "📊 Performance": "Performance Analysis",
        "📅 Event Schedule": "Event Schedule"
    }

    # Styling for navbar
    st.markdown("""
    <style>
        .nav-container {
            display: flex; justify-content: center; gap: 10px;
            background-color: #16171d; padding: 10px; border-radius: 8px;
        }
        .nav-button {
            background-color: #e10600; color: white; font-weight: bold;
            border: none; border-radius: 5px; padding: 10px 20px;
            cursor: pointer;
        }
        .nav-button:hover {
            background-color: #b80500;
        }
    </style>
    """, unsafe_allow_html=True)

    # Create horizontal navbar
    selected = None
    cols = st.columns(len(nav_items))

    for idx, (label, page) in enumerate(nav_items.items()):
        if cols[idx].button(label, key=f"nav_{page}"):
            selected = page

    # Store selected page in session state
    if selected:
        st.session_state["current_page"] = selected
    else:
        selected = st.session_state["current_page"]  # Default to last selected page

    # Add a separator
    st.markdown("""<hr style="height:2px;border:none;color:#333;background-color:#333;" />""", unsafe_allow_html=True)

    return selected

# Helper function for creating formatted section titles
def section_title(title, icon=""):
    """Creates a consistently formatted section title."""
    st.markdown(f"## {icon} {title}", unsafe_allow_html=True)
    st.markdown("---")
