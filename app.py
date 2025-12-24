import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
import re
import os
import ast


ANALYTICS_FILE = "analytics_events.csv"

FOUNDER_EMAIL = "dgosa1437@gmail.com"


# ================= CONFIG =================
st.set_page_config(page_title="GLOQONT", layout="centered")

# ================= SESSION STATE INITIALIZATION =================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "portfolio_entered" not in st.session_state:
    st.session_state.portfolio_entered = False
if "user_portfolio" not in st.session_state:
    st.session_state.user_portfolio = None
if "decision_log" not in st.session_state:
    st.session_state.decision_log = []
if "simulation_count" not in st.session_state:
    st.session_state.simulation_count = 0
if "session_start" not in st.session_state:
    st.session_state.session_start = datetime.utcnow()

# ================= ANALYTICS LOGGING =================
def log_event(event_type, data=None):
    timestamp = datetime.utcnow().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "user_email": st.session_state.user_email,
        "event": event_type,
        "data": data or {}
    }

    # ---- Session log (still useful) ----
    if "event_log" not in st.session_state:
        st.session_state.event_log = []
    st.session_state.event_log.append(log_entry)

    # ---- Global persistent log ----
    df = pd.DataFrame([{
        "timestamp": timestamp,
        "user_email": st.session_state.user_email,
        "event": event_type,
        "data": str(data or {})
    }])

    if os.path.exists(ANALYTICS_FILE):
        df.to_csv(ANALYTICS_FILE, mode="a", header=False, index=False)
    else:
        df.to_csv(ANALYTICS_FILE, index=False)


