import streamlit as st

def event_card(event_name, event_date, link):
    st.markdown(f"""
        <div style="border: 2px solid #f1c40f; padding: 10px; margin: 10px; text-align: center;">
            <h3>{event_name}</h3>
            <p>{event_date}</p>
            <a href="{link}"><button>View Event</button></a>
        </div>
        """, unsafe_allow_html=True)
