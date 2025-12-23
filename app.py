import streamlit as st
import numpy as np
import pandas as pd
from uuid import uuid4
from datetime import datetime

# ================= CONFIG =================
st.set_page_config(page_title="GLOQONT — Decision Consequences", layout="centered")

# ================= HELPERS =================
def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

# ================= CORE CONSEQUENCE ENGINE =================
def consequence_engine(decision_type, decision_text, magnitude):
    """
    Consequences scale based on:
    - decision type
    - magnitude
    - whether decision sounds concentrated, macro, or risky
    """

    text = decision_text.lower()

    concentration_boost = 1.4 if any(x in text for x in ["nvda", "single", "one", "all in"]) else 1.0
    macro_boost = 1.6 if decision_type in ["Macro Event", "Shock Scenario"] else 1.0
    size_boost = 1 + magnitude / 20

    risk_multiplier = concentration_boost * macro_boost * size_boost

    base_vol = 1.2  # %
    p5 = -base_vol * risk_multiplier * 2.2
    p50 = base_vol * (1 / risk_multiplier)
    p95 = base_vol * risk_multiplier * 1.3

    drawdown = abs(p5) * 1.4

    attribution = {
        "Target asset exposure": round(55 * concentration_boost, 1),
        "Correlation increase": round(30 * macro_boost, 1),
        "Liquidity loss": round(15 * size_boost, 1),
    }

    regime = {
        "Risk-On": {"do_nothing": 0.8, "act": p95},
        "Risk-Off": {"do_nothing": -1.1, "act": p5},
    }

    liquidity_flag = "⚠️ Harder to exit quickly" if magnitude > 10 else "✓ Liquidity stable"

    kid_explanation = (
        f"If things go bad, you lose money **faster than before**.\n\n"
        f"Before, falling hurt a little.\n"
        f"After this decision, falling hurts **a lot more**."
    )

    return {
        "distribution": (p5, p50, p95),
        "drawdown": drawdown,
        "attribution": attribution,
        "regime": regime,
        "liquidity": liquidity_flag,
        "kid": kid_explanation,
        "multiplier": round(abs(p5) / base_vol, 1),
    }

# ================= UI =================
st.title("GLOQONT")
st.caption("What happens to your money if you do this?")

st.markdown("""
Before money moves, GLOQONT shows **what gets worse**.
Not predictions. **Consequences.**
""")

# ================= DECISION INPUT =================
with st.form("decision"):
    decision_type = st.selectbox(
        "Decision Type",
        ["Trade Decision", "Portfolio Action", "Macro Event", "Shock Scenario"]
    )

    decision_text = st.text_input(
        "What are you about to do?",
        placeholder="Buy NVDA +5%, Reduce equities −10%, Fed hikes 50bps"
    )

    magnitude = st.slider("How big is this decision (%)", 1, 30, 5)

    submitted = st.form_submit_button("Show Consequences")

# ================= CONSEQUENCE OUTPUT =================
if submitted and decision_text.strip():

    c = consequence_engine(decision_type, decision_text, magnitude)

    st.markdown("## 🔴 What this decision does to your portfolio")

    st.error(
        f"""
        **Big picture:**  
        This decision makes bad outcomes **{c['multiplier']}× worse** when markets turn against you.
        """
    )

    # -------- P&L DISTRIBUTION --------
    st.markdown("### 📊 Portfolio Outcomes (Next 30 Days)")

    dist_df = pd.DataFrame({
        "Scenario": ["Worst case", "Typical", "Best case"],
        "Portfolio change (%)": [
            round(c["distribution"][0], 2),
            round(c["distribution"][1], 2),
            round(c["distribution"][2], 2),
        ]
    })

    st.table(dist_df)

    # -------- WORST CASE --------
    st.markdown("### 💥 Worst-Case Damage")

    st.warning(
        f"""
        If things go wrong, your portfolio can fall **{round(c['drawdown'],2)}%**
        before you can recover.
        """
    )

    # -------- ATTRIBUTION --------
    st.markdown("### 🧩 What causes the damage")

    attr_df = pd.DataFrame.from_dict(
        c["attribution"], orient="index", columns=["% of total downside"]
    )

    st.bar_chart(attr_df)

    # -------- CORRELATION --------
    st.markdown("### 🔗 Correlation Breakage")

    st.info(
        """
        Assets that usually move separately now **fall together**.
        Diversification protects you less when you need it most.
        """
    )

    # -------- LIQUIDITY --------
    st.markdown("### 💧 Liquidity Stress")

    st.write(c["liquidity"])

    # -------- REGIME --------
    st.markdown("### 🌧️ What happens in different markets")

    regime_df = pd.DataFrame([
        ["Markets calm", c["regime"]["Risk-On"]["do_nothing"], c["regime"]["Risk-On"]["act"]],
        ["Markets panic", c["regime"]["Risk-Off"]["do_nothing"], c["regime"]["Risk-Off"]["act"]],
    ], columns=["Market mood", "Do nothing (%)", "If you act (%)"])

    st.table(regime_df)

    # -------- KID EXPLANATION --------
    st.markdown("### 🧠 Explain it to a 10-year-old")

    st.success(c["kid"])

    # -------- DO NOTHING VS ACT --------
    st.markdown("## ⚖️ Do Nothing vs Act")

    left, right = st.columns(2)

    with left:
        st.markdown("### 🟦 Do Nothing")
        st.markdown("""
        - Portfolio stays balanced  
        - Losses grow slowly  
        - You have time to react  
        - Diversification still helps  
        """)

    with right:
        st.markdown("### 🟥 Act on this decision")
        st.markdown(f"""
        - Bigger swings up **and down**  
        - Losses grow faster  
        - Assets move together  
        - Recovery takes longer  
        """)

    st.markdown(
        f"""
        ⚠️ **Simple truth:**  
        Doing nothing keeps risk **manageable**.  
        Acting makes mistakes **hurt faster**.
        """
    )
