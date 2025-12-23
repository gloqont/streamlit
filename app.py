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

st.metric(
    "Total Portfolio Value",
    f"${total_value:,.0f}",
    f"+{pnl_pct}% (${pnl_val:,.0f})"
)

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
    st.markdown(
        "• Portfolio risk remains unchanged\n"
        "• Expected drift: +0.6%\n"
        "• No acceleration of downside"
    )

    st.markdown("### 🔴 If You Execute This Decision")

    if c["block"]:
        st.error("DO NOT EXECUTE — downside accelerates beyond recovery control")
    else:
        st.warning("Risk increases materially — execution requires discipline")

    st.markdown(
        f"Primary exposure impacted: {target}\n\n"
        f"Portfolio weight affected: {c['weight']}%"
    )

    st.metric("Downside amplification", f"{c['multiplier']}×")

    st.markdown("### 📊 Portfolio Impact Distribution")
    st.table(pd.DataFrame({
        "Scenario": ["Worst Case", "Best Case"],
        "Portfolio Change (%)": [c["worst"], c["best"]]
    }))

    st.markdown("### ⏱️ Time-to-Damage")
    st.metric("Losses accelerate within", f"{c['break_time']} {c['unit']}")

    st.markdown("### 🌪️ Fragile Under Market Regimes")
    st.markdown(
        "• Volatility expansion\n"
        "• Liquidity contraction\n"
        "• Correlation spikes"
    )

    st.markdown("### 🧩 Risk Concentration Attribution")
    st.dataframe(
        portfolio[["Asset", "Weight (%)"]].sort_values("Weight (%)", ascending=False),
        use_container_width=True
    )

    # ===== FIXED IRREVERSIBILITY TEXT (NO ** ANYWHERE) =====
    st.markdown("### 🚨 Irreversibility Check")

    capital_loss = abs(c["worst"]) * total_value / 100
    opportunity_loss = capital_loss * 0.6

    st.markdown(
        f"If this goes wrong, what cannot be undone:\n\n"
        f"• Capital lost: ~${capital_loss:,.0f}\n"
        f"• Time to recover: ~{c['break_time']} {c['unit']}\n"
        f"• Opportunity cost: ~${opportunity_loss:,.0f}"
    )

    # ================= ADDITION: IRREVERSIBLE-LOSS HEATMAP =================
    st.markdown("### 🔥 Irreversible-Loss Heatmap")

    time_horizon = ["Weeks", "Months", "Years"]
    capital_risk = np.array([5, 10, 15, 20, 25, 30])

    heatmap = np.zeros((len(capital_risk), len(time_horizon)))

    for i, cap in enumerate(capital_risk):
        for j, t in enumerate(time_horizon):
            score = cap * (j + 1) * c["multiplier"]
            if score < 40:
                heatmap[i, j] = 1    # recoverable
            elif score < 75:
                heatmap[i, j] = 2    # delayed
            else:
                heatmap[i, j] = 3    # unrecoverable

    heatmap_df = pd.DataFrame(
        heatmap,
        index=[f"{c}% capital" for c in capital_risk],
        columns=time_horizon
    )

    st.dataframe(
        heatmap_df.replace({
            1: "Recoverable",
            2: "Delayed recovery",
            3: "Unrecoverable"
        }),
        use_container_width=True
    )

    unrecoverable_pct = capital_risk[heatmap.max(axis=1) == 3].max(initial=0)

    if unrecoverable_pct > 0:
        st.error(
            f"This decision pushes approximately {unrecoverable_pct}% "
            "of your portfolio into an unrecoverable loss zone under stress."
        )

    observed = round(c["expected"] * np.random.uniform(0.5, 1.4), 2)

    st.session_state.decision_log.append({
        "time": now(),
        "decision": decision_text,
        "target": target,
        "expected_pct": c["expected"],
        "observed_pct": observed,
        "portfolio_value": total_value
    })
        # ================= ADDITION: PORTFOLIO-LEVEL IRREVERSIBLE EXPOSURE =================
    st.markdown("### 🧠 Portfolio-Level Irreversible Exposure")

    # --- heuristic thresholds (intentionally simple & explainable) ---
    IRREVERSIBLE_THRESHOLD = 4.5  # structural loss regime

    # --- classify assets ---
    equity_mask = portfolio["Class"] == "Equity"
    macro_mask = portfolio["Region"] != "USA"  # proxy for macro sensitivity
    liquidity_mask = portfolio["Class"].isin(["Crypto"])  # proxy for liquidity lock

    # --- base irreversible exposure before decision (static baseline) ---
    base_multiplier = 3.0  # conservative baseline stress
    base_irrev = portfolio["Weight (%)"][portfolio["Weight (%)"] * base_multiplier > IRREVERSIBLE_THRESHOLD].sum()

    # --- incremental exposure from this decision ---
    decision_irrev = 0.0
    if c["multiplier"] > IRREVERSIBLE_THRESHOLD:
        decision_irrev = c["weight"]

    # --- aggregated after-decision exposure ---
    total_irrev_after = min(100.0, base_irrev + decision_irrev)

    # --- category breakdowns ---
    equity_irrev = portfolio.loc[
        equity_mask & (portfolio["Weight (%)"] * c["multiplier"] > IRREVERSIBLE_THRESHOLD),
        "Weight (%)"
    ].sum()

    macro_irrev = portfolio.loc[
        macro_mask & (portfolio["Weight (%)"] * c["multiplier"] > IRREVERSIBLE_THRESHOLD),
        "Weight (%)"
    ].sum()

    liquidity_irrev = portfolio.loc[
        liquidity_mask & (portfolio["Weight (%)"] * c["multiplier"] > IRREVERSIBLE_THRESHOLD),
        "Weight (%)"
    ].sum()

    # --- display (one number, one statement, clean breakdown) ---
    st.markdown(
        f"This decision increases irreversible exposure from "
        f"{base_irrev:.0f}% → {total_irrev_after:.0f}% of the portfolio under stress."
    )

    st.markdown(
        f"• Equity irreversible exposure: {equity_irrev:.0f}%\n"
        f"• Macro-sensitive irreversible exposure: {macro_irrev:.0f}%\n"
        f"• Liquidity-locked irreversible exposure: {liquidity_irrev:.0f}%"
    )

    if decision_irrev > 0:
        st.error(
            "A material portion of the portfolio has entered a structurally fragile state. "
            "Recovery now depends on favorable external conditions, not decision quality."
        )

