import streamlit as st
from datetime import datetime

def log_event(event_type, data=None):
    if "event_log" not in st.session_state:
        st.session_state.event_log = []

    st.session_state.event_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "user_email": st.session_state.get("user_email"),
        "event": event_type,
        "data": data or {}
    })
