import streamlit as st
import numpy as np
import pandas as pd
import json
import os
from uuid import uuid4
from datetime import datetime, timedelta

# ================= CONFIG =================
st.set_page_config(
    page_title="GLOQONT — Decision Intelligence",
    layout="centered"
)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ================= UTILITIES =================
def now():
    return datetime.utcnow().isoformat()

def user_file(user_id):
    return os.path.join(DATA_DIR, f"{user_id}_ledger.json")

def safe_get(d, k, default=None):
    return d[k] if k in d else default

# ================= USER SYSTEM =================
st.title("GLOQONT")
st.caption("Decision → Consequence → Memory")

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if not st.session_state.user_id:
    st.markdown("### Identify yourself")
    user = st.text_input("User ID / Email (demo-safe)", placeholder="investor@fund.com")
    if st.button("Enter"):
        st.session_state.user_id = user.strip().lower()
        st.rerun()
    st.stop()

USER_ID = st.session_state.user_id

# ================= LEDGER =================
def load_ledger():
    path = user_file(USER_ID)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        ledger = json.load(f)

    # --- schema hardening ---
    for d in ledger:
        d.setdefault("type", "Decision")
        d.setdefault("outcome", "pending")
        d.setdefault("realized_return", None)
        d.setdefault("quality_score", None)

    return ledger

def save_ledger(ledger):
    with open(user_file(USER_ID), "w") as f:
        json.dump(ledger, f, indent=2)

def append_decision(d):
    ledger = load_ledger()
    ledger.append(d)
    save_ledger(ledger)

# ================= CORE ENGINE =================
def simulate_distribution(vol, magnitude, n=5000):
    shock = magnitude / 100
    rets = np.random.normal(0, vol * (1 + shock), n)
    return np.percentile(rets, [5, 50, 95])

def regime_matrix(vol, magnitude):
    shock = magnitude / 100
    return {
        "Risk-On": (vol * 0.6, vol * 0.6 * (1 + shock)),
        "Risk-Off": (vol * 1.2, vol * 1.2 * (1 + shock * 2)),
        "Vol Spike": (vol * 1.6, vol * 1.6 * (1 + shock * 3)),
    }

def score_decision(expected, realized):
    if realized is None:
        return None
    error = abs(realized - expected)
    if error < 0.01:
        return 95
    if error < 0.03:
        return 80
    if error < 0.06:
        return 60
    return 30

# ================= DECISION CREATION =================
st.markdown("## 1️⃣ Define the Decision")

with st.form("decision_form"):
    d_type = st.selectbox(
        "Decision Type",
        ["Trade", "Portfolio Action", "Macro Event", "Shock Scenario"]
    )

    intent = st.text_input(
        "Decision",
        placeholder="Buy NVDA +5%, Reduce equity −10%, Fed hikes 50bps"
    )

    magnitude = st.slider("Impact magnitude (%)", 1, 50, 10)
    horizon = st.selectbox("Horizon", ["7 days", "30 days", "90 days"])

    submit = st.form_submit_button("Simulate Consequences")

if submit:
    decision = {
        "id": str(uuid4()),
        "timestamp": now(),
        "type": d_type,
        "intent": intent,
        "magnitude": magnitude,
        "horizon": horizon,
    }

    # ===== Portfolio Context =====
    portfolio = [
        {"asset": "AAPL", "weight": 30, "class": "Equity"},
        {"asset": "MSFT", "weight": 25, "class": "Equity"},
        {"asset": "BTC", "weight": 15, "class": "Crypto"},
        {"asset": "Cash", "weight": 30, "class": "Cash"},
    ]

    equity_weight = sum(p["weight"] for p in portfolio if p["class"] == "Equity")
    base_vol = 0.012 + equity_weight / 2000

    p5, p50, p95 = simulate_distribution(base_vol, magnitude)
    regimes = regime_matrix(base_vol, magnitude)

    decision["expected"] = {
        "p5": p5,
        "median": p50,
        "p95": p95,
        "regimes": regimes,
    }

    decision["summary"] = {
        "left_tail_multiplier": round(abs(p5) / base_vol, 2),
        "expected_return": round(p50 * 100, 2),
        "recovery_days": int(15 + magnitude * 2),
    }

    decision["outcome"] = "committed"
    append_decision(decision)
    st.success("Decision recorded. Memory updated.")

# ================= DECISION MEMORY =================
st.markdown("## 2️⃣ Decision Memory")

ledger = load_ledger()

if not ledger:
    st.info("No decisions yet.")
    st.stop()

df = pd.DataFrame([
    {
        "Time": d["timestamp"][:19],
        "Decision": d["intent"],
        "Expected %": d["summary"]["expected_return"],
        "Realized %": d["realized_return"],
        "Quality": d["quality_score"],
    }
    for d in ledger
])

st.dataframe(df, use_container_width=True)

# ================= OUTCOME UPDATE =================
st.markdown("## 3️⃣ Record Realized Outcome")

pending = [d for d in ledger if d["realized_return"] is None]

if pending:
    d_map = {d["id"]: d for d in pending}
    sel = st.selectbox(
        "Select decision",
        options=list(d_map.keys()),
        format_func=lambda x: d_map[x]["intent"]
    )

    realized = st.number_input("Realized return (%)", -50.0, 50.0, 0.0)

    if st.button("Update Outcome"):
        d = d_map[sel]
        d["realized_return"] = realized
        d["quality_score"] = score_decision(
            d["summary"]["expected_return"] / 100,
            realized / 100
        )
        save_ledger(ledger)
        st.success("Outcome recorded. Decision quality updated.")
        st.rerun()
else:
    st.info("All decisions have realized outcomes.")

# ================= INSIGHT =================
st.markdown("## 4️⃣ Decision Quality Intelligence")

scored = [d for d in ledger if d["quality_score"] is not None]

if scored:
    avg_quality = int(np.mean([d["quality_score"] for d in scored]))
    st.metric("Average Decision Quality", f"{avg_quality}/100")

    st.markdown(
        """
        **Interpretation**
        - >80: Decisions are well-calibrated
        - 60–80: Risk understood, timing noisy
        - <60: Systematic misjudgment detected
        """
    )
else:
    st.info("No scored decisions yet.")

# ================= FINAL MESSAGE =================
st.markdown("---")
st.markdown(
    """
    **GLOQONT is not a prediction tool.**

    It is a **decision memory system** that:
    - Exposes downside before action
    - Records intent, assumptions, and outcomes
    - Learns where judgment breaks

    This is how capital allocation becomes accountable.
    """
)
