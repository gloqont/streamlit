import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime

# ================= CONFIG =================
st.set_page_config(page_title="GLOQONT", layout="centered")

# ================= SESSION MEMORY =================
if "decision_log" not in st.session_state:
    st.session_state.decision_log = []

# ================= HELPERS =================
def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

# ================= CANONICAL DEMO PORTFOLIO =================
def load_demo_portfolio():
    rows = [
        ("AAPL", "USA", "Equity", 120, 190),
        ("MSFT", "USA", "Equity", 80, 420),
        ("NVDA", "USA", "Equity", 40, 1150),
        ("ASML", "Europe", "Equity", 25, 920),
        ("RELIANCE", "India", "Equity", 90, 2900),
        ("TCS", "India", "Equity", 60, 3900),
        ("BTC", "Global", "Crypto", 1.2, 65000),
    ]

    df = pd.DataFrame(rows, columns=["Asset", "Region", "Class", "Quantity", "Price"])
    df["Value"] = df["Quantity"] * df["Price"]
    total = df["Value"].sum()
    df["Weight (%)"] = (df["Value"] / total * 100).round(2)

    pnl_pct = 0.6
    pnl_val = round(total * pnl_pct / 100, 0)

    return df, total, pnl_pct, pnl_val

portfolio, total_value, pnl_pct, pnl_val = load_demo_portfolio()

# ================= LANDING =================
st.title("GLOQONT")
st.caption("What happens to your portfolio if you do this?")

st.markdown("""
GLOQONT is portfolio-aware decision intelligence.  
It does not predict prices. It reveals consequences before capital is committed.
""")

# ================= PORTFOLIO VIEW =================
st.markdown("## 💼 Portfolio Snapshot")

st.metric("Total Portfolio Value", f"${total_value:,.0f}", f"+{pnl_pct}% (${pnl_val:,.0f})")
st.dataframe(portfolio, use_container_width=True)

# ================= MODE =================
mode = st.radio(
    "Decision Context",
    ["Reflexive Mode (short-term, convex risk)", "Compounding Mode (long-term, drawdown risk)"],
    horizontal=True
)

# ================= DECISION INPUT =================
with st.form("decision"):
    decision_type = st.selectbox(
        "Decision Type",
        ["Trade Decision", "Portfolio Reallocation", "Macro Event", "Shock Scenario"]
    )
    decision_text = st.text_input(
        "What decision are you about to make?",
        placeholder="Buy NVDA +5%, Reduce India exposure, Fed hikes 50bps"
    )
    magnitude = st.slider("Decision Size / Intensity (%)", 1, 30, 5)
    submit = st.form_submit_button("Show Consequences")

# ================= DECISION PARSER =================
def analyze_decision(text):
    text = text.lower()
    for asset in portfolio["Asset"]:
        if asset.lower() in text:
            return asset
    for region in portfolio["Region"].unique():
        if region.lower() in text:
            return region
    if "crypto" in text or "btc" in text:
        return "BTC"
    return "Macro / Multi-Asset"

# ================= CONSEQUENCE ENGINE =================
def consequence_engine(target, magnitude):
    if target in portfolio["Asset"].values:
        w = portfolio.loc[portfolio["Asset"] == target, "Weight (%)"].iloc[0]
    elif target in portfolio["Region"].values:
        w = portfolio.loc[portfolio["Region"] == target, "Weight (%)"].sum()
    else:
        w = 18.0

    base_risk = w / 8
    size_boost = 1 + magnitude / 18
    risk_multiplier = base_risk * size_boost

    worst = -risk_multiplier * 2.4
    best = risk_multiplier * 1.2
    expected = (worst + best) / 2

    if "Reflexive" in mode:
        break_time = max(2, int(35 / risk_multiplier))
        unit = "minutes"
    else:
        break_time = max(5, int(55 / risk_multiplier))
        unit = "months"

    block = risk_multiplier > 6 or break_time <= 4

    return {
        "weight": round(w, 2),
        "worst": round(worst, 2),
        "best": round(best, 2),
        "expected": round(expected, 2),
        "multiplier": round(risk_multiplier, 1),
        "break_time": break_time,
        "unit": unit,
        "block": block
    }

