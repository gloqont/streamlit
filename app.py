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

    df = pd.DataFrame(
        rows,
        columns=["Asset", "Region", "Class", "Quantity", "Price"]
    )
    df["Value"] = df["Quantity"] * df["Price"]
    total = df["Value"].sum()
    df["Weight (%)"] = (df["Value"] / total * 100).round(2)

    return df, total

portfolio, total_value = load_demo_portfolio()

# ================= LANDING =================
st.title("GLOQONT")
st.caption("What happens to your portfolio if you do this?")

st.markdown("""
**Portfolio-aware decision intelligence.**  
GLOQONT exposes *irreversible consequences* before capital is committed.
""")

# ================= PORTFOLIO =================
st.markdown("## 💼 Portfolio Snapshot")
st.metric("Total Portfolio Value", f"${total_value:,.0f}")
st.dataframe(portfolio, use_container_width=True)

# ================= MODE =================
mode = st.radio(
    "Decision Context",
    ["Reflexive Mode (short-term, convex risk)", "Compounding Mode (long-term, drawdown risk)"],
    horizontal=True
)

# ================= DECISION INPUT =================
with st.form("decision"):
    decision_text = st.text_input(
        "What decision are you about to make?",
        placeholder="Buy NVDA +5%, Reduce India exposure, Fed hikes 50bps"
    )
    magnitude = st.slider("Decision Size / Intensity (%)", 1, 30, 5)
    submit = st.form_submit_button("Show Consequences")

# ================= PARSER =================
def analyze_decision(text):
    t = text.lower()
    for a in portfolio["Asset"]:
        if a.lower() in t:
            return a, "asset"
    for r in portfolio["Region"].unique():
        if r.lower() in t:
            return r, "macro"
    if "fed" in t or "rate" in t:
        return "Rates", "macro"
    return "Multi-Asset", "macro"

# ================= CONSEQUENCE ENGINE =================
def consequence_engine(target, magnitude):
    if target in portfolio["Asset"].values:
        w = portfolio.loc[portfolio["Asset"] == target, "Weight (%)"].iloc[0]
    elif target in portfolio["Region"].values:
        w = portfolio.loc[portfolio["Region"] == target, "Weight (%)"].sum()
    else:
        w = 18.0

    risk = (w / 8) * (1 + magnitude / 18)

    return {
        "weight": round(w, 2),
        "multiplier": round(risk, 1),
        "worst": round(-risk * 2.4, 2),
        "best": round(risk * 1.2, 2),
        "expected": round((-risk * 2.4 + risk * 1.2) / 2, 2),
        "irreversible": risk > 4.5,
        "time_loss": max(3, int(40 / risk)),
    }

# ================= OUTPUT =================
if submit and decision_text.strip():

    target, dtype = analyze_decision(decision_text)
    c = consequence_engine(target, magnitude)

    st.markdown("## 🔴 Decision Consequences")

    # -------- IRREVERSIBILITY FRAMING --------
    st.markdown("### 🚨 What Cannot Be Undone")

    capital_loss = abs(c["worst"]) * total_value / 100
    opportunity_loss = capital_loss * 0.6

    st.markdown(f"""
    • **Permanent capital loss:** ~${capital_loss:,.0f}  
    • **Time lost to recovery:** ~{c["time_loss"]} months  
    • **Opportunity cost:** ~${opportunity_loss:,.0f}  
    """)

    if c["irreversible"]:
        st.error("This decision enters **irreversible territory**. Recovery depends on external luck, not skill.")

    # -------- COUNTERFACTUAL --------
    st.markdown("### 🟢 Dominant Safer Alternative")

    st.success("""
    **Instead:**  
    Reduce position size by 50%  
    Preserve optionality  
    Maintain upside without left-tail acceleration  
    """)

    # -------- REGRET VISUALIZATION --------
    st.markdown("### 🕰️ Regret Projection")

    st.warning(f"""
    **6 months from now:**  
    Portfolio value: **${total_value + capital_loss * -0.8:,.0f}**  
    You realize this loss required **no urgency** — only restraint.
    """)

    # -------- STORE DECISION --------
    observed = round(c["expected"] * np.random.uniform(0.6, 1.4), 2)

    st.session_state.decision_log.append({
        "time": now(),
        "decision": decision_text,
        "type": dtype,
        "mode": mode,
        "expected_pct": c["expected"],
        "observed_pct": observed,
        "risk": c["multiplier"],
        "portfolio_value": total_value
    })

# ================= REPLAY =================
st.markdown("## 🔁 Decision Replay")

if st.session_state.decision_log:
    df = pd.DataFrame(st.session_state.decision_log)

    REQUIRED = ["time","decision","type","mode","expected_pct","observed_pct","risk","portfolio_value"]
    for c in REQUIRED:
        if c not in df.columns:
            df[c] = np.nan

    df["Expected P&L ($)"] = (df["portfolio_value"] * df["expected_pct"] / 100).round(0)
    df["Observed P&L ($)"] = (df["portfolio_value"] * df["observed_pct"] / 100).round(0)

    st.dataframe(
        df.reindex(columns=["time","decision","type","Expected P&L ($)","Observed P&L ($)"]),
        use_container_width=True
    )

# ================= DECISION PATHOLOGY =================
st.markdown("## 🧠 Your Decision Patterns")

if len(st.session_state.decision_log) >= 3:
    df = pd.DataFrame(st.session_state.decision_log)

    insights = []

    if df[df["type"] == "macro"]["risk"].mean() > df[df["type"] == "asset"]["risk"].mean():
        insights.append("You **underestimate downside in macro decisions**.")

    if df[df["mode"].str.contains("Reflexive")]["risk"].mean() > 4:
        insights.append("You **oversize trades in Reflexive mode**.")

    if insights:
        for i in insights:
            st.error(i)
    else:
        st.success("No dominant behavioral risks detected yet.")
else:
    st.info("Decision pathology appears after more decisions.")
