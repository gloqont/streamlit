import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
import random
import re

# ================= CONFIG =================
st.set_page_config(page_title="GLOQONT", layout="centered")

# ================= SESSION MEMORY =================
if "decision_log" not in st.session_state:
    st.session_state.decision_log = []

# ================= HELPERS =================
def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def random_price(base, vol=0.05):
    return round(base * (1 + np.random.uniform(-vol, vol)), 2)

# ================= RANDOM PORTFOLIO =================
@st.cache_data
def generate_portfolio():
    assets = [
        ("AAPL", "USA", "Equity", 190),
        ("MSFT", "USA", "Equity", 420),
        ("NVDA", "USA", "Equity", 1150),
        ("SHOP", "Canada", "Equity", 75),
        ("TD", "Canada", "Equity", 63),
        ("SAP", "Europe", "Equity", 185),
        ("ASML", "Europe", "Equity", 920),
        ("RELIANCE", "India", "Equity", 2900),
        ("TCS", "India", "Equity", 3900),
        ("BTC", "Global", "Crypto", 65000),
    ]

    rows = []
    for a, region, cls, base in assets:
        qty = round(np.random.uniform(2, 25), 2) if a == "BTC" else random.randint(5, 120)
        price = random_price(base)
        value = qty * price
        rows.append([a, region, cls, qty, price, value])

    df = pd.DataFrame(
        rows,
        columns=["Asset", "Region", "Class", "Quantity", "Price", "Value"]
    )

    total = df["Value"].sum()
    df["Weight (%)"] = (df["Value"] / total * 100).round(2)

    pnl_pct = round(np.random.uniform(-1.5, 1.5), 2)
    pnl_val = round(total * pnl_pct / 100, 2)

    return df, total, pnl_pct, pnl_val

portfolio, total_value, pnl_pct, pnl_val = generate_portfolio()

# ================= LANDING =================
st.title("GLOQONT")
st.caption("What happens to your portfolio if you do this?")

st.markdown("""
**GLOQONT is portfolio-aware decision intelligence.**  
Every answer is based on *your actual holdings*, not generic theory.
""")

# ================= PORTFOLIO VIEW =================
st.markdown("## 💼 Your Portfolio (Live Snapshot)")

st.metric(
    "Total Portfolio Value",
    f"${total_value:,.0f}",
    f"{pnl_pct}% ({'+' if pnl_val>=0 else ''}${pnl_val:,.0f})"
)

st.dataframe(portfolio, use_container_width=True)

# ================= MODE =================
mode = st.radio(
    "How do you operate?",
    ["Trader Mode", "Investor Mode"],
    horizontal=True
)

# ================= DECISION INPUT =================
with st.form("decision"):
    decision_type = st.selectbox(
        "Decision Type",
        ["Trade Decision", "Portfolio Action", "Macro Event", "Shock Scenario"]
    )

    decision_text = st.text_input(
        "What are you about to do?",
        placeholder="Buy NVDA +5%, Sell BTC, Reduce India exposure, Fed hikes 50bps"
    )

    magnitude = st.slider("Decision size (%)", 1, 30, 5)
    submit = st.form_submit_button("Show Consequences")

# ================= DECISION PARSER =================
def analyze_decision(text):
    text = text.lower()
    for asset in portfolio["Asset"]:
        if asset.lower() in text:
            return asset
    if "india" in text:
        return "India"
    if "usa" in text or "us " in text:
        return "USA"
    if "crypto" in text or "btc" in text:
        return "BTC"
    return None

