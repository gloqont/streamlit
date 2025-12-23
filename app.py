import streamlit as st
from uuid import uuid4
from datetime import datetime
import json
import os

# ================= CONFIG =================
st.set_page_config(page_title="GLOQONT", layout="centered")

LEDGER_FILE = "decision_ledger.json"

# ================= SESSION STATE =================
if "decision" not in st.session_state:
    st.session_state.decision = None
if "decision_committed" not in st.session_state:
    st.session_state.decision_committed = False
if "decision_aborted" not in st.session_state:
    st.session_state.decision_aborted = False

# ================= LEDGER =================
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

# ================= LOGIC =================
def compute_consequences(decision):
    positions = decision["portfolio"]["positions"]
    leverage = decision["portfolio"]["leverage"]

    equity_weight = sum(
        p["weight"] for p in positions if p["class"] in ["Equity", "Crypto"]
    )

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

# ================= RENDER =================
st.title("GLOQONT")

# ================= ABORTED =================
if st.session_state.decision_aborted:
    st.error("Decision aborted. No analysis shown.")
    if st.button("Start new decision"):
        st.session_state.clear()
    st.stop()

# ================= DECISION GATE =================
if not st.session_state.decision_committed:

    st.markdown(
        """
        ### Before capital moves, stop.

        Most investors lose money **not because of bad ideas**,  
        but because they **don’t see consequences before acting**.

        GLOQONT forces that moment.
        """
    )

    st.markdown("## What are you about to do?")

    with st.form("decision_form"):
        intent = st.selectbox(
            "Decision",
            ["Increase exposure", "Decrease exposure", "Exit position"]
        )
        asset = st.text_input("Asset / Ticker", placeholder="e.g. NVDA, BTC")
        magnitude = st.number_input("Change in exposure (%)", 0.0, 100.0, 5.0)
        horizon = st.selectbox("Time horizon", ["7 days", "30 days", "90 days"])
        submitted = st.form_submit_button("Continue")

    if submitted:
        st.session_state.decision = {
            "id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "intent": intent,
            "asset": asset,
            "magnitude": magnitude,
            "horizon": horizon,
        }

    if st.session_state.decision:
        st.markdown("## What does this decision affect?")

        portfolio = st.data_editor(
            [
                {"asset": "AAPL", "weight": 30.0, "class": "Equity"},
                {"asset": "MSFT", "weight": 25.0, "class": "Equity"},
                {"asset": "BTC", "weight": 15.0, "class": "Crypto"},
                {"asset": "Cash", "weight": 30.0, "class": "Cash"},
            ],
            num_rows="dynamic",
            use_container_width=True,
        )

        leverage = st.checkbox("Portfolio uses leverage")

        st.session_state.decision["portfolio"] = {
            "positions": portfolio,
            "leverage": leverage,
        }

        st.markdown("## What breaks if this goes wrong?")

        consequences = compute_consequences(st.session_state.decision)
        for k, v in consequences.items():
            st.write(f"**{k}**: {v}")

        st.markdown(
            "_These are not predictions. They are fragilities this decision introduces._"
        )

        st.markdown("## What must stay true for this to work?")

        assumptions = derive_assumptions(consequences)
        for a in assumptions:
            st.warning(a)

        ack = st.checkbox("I understand this decision depends on these assumptions.")
        weakest = st.selectbox("Weakest assumption", assumptions)

        choice = st.radio(
            "Knowing this, what do you choose?",
            ["Proceed with decision", "Abort decision"]
        )

        if choice == "Abort decision":
            st.session_state.decision_aborted = True
            st.session_state.decision["commitment"] = {
                "action": "abort",
                "weakest_assumption": weakest,
            }
            save_to_ledger(st.session_state.decision)
            st.rerun()


        if choice == "Proceed with decision" and ack:
            st.session_state.decision_committed = True
            st.session_state.decision["commitment"] = {
                "action": "proceed",
                "weakest_assumption": weakest,
            }
            save_to_ledger(st.session_state.decision)
            st.rerun()


    st.stop()

# ================= POST-DECISION INTELLIGENCE =================
if st.session_state.decision is None:
    st.error("No decision found in session. Please start again.")
    if st.button("Start new decision"):
        st.session_state.clear()
    st.stop()

st.success("Decision committed. Intelligence unlocked.")

st.markdown("## Decision Impact Overview")
st.write(
    f"""
    **Decision:** {st.session_state.decision['intent']}  
    **Asset:** {st.session_state.decision['asset']}  
    **Magnitude:** {st.session_state.decision['magnitude']}%  
    **Horizon:** {st.session_state.decision['horizon']}
    """
)

st.info(
    "This is where your existing dashboards, risk models, and simulations plug in — "
    "**all scoped to this decision.**"
)

st.markdown("## Decision Ledger")
for d in reversed(load_ledger()):
    st.write(
        f"- **{d['intent']} {d['asset']} ({d['magnitude']}%)** → {d['commitment']['action']}"
    )