# ================= HELPERS =================
def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def validate_email(email):
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def to_date(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    return df

# ================= AUTHENTICATION SCREEN =================
def show_login():
    st.title("🎯 GLOQONT")
    st.subheader("See What Happens to Your Portfolio BEFORE You Make the Decision")
    
    st.markdown("""
    ### Why GLOQONT?
    - 📊 **Portfolio-wide impact analysis** - Not just single stock moves
    - ⚡ **Real-time consequence modeling** - Before you commit capital
    - 🎯 **Cross-asset correlation detection** - See hidden risks
    - 🚨 **Irreversibility warnings** - Know what can't be undone
    """)
    
    st.markdown("---")
    st.markdown("### 🚀 Start Your Free Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("login_form"):
            name = st.text_input("Your Name", placeholder="John Doe")
            email = st.text_input("Email Address", placeholder="john@example.com")
            
            submitted = st.form_submit_button("Analyze My Portfolio →", use_container_width=True)
            
            if submitted:
                if not name or not email:
                    st.error("Please fill in both fields")
                elif not validate_email(email):
                    st.error("Please enter a valid email address")
                else:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.user_name = name
                    st.session_state.session_start = datetime.utcnow()
                    
                    # Log signup event
                    log_event("user_signup", {
                        "email": email,
                        "name": name
                    })
                    
                    st.rerun()
    
    with col2:
        st.info("💡 **Takes 5 minutes**\n\nNo payment required.\nYour data stays private.")

# ================= PORTFOLIO ENTRY SCREEN =================
def show_portfolio_entry():
    st.title(f"Welcome, {st.session_state.user_name}! 👋")
    st.markdown("### Enter Your Portfolio")
    
    st.info("""
    **📝 How to enter your portfolio:**
    - Add each position (stocks, crypto, etc.)
    - Specify quantity and current price
    - We'll calculate the portfolio weights automatically
    """)
    
    # Initialize portfolio entries in session state
    if "portfolio_entries" not in st.session_state:
        st.session_state.portfolio_entries = []
    
    # Portfolio entry form
    with st.form("portfolio_form", clear_on_submit=True):
        st.markdown("#### Add Position")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            asset_ticker = st.text_input(
                "Asset/Ticker*", 
                placeholder="e.g., AAPL, BTC, RELIANCE.NS",
                help="Enter stock ticker, crypto symbol, or asset name"
            )
        
        with col2:
            quantity = st.number_input(
                "Quantity*", 
                min_value=0.0001,
                value=1.0,
                step=0.1,
                format="%.4f",
                help="Number of units you own"
            )
        
        with col3:
            price = st.number_input(
                "Current Price (USD)*", 
                min_value=0.01,
                value=100.0,
                step=0.01,
                help="Current market price per unit"
            )
        
        col4, col5 = st.columns(2)
        
        with col4:
            region = st.selectbox(
                "Region*",
                ["USA", "India", "Europe", "Asia", "Global", "Other"],
                help="Geographic region or market"
            )
        
        with col5:
            asset_class = st.selectbox(
                "Asset Class*",
                ["Equity", "Crypto", "Bonds", "Commodities", "Real Estate", "Cash", "Other"],
                help="Type of asset"
            )
        
        add_position = st.form_submit_button("➕ Add Position", use_container_width=True)
        
        if add_position:
            if not asset_ticker:
                st.error("Asset/Ticker is required")
            else:
                new_entry = {
                    "Asset": asset_ticker.upper().strip(),
                    "Region": region,
                    "Class": asset_class,
                    "Quantity": quantity,
                    "Price": price
                }
                st.session_state.portfolio_entries.append(new_entry)
                st.success(f"✅ Added {asset_ticker.upper()}")
                
                # Log position added
                log_event("position_added", {
                    "asset": asset_ticker.upper(),
                    "value": quantity * price
                })
    
    # Display current portfolio
    if st.session_state.portfolio_entries:
        st.markdown("---")
        st.markdown("#### 📊 Your Portfolio Preview")
        
        # Create DataFrame
        df = pd.DataFrame(st.session_state.portfolio_entries)
        df["Value"] = df["Quantity"] * df["Price"]
        total = df["Value"].sum()
        df["Weight (%)"] = (df["Value"] / total * 100).round(2)
        
        # Display with option to remove
        for idx, row in df.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(f"{row['Asset']} | {row['Region']} | {row['Class']} | "
                       f"Qty: {row['Quantity']:.4f} | Price: ${row['Price']:.2f} | "
                       f"Value: ${row['Value']:,.2f} ({row['Weight (%)']:.2f}%)")
            with col2:
                if st.button("🗑️", key=f"remove_{idx}"):
                    st.session_state.portfolio_entries.pop(idx)
                    st.rerun()
        
        st.markdown(f"**Total Portfolio Value: ${total:,.2f}**")
        
        # Confirm portfolio button
        if st.button("✅ Confirm Portfolio & Start Analysis", type="primary", use_container_width=True):
            if len(st.session_state.portfolio_entries) < 2:
                st.error("Please add at least 2 positions to analyze portfolio impact")
            else:
                st.session_state.user_portfolio = df
                st.session_state.portfolio_entered = True
                
                # Log portfolio confirmation
                log_event("portfolio_confirmed", {
                    "num_positions": len(df),
                    "total_value": float(total),
                    "time_spent_seconds": (datetime.utcnow() - st.session_state.session_start).seconds
                })
                
                st.success("🎉 Portfolio saved! Redirecting to analysis...")
                st.rerun()
    
    else:
        st.warning("👆 Add your first position above to get started")
        
        # Option to use demo portfolio
        st.markdown("---")
        if st.button("🎮 Or Try With Demo Portfolio First"):
            demo_entries = [
                {"Asset": "AAPL", "Region": "USA", "Class": "Equity", "Quantity": 120, "Price": 190},
                {"Asset": "MSFT", "Region": "USA", "Class": "Equity", "Quantity": 80, "Price": 420},
                {"Asset": "NVDA", "Region": "USA", "Class": "Equity", "Quantity": 40, "Price": 1150},
                {"Asset": "RELIANCE.NS", "Region": "India", "Class": "Equity", "Quantity": 90, "Price": 2900},
                {"Asset": "BTC", "Region": "Global", "Class": "Crypto", "Quantity": 1.2, "Price": 65000},
            ]
            st.session_state.portfolio_entries = demo_entries
            
            # Log demo usage
            log_event("demo_portfolio_selected")
            st.rerun()

# ================= DECISION ANALYSIS SCREEN =================
def show_analysis():
    portfolio = st.session_state.user_portfolio
    total_value = portfolio["Value"].sum()
    
    # Calculate P&L (simulated for demo)
    pnl_pct = 0.6
    pnl_val = round(total_value * pnl_pct / 100, 0)
    
    # Header
    st.title("GLOQONT")
    st.caption("What happens to your portfolio if you do this?")
    
    # User info and portfolio summary
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**User:** {st.session_state.user_name} | **Email:** {st.session_state.user_email}")
    with col2:
        if st.button("📝 Edit Portfolio"):
            st.session_state.portfolio_entered = False
            st.rerun()
    
    st.markdown("---")
    
    # Portfolio snapshot
    st.markdown("## 💼 Your Portfolio Snapshot")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Value", f"${total_value:,.0f}", f"+{pnl_pct}%")
    with col2:
        st.metric("Positions", len(portfolio))
    with col3:
        st.metric("Simulations Run", st.session_state.simulation_count)
    
    st.dataframe(portfolio[["Asset", "Region", "Class", "Quantity", "Price", "Value", "Weight (%)"]],
                 use_container_width=True)
    
    st.markdown("---")
    
    # Mode selection
    mode = st.radio(
        "Decision Context",
        ["Reflexive Mode (short-term, convex risk)", "Compounding Mode (long-term, drawdown risk)"],
        horizontal=True
    )
    
    # Decision input
    with st.form("decision"):
        st.markdown("## 🎯 Test Your Decision")
        
        decision_type = st.selectbox(
            "Decision Type",
            ["Trade Decision", "Portfolio Reallocation", "Macro Event", "Shock Scenario"]
        )
        
        decision_text = st.text_input(
            "What decision are you about to make?",
            placeholder="e.g., Buy more NVDA, Sell 50% of AAPL, Increase India exposure by 10%",
            help="Describe the trade or decision you're considering"
        )
        
        magnitude = st.slider("Decision Size / Intensity (%)", 1, 30, 5,
                            help="How significant is this decision relative to your portfolio?")
        
        submit = st.form_submit_button("🔍 Show Consequences", type="primary", use_container_width=True)
    
    # Analysis logic
    if submit and decision_text.strip():
        # Log simulation event
        st.session_state.simulation_count += 1
        log_event("simulation_run", {
            "decision": decision_text,
            "magnitude": magnitude,
            "decision_type": decision_type,
            "simulation_number": st.session_state.simulation_count
        })
        
        # Parse decision
        target = analyze_decision(decision_text, portfolio)
        c = consequence_engine(target, magnitude, portfolio, total_value, mode)
        
        # Display results
        show_consequences(target, c, portfolio, total_value, decision_text, mode)
        
        # Log results viewed
        log_event("results_viewed", {
            "target": target,
            "risk_multiplier": c["multiplier"],
            "blocked": c["block"]
        })

# ================= DECISION PARSER =================
def analyze_decision(text, portfolio):
    text = text.lower()
    
    # Check for assets
    for asset in portfolio["Asset"]:
        if asset.lower() in text:
            return asset
    
    # Check for regions
    for region in portfolio["Region"].unique():
        if region.lower() in text:
            return region
    
    # Check for asset classes
    for asset_class in portfolio["Class"].unique():
        if asset_class.lower() in text:
            return asset_class
    
    return "Macro / Multi-Asset"

# ================= CONSEQUENCE ENGINE =================
def consequence_engine(target, magnitude, portfolio, total_value, mode):
    # Calculate weight affected
    if target in portfolio["Asset"].values:
        w = portfolio.loc[portfolio["Asset"] == target, "Weight (%)"].iloc[0]
    elif target in portfolio["Region"].values:
        w = portfolio.loc[portfolio["Region"] == target, "Weight (%)"].sum()
    elif target in portfolio["Class"].values:
        w = portfolio.loc[portfolio["Class"] == target, "Weight (%)"].sum()
    else:
        w = 18.0  # Default for macro
    
    # Risk calculation
    base_risk = w / 8
    size_boost = 1 + magnitude / 18
    risk_multiplier = base_risk * size_boost
    
    # Impact scenarios
    worst = -risk_multiplier * 2.4
    best = risk_multiplier * 1.2
    expected = (worst + best) / 2
    
    # Time dynamics
    if "Reflexive" in mode:
        break_time = max(2, int(35 / risk_multiplier))
        unit = "minutes"
    else:
        break_time = max(5, int(55 / risk_multiplier))
        unit = "months"
    
    # Risk flag
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

# ================= CONSEQUENCES DISPLAY =================
def show_consequences(target, c, portfolio, total_value, decision_text, mode):
    st.markdown("## 🔴 Decision Consequences")
    
    # Do nothing scenario
    st.markdown("### 🟢 If You Do Nothing")
    st.markdown(
        "• Portfolio risk remains unchanged\n"
        "• Expected drift: +0.6%\n"
        "• No acceleration of downside"
    )
    
    # Execute scenario
    st.markdown("### 🔴 If You Execute This Decision")
    
    if c["block"]:
        st.error("⛔ DO NOT EXECUTE — downside accelerates beyond recovery control")
    else:
        st.warning("⚠️ Risk increases materially — execution requires discipline")
    
    st.markdown(
        f"**Primary exposure impacted:** {target}\n\n"
        f"**Portfolio weight affected:** {c['weight']}%"
    )
    
    st.metric("Downside Amplification", f"{c['multiplier']}×")
    
    # Impact distribution
    st.markdown("### 📊 Portfolio Impact Distribution")
    st.table(pd.DataFrame({
        "Scenario": ["Worst Case", "Best Case", "Expected"],
        "Portfolio Change (%)": [c["worst"], c["best"], c["expected"]]
    }))
    
    # Time to damage
    st.markdown("### ⏱️ Time-to-Damage")
    st.metric("Losses accelerate within", f"{c['break_time']} {c['unit']}")
    
    # Market regime fragility
    st.markdown("### 🌪️ Fragile Under Market Regimes")
    st.markdown(
        "• Volatility expansion\n"
        "• Liquidity contraction\n"
        "• Correlation spikes"
    )
    
    # Risk concentration
    st.markdown("### 🧩 Risk Concentration Attribution")
    st.dataframe(
        portfolio[["Asset", "Weight (%)"]].sort_values("Weight (%)", ascending=False),
        use_container_width=True
    )
    
    # Irreversibility check
    st.markdown("### 🚨 Irreversibility Check")
    
    capital_loss = abs(c["worst"]) * total_value / 100
    opportunity_loss = capital_loss * 0.6
    
    st.markdown(
        f"If this goes wrong, what cannot be undone:\n\n"
        f"• Capital lost: ~${capital_loss:,.0f}\n"
        f"• Time to recover: ~{c['break_time']} {c['unit']}\n"
        f"• Opportunity cost: ~${opportunity_loss:,.0f}"
    )
    
    # Irreversible loss heatmap
    show_irreversible_heatmap(c)
    
    # Portfolio-level exposure
    show_portfolio_exposure(c, portfolio, total_value)
    
    # Session log
    observed = round(c["expected"] * np.random.uniform(0.5, 1.4), 2)
    st.session_state.decision_log.append({
        "time": now(),
        "decision": decision_text,
        "target": target,
        "expected_pct": c["expected"],
        "observed_pct": observed,
        "portfolio_value": total_value
    })
    
    # Feedback section
    st.markdown("---")
    st.markdown("### 💬 Was This Analysis Helpful?")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("👍 Very Helpful", use_container_width=True):
            log_event("feedback_positive", {"decision": decision_text})
            st.success("Thank you! 🙏")
    with col2:
        if st.button("🤔 Somewhat Helpful", use_container_width=True):
            log_event("feedback_neutral", {"decision": decision_text})
            st.info("Thanks for the feedback!")
    with col3:
        if st.button("👎 Not Helpful", use_container_width=True):
            log_event("feedback_negative", {"decision": decision_text})
            st.warning("We'll improve!")

# ================= IRREVERSIBLE HEATMAP =================
def show_irreversible_heatmap(c):
    st.markdown("### 🔥 Irreversible-Loss Heatmap")
    
    time_horizon = ["Weeks", "Months", "Years"]
    capital_risk = np.array([5, 10, 15, 20, 25, 30])
    
    heatmap = np.zeros((len(capital_risk), len(time_horizon)))
    
    for i, cap in enumerate(capital_risk):
        for j, t in enumerate(time_horizon):
            score = cap * (j + 1) * c["multiplier"]
            if score < 40:
                heatmap[i, j] = 1  # recoverable
            elif score < 75:
                heatmap[i, j] = 2  # delayed
            else:
                heatmap[i, j] = 3  # unrecoverable
    
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
            f"⚠️ This decision pushes approximately {unrecoverable_pct}% "
            "of your portfolio into an unrecoverable loss zone under stress."
        )

# ================= PORTFOLIO EXPOSURE =================
def show_portfolio_exposure(c, portfolio, total_value):
    st.markdown("### 🧠 Portfolio-Level Irreversible Exposure")
    
    IRREVERSIBLE_THRESHOLD = 4.5
    
    # Classify assets
    equity_mask = portfolio["Class"] == "Equity"
    macro_mask = portfolio["Region"] != "USA"
    liquidity_mask = portfolio["Class"].isin(["Crypto"])
    
    # Base exposure
    base_multiplier = 3.0
    base_irrev = portfolio["Weight (%)"][portfolio["Weight (%)"] * base_multiplier > IRREVERSIBLE_THRESHOLD].sum()
    
    # Decision exposure
    decision_irrev = 0.0
    if c["multiplier"] > IRREVERSIBLE_THRESHOLD:
        decision_irrev = c["weight"]
    
    total_irrev_after = min(100.0, base_irrev + decision_irrev)
    
    # Category breakdowns
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
    
    # Display
    st.markdown(
        f"This decision increases irreversible exposure from "
        f"**{base_irrev:.0f}% → {total_irrev_after:.0f}%** of the portfolio under stress."
    )
    
    st.markdown(
        f"• Equity irreversible exposure: {equity_irrev:.0f}%\n"
        f"• Macro-sensitive irreversible exposure: {macro_irrev:.0f}%\n"
        f"• Liquidity-locked irreversible exposure: {liquidity_irrev:.0f}%"
    )
    
    if decision_irrev > 0:
        st.error(
            "⚠️ A material portion of the portfolio has entered a structurally fragile state. "
            "Recovery now depends on favorable external conditions, not decision quality."
        )
    
def show_founder_analytics():
    st.markdown("## 🧠 Founder Analytics (Internal Only)")

    if not os.path.exists(ANALYTICS_FILE):
        st.info("No analytics data yet.")
        return

    df = pd.read_csv(ANALYTICS_FILE)

    if df.empty:
        st.info("No analytics data yet.")
        return

    # -------------------------
    # BASIC METRICS
    # -------------------------
    signups = df[df["event"] == "user_signup"]["user_email"].nunique()
    activations = df[df["event"] == "portfolio_confirmed"]["user_email"].nunique()

    activation_rate = (activations / signups * 100) if signups > 0 else 0
        # -------------------------
    # TIME-SERIES VIEWS
    # -------------------------
    st.markdown("## 📈 Time-Series Trends")

    df_ts = add_date_column(df)

    # Daily Signups
    signups_ts = (
        df_ts[df_ts["event"] == "user_signup"]
        .groupby("date")["user_email"]
        .nunique()
    )

    if not signups_ts.empty:
        st.markdown("### Daily Signups")
        st.line_chart(signups_ts)

    # Daily Activations
    activations_ts = (
        df_ts[df_ts["event"] == "portfolio_confirmed"]
        .groupby("date")["user_email"]
        .nunique()
    )

    if not activations_ts.empty:
        st.markdown("### Daily Portfolio Activations")
        st.line_chart(activations_ts)

    # Activation Rate Over Time
    if not signups_ts.empty and not activations_ts.empty:
        combined = pd.concat(
            [signups_ts, activations_ts],
            axis=1,
            keys=["signups", "activations"]
        ).fillna(0)

        combined["activation_rate_pct"] = (
            combined["activations"]
            / combined["signups"].replace(0, np.nan)
            * 100
        )

        st.markdown("### Activation Rate Over Time (%)")
        st.line_chart(combined["activation_rate_pct"])

    # Daily Simulations Volume
    simulations_ts = (
        df_ts[df_ts["event"] == "simulation_run"]
        .groupby("date")
        .size()
    )

    if not simulations_ts.empty:
        st.markdown("### Daily Simulations Run")
        st.line_chart(simulations_ts)


    st.markdown("### 📌 Core Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Signups", signups)
    col2.metric("Activated Users", activations)
    col3.metric("Activation Rate", f"{activation_rate:.1f}%")

    # -------------------------
    # FUNNEL VISUAL
    # -------------------------
    st.markdown("### 🔻 Signup → Activation Funnel")

    funnel_df = pd.DataFrame({
        "Stage": ["Signed Up", "Portfolio Confirmed"],
        "Users": [signups, activations]
    })

    st.bar_chart(funnel_df.set_index("Stage"))

    # -------------------------
    # SIMULATIONS PER USER
    # -------------------------
    sims = df[df["event"] == "simulation_run"]
    if not sims.empty:
        sims_per_user = sims.groupby("user_email").size()

        st.markdown("### 🔁 Simulations per User")
        st.bar_chart(sims_per_user)

        st.metric("Avg Simulations / User", f"{sims_per_user.mean():.2f}")

    # -------------------------
    # FEEDBACK SENTIMENT
    # -------------------------
    feedback = df[df["event"].str.startswith("feedback")]
    if not feedback.empty:
        sentiment = feedback["event"].value_counts().rename_axis("Sentiment").reset_index(name="Count")

        st.markdown("### 💬 Feedback Sentiment")
        st.bar_chart(sentiment.set_index("Sentiment"))

        with st.expander("Who clicked what"):
            st.dataframe(feedback[["user_email", "event", "timestamp"]])

    # -------------------------
    # STAY TIME DISTRIBUTION
    # -------------------------
    portfolio_events = df[df["event"] == "portfolio_confirmed"]

    def extract_time(val):
        try:
            parsed = ast.literal_eval(val)
            return parsed.get("time_spent_seconds", 0)
        except Exception:
            return 0

    if not portfolio_events.empty:
        portfolio_events["stay_seconds"] = portfolio_events["data"].apply(extract_time)

        st.markdown("### ⏱️ Time Spent Before Activation (seconds)")
        st.bar_chart(portfolio_events["stay_seconds"])

        st.metric(
            "Median Time to Portfolio Entry",
            f"{portfolio_events['stay_seconds'].median():.0f} sec"
        )

    # -------------------------
    # RAW EXPORT (FOR YOU)
    # -------------------------
    st.markdown("### 📁 Raw Analytics Data")
    st.download_button(
        "Download analytics_events.csv",
        df.to_csv(index=False),
        file_name="analytics_events.csv"
    )


# ================= MAIN APP LOGIC =================
def main():
    # Founder analytics (sidebar only)
    if st.session_state.user_email == FOUNDER_EMAIL:
        show_founder_analytics()

    if not st.session_state.authenticated:
        show_login()
    elif not st.session_state.portfolio_entered:
        show_portfolio_entry()
    else:
        show_analysis()


if __name__ == "__main__":
    main() 