# ================= OUTPUT =================
if submit and decision_text.strip():

    target = analyze_decision(decision_text)
    c = consequence_engine(target, magnitude)

    st.markdown("## 🔴 Decision Consequences")

    st.markdown("### 🟢 If You Do Nothing")
    st.markdown("• Portfolio risk remains unchanged\n• Expected drift: +0.6%\n• No acceleration of downside")

    st.markdown("### 🔴 If You Execute This Decision")

    if c["block"]:
        st.error("DO NOT EXECUTE — downside accelerates beyond recovery control")
    else:
        st.warning("Risk increases materially — execution requires discipline")

    st.markdown(f"Primary exposure impacted: {target}\n\nPortfolio weight affected: {c['weight']}%")
    st.metric("Downside amplification", f"{c['multiplier']}×")

    st.table(pd.DataFrame({
        "Scenario": ["Worst Case", "Best Case"],
        "Portfolio Change (%)": [c["worst"], c["best"]]
    }))

    observed = round(c["expected"] * np.random.uniform(0.5, 1.4), 2)

    st.session_state.decision_log.append({
        "time": now(),
        "decision": decision_text,
        "target": target,
        "expected_pct": c["expected"],
        "observed_pct": observed,
        "portfolio_value": total_value
    })

# ================= IRREVERSIBLE EXPOSURE TREND =================
st.markdown("## 📉 Irreversible Exposure Trend (Post-Decision)")

if len(st.session_state.decision_log) >= 2:
    df = pd.DataFrame(st.session_state.decision_log)

    IRREVERSIBLE_THRESHOLD = 4.5
    base_multiplier = 3.0

    base_irrev = portfolio["Weight (%)"][
        portfolio["Weight (%)"] * base_multiplier > IRREVERSIBLE_THRESHOLD
    ].sum()

    irrev_series = []

    for _, row in df.iterrows():
        approx_mult = abs(row["expected_pct"]) / max(1e-6, portfolio["Weight (%)"].mean())
        incr = portfolio["Weight (%)"].mean() if approx_mult > IRREVERSIBLE_THRESHOLD else 0.0
        irrev_series.append(min(100.0, base_irrev + incr))

    trend_df = pd.DataFrame({
        "Decision #": range(1, len(irrev_series) + 1),
        "Irreversible Exposure (%)": irrev_series
    })

    st.line_chart(trend_df.set_index("Decision #"), height=220)

# ================= IRREVERSIBLE EXPOSURE GUARDRAIL =================
st.markdown("## 🚧 Irreversible Exposure Guardrail")

if len(st.session_state.decision_log) >= 2:
    df = pd.DataFrame(st.session_state.decision_log)

    IRREVERSIBLE_THRESHOLD = 4.5
    base_multiplier = 3.0

    base_irrev = portfolio["Weight (%)"][
        portfolio["Weight (%)"] * base_multiplier > IRREVERSIBLE_THRESHOLD
    ].sum()

    last = df.iloc[-1]
    approx_mult = abs(last["expected_pct"]) / max(1e-6, portfolio["Weight (%)"].mean())
    incr = portfolio["Weight (%)"].mean() if approx_mult > IRREVERSIBLE_THRESHOLD else 0.0
    current_irrev = min(100.0, base_irrev + incr)

    history = [round(base_irrev), round(current_irrev)]

    st.markdown("Irreversible exposure: " + " → ".join(f"{x}%" for x in history))
    st.warning("Further deterioration historically correlates with unrecoverable drawdowns.")

    col1, col2, col3 = st.columns(3)
    with col1: st.button("Proceed anyway")
    with col2: st.button("Reduce magnitude")
    with col3: st.button("Abort decision")
