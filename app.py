import streamlit as st
from datetime import datetime
import re

from portfolio_ui import show_portfolio_entry
from analysis_ui import show_analysis

st.set_page_config(page_title="GLOQONT", layout="centered")

# ---------- SESSION STATE ----------
for k, v in {
    "authenticated": False,
    "user_email": "",
    "user_name": "",
    "portfolio_entered": False,
    "session_start": datetime.utcnow()
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def valid_email(e):
    return re.match(r"[^@]+@[^@]+\.[^@]+", e)

# ---------- LOGIN ----------
def show_login():
    st.title("GLOQONT")
    st.markdown("### See consequences before committing capital")

    with st.form("login"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        go = st.form_submit_button("Continue")

        if go:
            if not name or not valid_email(email):
                st.error("Enter valid name and email")
            else:
                st.session_state.user_name = name
                st.session_state.user_email = email
                st.session_state.authenticated = True
                st.session_state.session_start = datetime.utcnow()
                st.rerun()

# ---------- ROUTER ----------
if not st.session_state.authenticated:
    show_login()
elif not st.session_state.portfolio_entered:
    show_portfolio_entry()
else:
    show_analysis()
