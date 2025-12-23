import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
import random
import json
import os

# ================= CONFIG =================
st.set_page_config(page_title="GLOQONT", layout="centered")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ================= HELPERS =================
def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def random_price(base, vol=0.05):
    return round(base * (1 + np.random.uniform(-vol, vol)), 2)

def ledger_path(team):
    return os.path.join(DATA_DIR, f"{team}_ledger.json")

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

# ================= TEAM / USER =================
st.title("GLOQONT")
st.caption("Decision intelligence with memory")

team = st.text_input("Team / Fund Name", value="DemoFund")
member = st.text_input("Decision Maker", value="PM-1")

# ================= LEDGER =================
def load_ledger():
    path = ledger_path(team)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_decision(d):
    ledger = load_ledger()
    ledger.append(d)
    with open(ledger_path(team), "w") as f:
        json.dump(ledger, f, indent=2)

# ================= PORTFOLIO VIEW =================
st.markdown("## 💼 Portfolio Snapshot")

st.metric(
    "Total Portfolio Value",
    f"${total_value:,.0f}",
    f"{pnl_pct}% ({'+' if pnl_val>=0 else ''}${pnl_val:,.0f})"
)

st.dataframe(portfolio, use_container_width=True)

# ================= MODE =================
mode = st.radio("Operating Mode", ["Trader Mode", "Investor Mode"], horizontal=True)

# ================= DECISION =================
with st.form("decision"):
    decision_type = st.selectbox(
        "Decision Type",
        ["Trade Decision", "Portfolio Action", "Macro Event", "Shock Scenario"]
    )

    decision_text = st.text_input(
        "What are you about to do?",
        placeholder="Buy NVDA +5%, Sell BTC, Reduce India exposure"
    )

    magnitude = st.slider("Decision size (%)", 1, 30, 5)
    submit = st.form_submit_button("Analyze Decision")

# ================= DECISION ANALYSIS =================
def analyze_decision(text):
    text = text.lower()
    for asset in portfolio["Asset"]:
        if asset.lower() in text:
            return asset
    for region in portfolio["Region"].unique():
        if region.lower() in text:
            return region
    return "Macro"

def consequence_engine(hit, magnitude):
    if hit in portfolio["Asset"].values:
        w = portfolio.loc[portfolio["Asset"] == hit, "Weight (%)"].iloc[0]
    elif hit in portfolio["Region"].values:
        w = portfolio.loc[portfolio["Region"] == hit, "Weight (%)"].sum()
    else:
        w = 15

    base_risk = w / 10
    risk = base_risk * (1 + magnitude / 20)

    return {
        "exposure": round(w, 2),
        "risk_mult": round(risk, 2),
        "worst": round(-risk * 2.5, 2),
        "best": round(risk * 1.3, 2),
        "break_time": int(40 / risk) if mode == "Trader Mode" else int(60 / risk),
        "unit": "minutes" if mode == "Trader Mode" else "days",
    }

# ================= OUTPUT =================
if submit and decision_text:

    hit = analyze_decision(decision_text)
    c = consequence_engine(hit, magnitude)

    st.markdown("## 🔴 Decision Consequences")

    st.metric("Portfolio exposure affected", f"{c['exposure']}%")
    st.metric("How much worse losses become", f"{c['risk_mult']}×")

    st.table(pd.DataFrame({
        "Scenario": ["Worst case", "Best case"],
        "Portfolio impact (%)": [c["worst"], c["best"]]
    }))

    st.metric("How fast things break", f"{c['break_time']} {c['unit']}")

    # ================= SAVE DECISION =================
    decision = {
        "time": now(),
        "team": team,
        "member": member,
        "decision": decision_text,
        "hit": hit,
        "mode": mode,
        "portfolio_value": total_value,
        "impact": c,
    }
    save_decision(decision)

# ================= LIVE P&L REPLAY =================
st.markdown("## 🔁 Decision Replay & Learning")

ledger = load_ledger()

if ledger:
    df = pd.DataFrame(ledger)
    df["Δ Portfolio ($)"] = total_value - df["portfolio_value"]

    st.dataframe(
        df[["time", "member", "decision", "hit", "mode", "Δ Portfolio ($)"]],
        use_container_width=True
    )
else:
    st.info("No decisions yet.")

# ================= SKILL SCORE =================
st.markdown("## 🎯 Decision Skill Insights")

if ledger:
    skill = {}
    for d in ledger:
        key = d["hit"]
        skill.setdefault(key, []).append(abs(d["impact"]["worst"]))

    skill_df = pd.DataFrame(
        [(k, round(100 - np.mean(v) * 5, 1)) for k, v in skill.items()],
        columns=["Asset / Region", "Skill Score (0–100)"]
    )

    st.bar_chart(skill_df.set_index("Asset / Region"))
else:
    st.info("Skill scores will appear after decisions.")
