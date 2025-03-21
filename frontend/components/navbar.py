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
            margin-bottom: 15px;
        }
        .nav-button {
            background-color: #e10600; color: white; font-weight: bold;
            border: none; border-radius: 5px; padding: 10px 20px;
            cursor: pointer;
        }
        .nav-button:hover {
            background-color: #b80500;
        }
        .nav-button-selected {
            background-color: #b80500; color: white; font-weight: bold;
            border: none; border-radius: 5px; padding: 10px 20px;
            cursor: pointer;
        }
    </style>
    """, unsafe_allow_html=True)

    # Create HTML for navigation bar
    nav_html = '<div class="nav-container">'
    
    selected = None
    for label, page in nav_items.items():
        # Check if this is the currently selected page
        button_class = "nav-button-selected" if page == st.session_state["current_page"] else "nav-button"
        
        # Add button with unique key
        button_id = f"nav_btn_{page.replace(' ', '_')}"
        nav_html += f'<button class="{button_class}" id="{button_id}" onclick="setPage(\'{page}\')">{label}</button>'
    
    nav_html += '</div>'
    
    # JavaScript to handle button clicks
    js = """
    <script>
    function setPage(page) {
        // Update session state via form submission
        const data = new FormData();
        data.append('current_page', page);
        fetch('/', {
            method: 'POST',
            body: data
        }).then(() => {
            // Reload page to reflect change
            window.location.reload();
        });
    }
    </script>
    """
    
    # Combine HTML and JavaScript
    st.markdown(nav_html + js, unsafe_allow_html=True)
    
    # Create individual buttons as fallback for the JavaScript method
    cols = st.columns(len(nav_items))
    for idx, (label, page) in enumerate(nav_items.items()):
        if cols[idx].button(label, key=f"nav_{page}", help=f"Navigate to {page}"):
            selected = page

    # If a button was clicked, update the session state
    if selected:
        st.session_state["current_page"] = selected
        st.rerun()  # Force page to rerun with new selection
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