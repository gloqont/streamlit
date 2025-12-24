import streamlit as st
import pandas as pd
from datetime import datetime
from events import log_event

def show_portfolio_entry():
    st.title(f"Welcome, {st.session_state.user_name}")
    st.markdown("### Enter Your Portfolio")

    if "portfolio_entries" not in st.session_state:
        st.session_state.portfolio_entries = []

    with st.form("add_position", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)

        asset = col1.text_input("Asset / Ticker")
        qty = col2.number_input("Quantity", min_value=0.0001, value=1.0)
        price = col3.number_input("Price (USD)", min_value=0.01, value=100.0)

        col4, col5 = st.columns(2)
        region = col4.selectbox("Region", ["USA", "India", "Europe", "Global", "Other"])
        cls = col5.selectbox("Asset Class", ["Equity", "Crypto", "Other"])

        add = st.form_submit_button("Add Position")

        if add and asset:
            st.session_state.portfolio_entries.append({
                "Asset": asset.upper(),
                "Region": region,
                "Class": cls,
                "Quantity": qty,
                "Price": price
            })
            log_event("position_added", {"asset": asset})

    if st.session_state.portfolio_entries:
        df = pd.DataFrame(st.session_state.portfolio_entries)
        df["Value"] = df["Quantity"] * df["Price"]
        total = df["Value"].sum()
        df["Weight (%)"] = (df["Value"] / total * 100).round(2)

        st.markdown("### Portfolio Preview")
        st.dataframe(df, use_container_width=True)

        if st.button("Confirm Portfolio & Continue"):
            if len(df) < 2:
                st.error("Add at least 2 positions")
            else:
                st.session_state.user_portfolio = df
                st.session_state.portfolio_entered = True
                log_event("portfolio_confirmed", {
                    "positions": len(df),
                    "total_value": float(total),
                    "time_spent": (datetime.utcnow() - st.session_state.session_start).seconds
                })
                st.rerun()

    else:
        st.info("No positions yet")

    st.markdown("---")
    if st.button("Use Demo Portfolio Instead"):
        demo = [
            {"Asset": "AAPL", "Region": "USA", "Class": "Equity", "Quantity": 120, "Price": 190},
            {"Asset": "MSFT", "Region": "USA", "Class": "Equity", "Quantity": 80, "Price": 420},
            {"Asset": "NVDA", "Region": "USA", "Class": "Equity", "Quantity": 40, "Price": 1150},
            {"Asset": "BTC", "Region": "Global", "Class": "Crypto", "Quantity": 1.2, "Price": 65000},
        ]
        df = pd.DataFrame(demo)
        df["Value"] = df["Quantity"] * df["Price"]
        df["Weight (%)"] = (df["Value"] / df["Value"].sum() * 100).round(2)

        st.session_state.user_portfolio = df
        st.session_state.portfolio_entered = True
        log_event("demo_portfolio_selected")
        st.rerun()