# ================= CONSEQUENCE ENGINE =================
def consequence_engine(asset_hit, magnitude):
    if asset_hit in portfolio["Asset"].values:
        w = portfolio.loc[portfolio["Asset"] == asset_hit, "Weight (%)"].iloc[0]
    elif asset_hit in portfolio["Region"].values:
        w = portfolio.loc[portfolio["Region"] == asset_hit, "Weight (%)"].sum()
    else:
        w = 15

    base_risk = w / 10
    size_boost = 1 + magnitude / 20
    risk = base_risk * size_boost

    worst = -risk * 2.5
    best = risk * 1.3

    if mode == "Trader Mode":
        break_time = max(3, int(40 / risk))
        unit = "minutes"
    else:
        break_time = max(7, int(50 / risk))
        unit = "days"

    auto_block = risk > 6 or break_time <= 5

    return {
        "weight": round(w, 2),
        "worst": round(worst, 2),
        "best": round(best, 2),
        "expected": round((worst + best) / 2, 2),
        "multiplier": round(risk, 1),
        "break_time": break_time,
        "unit": unit,
        "block": auto_block
    }

# ================= OUTPUT =================
if submit and decision_text.strip():

    hit = analyze_decision(decision_text)
    c = consequence_engine(hit, magnitude)

    st.markdown("## 🔴 Decision Consequences")

    if c["block"]:
        st.error("🚫 DO NOT TRADE THIS — downside accelerates beyond control")
    else:
        st.warning("⚠️ Elevated risk — proceed only with strict discipline")

    st.markdown(f"""
    **What you are impacting:** `{hit or 'Multiple assets / macro'}`  
    **Portfolio exposure affected:** **{c['weight']}%**
    """)

    st.metric("How much worse losses become", f"{c['multiplier']}×")

    st.markdown("### 📊 Portfolio Impact")

    st.table(pd.DataFrame({
        "Scenario": ["Worst case", "Best case"],
        "Portfolio change (%)": [c["worst"], c["best"]]
    }))

    st.markdown("### ⏱️ How fast things break")

    st.metric("Damage accelerates in", f"{c['break_time']} {c['unit']}")

    st.markdown("### 🧠 Explain it simply")

    if mode == "Trader Mode":
        st.success("If this goes wrong, losses stack up faster than you can fix them.")
    else:
        st.success("If this goes wrong, bad years become much harder to recover from.")

    # ===== STORE DECISION FOR REPLAY =====
    realized = round(c["expected"] * np.random.uniform(0.4, 1.6), 2)

    st.session_state.decision_log.append({
        "time": now(),
        "decision": decision_text,
        "asset": hit or "Macro",
        "mode": mode,
        "expected_pct": c["expected"],
        "realized_pct": realized,
        "portfolio_value": total_value
    })

# ================= LIVE P&L REPLAY =================
st.markdown("## 🔁 Live P&L Replay")

if st.session_state.decision_log:

    df = pd.DataFrame(st.session_state.decision_log)

    df["Expected P&L ($)"] = (df["portfolio_value"] * df["expected_pct"] / 100).round(0)
    df["Realized P&L ($)"] = (df["portfolio_value"] * df["realized_pct"] / 100).round(0)

    st.dataframe(
        df[["time", "decision", "asset", "Expected P&L ($)", "Realized P&L ($)"]],
        use_container_width=True
    )

else:
    st.info("No decisions yet.")

# ================= SKILL SCORE =================
st.markdown("## 🎯 Decision Skill Score")

if len(st.session_state.decision_log) >= 2:

    df = pd.DataFrame(st.session_state.decision_log)
    df["error"] = abs(df["expected_pct"] - df["realized_pct"])

    skill = (
        df.groupby("asset")["error"]
        .mean()
        .apply(lambda x: max(0, 100 - x * 20))
        .round(0)
        .reset_index()
        .rename(columns={"error": "Skill Score"})
    )

    st.dataframe(skill, use_container_width=True)

    st.markdown("""
    **How to read this:**  
    - **80–100** → well-calibrated judgment  
    - **60–80** → sizing / timing issues  
    - **<60** → repeated misjudgment  

    This measures **decision accuracy**, not returns.
    """)

else:
    st.info("Skill scores appear after multiple decisions.")
