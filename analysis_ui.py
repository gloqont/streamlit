import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
from events import log_event

def analyze_decision(text, portfolio):
    text = text.lower()
    for asset in portfolio["Asset"]:
        if asset.lower() in text:
            return asset
    for region in portfolio["Region"].unique():
        if region.lower() in text:
            return region
    return "Macro / Multi-Asset"

def consequence_engine(target, magnitude, portfolio, mode):
    if target in portfolio["Asset"].values:
        w = portfolio.loc[portfolio["Asset"] == target, "Weight (%)"].iloc[0]
    elif target in portfolio["Region"].values:
        w = portfolio.loc[portfolio["Region"] == target, "Weight (%)"].sum()
    else:
        w = 18.0

    base_risk = w / 8
    size_boost = 1 + magnitude / 18
    rm = base_risk * size_boost

    worst = -rm * 2.4
    best = rm * 1.2
    expected = (worst + best) / 2

    if "Reflexive" in mode:
        break_time, unit = max(2, int(35 / rm)), "minutes"
    else:
        break_time, unit = max(5, int(55 / rm)), "months"

    return {
        "weight": round(w, 2),
        "multiplier": round(rm, 1),
        "worst": round(worst, 2),
        "best": round(best, 2),
        "expected": round(expected, 2),
        "break_time": break_time,
        "unit": unit,
        "block": rm > 6 or break_time <= 4
    }

def show_analysis():
    portfolio = st.session_state.user_portfolio
    total_value = portfolio["Value"].sum()

    st.title("GLOQONT")
    st.caption("What happens to your portfolio if you do this?")

    st.dataframe(portfolio, use_container_width=True)

    mode = st.radio(
        "Decision Context",
        ["Reflexive Mode (short-term)", "Compounding Mode (long-term)"],
        horizontal=True
    )

    with st.form("decision"):
        decision = st.text_input("What decision are you about to make?")
        magnitude = st.slider("Decision Size (%)", 1, 30, 5)
        submit = st.form_submit_button("Show Consequences")

    if submit and decision:
        log_event("simulation_run", {"decision": decision})
        target = analyze_decision(decision, portfolio)
        c = consequence_engine(target, magnitude, portfolio, mode)

        if c["block"]:
            st.error("DO NOT EXECUTE — irreversible downside risk")
        else:
            st.warning("Risk increases materially")

        st.metric("Downside Amplification", f"{c['multiplier']}×")
        st.metric("Time-to-Damage", f"{c['break_time']} {c['unit']}")

        st.table(pd.DataFrame({
            "Scenario": ["Worst", "Best"],
            "Impact (%)": [c["worst"], c["best"]]
        }))
