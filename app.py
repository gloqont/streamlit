import streamlit as st
from uuid import uuid4
from datetime import datetime
import json
import os

st.set_page_config(page_title="GLOQONT", layout="centered")

LEDGER_FILE = "decision_ledger.json"

def load_ledger():
    if not os.path.exists(LEDGER_FILE):
        return []
    with open(LEDGER_FILE, "r") as f:
        return json.load(f)

def save_to_ledger(entry):
    ledger = load_ledger()
    ledger.append(entry)
    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=2)

def compute_consequences(decision):
    positions = decision["portfolio_context"]["positions"]
    leverage = decision["portfolio_context"]["leverage"]

    equity_weight = sum(p["weight"] for p in positions if p["class"] in ["Equity", "Crypto"])

    return {
        "Concentration Risk": "High" if decision["magnitude"] > 10 else "Moderate",
        "Volatility Sensitivity": "Very High" if leverage else "High" if equity_weight > 60 else "Moderate",
        "Correlation Fragility": "High" if len([p for p in positions if p["class"] == "Equity"]) > 2 else "Moderate",
        "Regime Dependence": "Very High" if equity_weight > 70 else "Moderate",
    }

def derive_assumptions(c):
    a = []
    if c["Volatility Sensitivity"] in ["High", "Very High"]:
        a.append("Market volatility must remain stable.")
    if c["Correlation Fragility"] == "High":
        a.append("Asset correlations must not converge.")
    if c["Regime Dependence"] in ["High", "Very High"]:
        a.append("The current market regime must persist.")
    if c["Concentration Risk"] == "High":
        a.append("This position must perform with little margin for error.")
    return a

st.title("GLOQONT")
st.subheader("Decision intelligence before capital moves")

with st.form("decision"):
    intent = st.selectbox("Decision", ["Increase exposure", "Decrease exposure", "Exit position"])
    asset = st.text_input("Asset / Ticker")
    magnitude = st.number_input("Change (%)", 0.0, 100.0, 5.0)
    horizon = st.selectbox("Horizon", ["7d", "30d", "90d"])
    submitted = st.form_submit_button("Analyze decision")

if submitted:
    decision = {
        "id": str(uuid4()),
        "time": datetime.utcnow().isoformat(),
        "intent": intent,
        "asset": asset,
        "magnitude": magnitude,
        "horizon": horizon
    }

    st.markdown("### Portfolio context")
    portfolio = st.data_editor([
        {"asset": "AAPL", "weight": 30.0, "class": "Equity"},
        {"asset": "MSFT", "weight": 25.0, "class": "Equity"},
        {"asset": "BTC", "weight": 15.0, "class": "Crypto"},
        {"asset": "Cash", "weight": 30.0, "class": "Cash"},
    ], num_rows="dynamic")

    leverage = st.checkbox("Uses leverage")

    decision["portfolio_context"] = {
        "positions": portfolio,
        "leverage": leverage
    }

    consequences = compute_consequences(decision)
    st.markdown("### Consequences")
    for k, v in consequences.items():
        st.write(f"**{k}**: {v}")

    assumptions = derive_assumptions(consequences)
    st.markdown("### Hidden assumptions")
    for a in assumptions:
        st.warning(a)

    ack = st.checkbox("I acknowledge these assumptions")
    weakest = st.selectbox("Weakest assumption", assumptions)
    action = st.radio("Decision", ["Proceed", "Abort"])

    if ack:
        decision["commitment"] = {"action": action, "weakest": weakest}
        save_to_ledger(decision)
        st.success(f"Decision {action.lower()}ed and recorded")

st.markdown("### Decision Ledger")
for d in reversed(load_ledger()):
    st.write(f"- {d['intent']} {d['asset']} ({d['magnitude']}%) → {d['commitment']['action']}")
