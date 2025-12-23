import streamlit as st
import numpy as np
import pandas as pd
from uuid import uuid4
from datetime import datetime
import json
import os

# ================= CONFIG =================
st.set_page_config(page_title="GLOQONT — Decision Intelligence", layout="centered")

LEDGER_FILE = "decision_ledger.json"

# ================= SESSION STATE =================
if "decision" not in st.session_state:
    st.session_state.decision = None
if "committed" not in st.session_state:
    st.session_state.committed = False
if "aborted" not in st.session_state:
    st.session_state.aborted = False

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

# ================= CORE ENGINE =================
def simulate_distribution(base_vol, magnitude, n=5000):
    shock = magnitude / 100
    returns = np.random.normal(0, base_vol * (1 + shock), n)
    return np.percentile(returns, [5, 50, 95])

def regime_matrix(base_risk, magnitude):
    shock = magnitude / 100
    return {
        "Risk-On": (base_risk * 0.6, base_risk * 0.6 * (1 + shock)),
        "Risk-Off": (base_risk * 1.2, base_risk * 1.2 * (1 + shock * 2)),
        "Volatility Spike": (base_risk * 1.6, base_risk * 1.6 * (1 + shock * 3)),
    }

def compute_consequences(decision):
    positions = decision["portfolio"]
    magnitude = decision["magnitude"]

    equity_weight = sum(p["weight"] for p in positions if p["class"] == "Equity")
    base_vol = 0.012 + equity_weight / 2000

    p5, p50, p95 = simulate_distribution(base_vol, magnitude)

    attribution = {
        "Target Asset": round(0.6 + magnitude / 200, 2),
        "Correlation Increase": round(0.25, 2),
        "Liquidity Reduction": round(0.15, 2),
    }

    regimes = regime_matrix(base_vol, magnitude)

    return {
        "distribution": {
            "p5": p5,
            "p50": p50,
            "p95": p95,
        },
        "attribution": attribution,
        "regimes": regimes,
        "summary": {
            "left_tail_multiplier": round(abs(p5) / base_vol, 2),
            "recovery_days": int(15 + magnitude * 2),
        }
    }

# ================= UI =================
st.title("GLOQONT")
st.caption("Decision → Consequence Intelligence")

# ================= ABORTED =================
if st.session_state.aborted:
    st.error("Decision aborted. No capital committed.")
    if st.button("Start new decision"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# ================= DECISION INPUT =================
if not st.session_state.committed:

    st.markdown("""
    ### Before capital moves, stop.

    GLOQONT does not predict markets.  
    It exposes **what gets worse if you are wrong**.
    """)

    with st.form("decision_form"):
        decision_type = st.selectbox(
            "Decision Type",
            ["Trade Decision", "Portfolio Action", "Macro Event", "Shock Scenario"]
        )

        intent = st.text_input(
            "Decision",
            placeholder="e.g. Buy NVDA +5%, Reduce equities −10%, Fed hikes 50bps"
        )

        magnitude = st.slider("Impact magnitude (%)", 1, 50, 10)
        horizon = st.selectbox("Time horizon", ["7 days", "30 days", "90 days"])

        submit = st.form_submit_button("Analyze Consequences")

    if submit:
        st.session_state.decision = {
            "id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "type": decision_type,
            "intent": intent,
            "magnitude": magnitude,
            "horizon": horizon,
        }

    if st.session_state.decision:

        st.markdown("## Portfolio Context")

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

        st.session_state.decision["portfolio"] = portfolio

        # ================= CONSEQUENCES =================
        c = compute_consequences(st.session_state.decision)

        st.markdown("## ⚠️ Decision Impact Summary")

        st.error(
            f"""
            **If you act:**  
            • Worst-case outcome worsens by **{c['summary']['left_tail_multiplier']}×**  
            • Expected recovery time extends to **{c['summary']['recovery_days']} days**  
            • Downside accelerates under regime stress
            """
        )

        st.markdown("## Outcome Distribution (30-day)")

        dist_df = pd.DataFrame({
            "Scenario": ["5th percentile", "Median", "95th percentile"],
            "Return (%)": [
                round(c["distribution"]["p5"] * 100, 2),
                round(c["distribution"]["p50"] * 100, 2),
                round(c["distribution"]["p95"] * 100, 2),
            ]
        })
        st.table(dist_df)

        st.markdown("## What Drives the New Risk")

        attr_df = pd.DataFrame.from_dict(
            c["attribution"], orient="index", columns=["Share of New Downside"]
        )
        st.bar_chart(attr_df)

        st.markdown("## Regime Sensitivity")

        regime_rows = []
        for r, (base, shocked) in c["regimes"].items():
            regime_rows.append([
                r,
                round(base * 100, 2),
                round(shocked * 100, 2)
            ])

        regime_df = pd.DataFrame(
            regime_rows,
            columns=["Regime", "Do Nothing (%)", "If You Act (%)"]
        )
        st.table(regime_df)

        st.markdown("## Final Choice")

        weakest = st.selectbox(
            "Weakest assumption",
            ["Volatility remains contained", "Correlations remain stable", "Liquidity persists"]
        )

        choice = st.radio(
            "Knowing this, what do you do?",
            ["Proceed with decision", "Abort decision"]
        )

        if choice == "Abort decision":
            st.session_state.aborted = True
            st.session_state.decision["outcome"] = "aborted"
            st.session_state.decision["weakest_assumption"] = weakest
            save_to_ledger(st.session_state.decision)
            st.rerun()

        if choice == "Proceed with decision":
            st.session_state.committed = True
            st.session_state.decision["outcome"] = "committed"
            st.session_state.decision["weakest_assumption"] = weakest
            save_to_ledger(st.session_state.decision)
            st.rerun()

    st.stop()

# ================= POST DECISION =================
st.success("Decision committed. This outcome is now part of your decision history.")

st.markdown("## Decision Record")

d = st.session_state.decision
st.write(f"""
**Type:** {d['type']}  
**Decision:** {d['intent']}  
**Magnitude:** {d['magnitude']}%  
**Horizon:** {d['horizon']}  
**Weakest Assumption:** {d['weakest_assumption']}
""")

st.markdown("## Your Decision Ledger")

for d in reversed(load_ledger()):
    st.write(
        f"- **{d['type']}** — {d['intent']} → **{d['outcome']}**"
    )
