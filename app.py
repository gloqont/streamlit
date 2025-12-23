import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import json
import os
from datetime import datetime
from uuid import uuid4

# ================= CONFIG =================
st.set_page_config(page_title="GLOQONT", layout="centered")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ================= UTIL =================
def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def user_file(uid):
    return os.path.join(DATA_DIR, f"{uid}.json")

def safe_get(d, k, default=None):
    return d[k] if k in d else default

# ================= USER =================
st.title("GLOQONT")
st.caption("Decision → Consequence → Memory")

if "uid" not in st.session_state:
    st.session_state.uid = None

if not st.session_state.uid:
    uid = st.text_input("User ID / Email (demo-safe)")
    if st.button("Enter"):
        st.session_state.uid = uid.lower().strip()
        st.rerun()
    st.stop()

UID = st.session_state.uid

# ================= LEDGER =================
def load_ledger():
    path = user_file(UID)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_ledger(ledger):
    with open(user_file(UID), "w") as f:
        json.dump(ledger, f, indent=2)

# ================= MARKET DATA =================
def get_market_volatility():
    try:
        vix = yf.download("^VIX", period="5d", interval="1d", progress=False)
        return float(vix["Close"].iloc[-1]) / 100
    except Exception:
        return 0.18  # fallback

# ================= ENGINE =================
def consequence_engine(mode, text, magnitude, market_vol):
    concentration = 1.4 if any(x in text.lower() for x in ["nvda", "all", "single"]) else 1
    size = 1 + magnitude / 20
    vol_boost = 1 + market_vol

    risk = concentration * size * vol_boost

    worst = -risk * 2.5
    typical = 1 / risk
    best = risk * 1.2

    if mode == "Trader Mode":
        break_time = max(3, int(45 / risk))
        irreversible = max(1, int(break_time / 3))
        unit = "minutes"
    else:
        break_time = max(5, int(60 / risk))
        irreversible = max(2, int(break_time / 2))
        unit = "days"

    auto_block = (
        risk > 3.5 or break_time <= 5 or market_vol > 0.3
    )

    return {
        "distribution": (worst, typical, best),
        "multiplier": round(abs(worst), 1),
        "break_time": break_time,
        "irreversible": irreversible,
        "unit": unit,
        "auto_block": auto_block,
        "market_vol": round(market_vol * 100, 1),
    }

# ================= LANDING =================
st.markdown("""
### For Traders  
You lose when things break **faster than you can react**.

### For Investors  
You lose when bad years become **unrecoverable**.

**GLOQONT shows both — before you act.**
""")

mode = st.radio("Mode", ["Trader Mode", "Investor Mode"], horizontal=True)

# ================= DECISION =================
with st.form("decision"):
    decision_text = st.text_input(
        "What are you about to do?",
        placeholder="Buy NVDA +5%, Short BTC, Reduce equity −10%"
    )
    magnitude = st.slider("Decision size (%)", 1, 30, 5)
    submit = st.form_submit_button("Analyze")

# ================= ANALYSIS =================
if submit and decision_text:
    market_vol = get_market_volatility()
    c = consequence_engine(mode, decision_text, magnitude, market_vol)

    st.markdown("## 🔴 Consequence Summary")

    if c["auto_block"]:
        st.error("🚫 DO NOT TRADE THIS — downside accelerates faster than control")
    else:
        st.warning("⚠️ High risk — proceed only with strict controls")

    st.metric("Market stress (live)", f"{c['market_vol']}%")

    st.markdown("### 📊 Outcome Distribution")
    st.table(pd.DataFrame({
        "Scenario": ["Worst", "Typical", "Best"],
        "Impact (%)": c["distribution"]
    }))

    st.markdown("### ⏱️ How fast things break")
    st.metric("Damage accelerates in", f"{c['break_time']} {c['unit']}")

    st.markdown("### 🧨 Time to irreversible damage")
    st.progress(c["irreversible"] / c["break_time"])
    st.caption(
        f"After ~{c['irreversible']} {c['unit']}, exits no longer prevent major loss."
    )

    decision = {
        "id": str(uuid4()),
        "time": now(),
        "mode": mode,
        "text": decision_text,
        "magnitude": magnitude,
        "analysis": c,
    }

    ledger = load_ledger()
    ledger.append(decision)
    save_ledger(ledger)

# ================= REPLAY =================
st.markdown("## 🔁 Replay Past Decisions")

ledger = load_ledger()

if ledger:
    ids = {d["id"]: d for d in ledger}
    sel = st.selectbox(
        "Select decision",
        options=list(ids.keys()),
        format_func=lambda x: ids[x]["text"]
    )

    d = ids[sel]
    st.markdown(f"**Decision:** {d['text']}")
    st.markdown(f"**When:** {d['time']}")
    st.markdown(f"**Mode:** {d['mode']}")

    st.markdown("### Consequences at the time")
    st.json(d["analysis"])
else:
    st.info("No past decisions yet.")

# ================= FOOTER =================
st.markdown("""
---
**GLOQONT is not a trading tool.  
It is a decision-integrity system.**

It shows:
- how bad things get  
- how fast they break  
- when mistakes become permanent  

Before capital is committed.
""")
