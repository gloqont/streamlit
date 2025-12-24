import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
import re
import os
import ast
import yfinance as yf
import feedparser
import random
from pyvis.network import Network
import tempfile


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
if "pending_symbol" not in st.session_state:
    st.session_state.pending_symbol = None
if "pending_price" not in st.session_state:
    st.session_state.pending_price = None

# ================= ANALYTICS LOGGING =================
def log_event(event_type, data=None):
    timestamp = datetime.utcnow().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "user_email": st.session_state.user_email,
        "event": event_type,
        "data": data or {}
    }

    if "event_log" not in st.session_state:
        st.session_state.event_log = []
    st.session_state.event_log.append(log_entry)

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
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@st.cache_data(ttl=24 * 3600)
def fetch_market_news():
    feed_url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US"
    feed = feedparser.parse(feed_url)

    headlines = []
    for entry in feed.entries[:8]:
        headlines.append(entry.title)

    return headlines

def classify_headline_sentiment(headline):
    negative_words = ["falls", "drops", "declines", "cuts", "slows", "crisis", "risk", "volatility", "plunge", "crash", "down"]
    positive_words = ["rises", "beats", "growth", "surges", "expands", "strong", "optimism", "rally", "gains", "up"]

    h = headline.lower()

    if any(w in h for w in negative_words):
        return "Negative"
    if any(w in h for w in positive_words):
        return "Positive"
    return "Neutral"

def pick_market_headlines():
    headlines = fetch_market_news()

    if not headlines:
        return []

    selected = random.sample(headlines, min(2, len(headlines)))

    return [
        {
            "title": h,
            "sentiment": classify_headline_sentiment(h)
        }
        for h in selected
    ]

@st.cache_data(ttl=24 * 3600)
def resolve_equity_symbol(user_input, country):
    """
    Auto-adds .NS for Indian stocks, resolves symbols via Yahoo Finance
    """
    query = user_input.strip().upper()
    candidates = []

    try:
        # Auto-add .NS for Indian stocks
        if country == "India" and not query.endswith(".NS"):
            query_variants = [query, f"{query}.NS"]
        else:
            query_variants = [query]

        # Try each variant
        for variant in query_variants:
            try:
                ticker = yf.Ticker(variant)
                hist = ticker.history(period="1d")

                if not hist.empty:
                    info = ticker.fast_info
                    candidates.append({
                        "symbol": variant,
                        "name": info.get("shortName", variant),
                        "price": float(hist["Close"].iloc[-1])
                    })
                    
                    # If we found a match, return immediately
                    if candidates:
                        return candidates
            except:
                continue

        # Fallback: Search by name
        search = yf.Search(user_input, max_results=5)
        for item in search.quotes[:3]:
            symbol = item.get("symbol")
            name = item.get("shortname") or item.get("longname")

            # Auto-add .NS for Indian companies
            if country == "India" and not symbol.endswith(".NS") and not any(x in symbol for x in [".", "-"]):
                symbol = f"{symbol}.NS"

            t = yf.Ticker(symbol)
            h = t.history(period="1d")

            if not h.empty:
                candidates.append({
                    "symbol": symbol,
                    "name": name,
                    "price": float(h["Close"].iloc[-1])
                })

    except Exception:
        pass

    return candidates

@st.cache_data(ttl=24 * 3600)
def get_live_price(symbol):
    """Fetch yesterday's closing price from Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except:
        pass
    return None

def load_demo_portfolio_with_live_prices():
    """Load demo portfolio with real yesterday prices from Yahoo Finance"""
    demo_tickers = [
        ("AAPL", "USA", "Equity", 120),
        ("MSFT", "USA", "Equity", 80),
        ("NVDA", "USA", "Equity", 40),
        ("ASML", "Europe", "Equity", 25),
        ("RELIANCE.NS", "India", "Equity", 90),
        ("TCS.NS", "India", "Equity", 60),
        ("BTC-USD", "Global", "Crypto", 1.2),
    ]
    
    entries = []
    for ticker, region, asset_class, quantity in demo_tickers:
        price = get_live_price(ticker)
        if price:
            entries.append({
                "Asset": ticker,
                "Region": region,
                "Class": asset_class,
                "Quantity": quantity,
                "Price": price
            })
    
    return entries

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
    - Type the asset name or ticker (e.g., Apple, AAPL, Reliance, TCS)
    - For Indian stocks: We automatically add .NS suffix
    - Confirm the suggested equity for accuracy
    - Quantity is mandatory
    """)

    if "portfolio_entries" not in st.session_state:
        st.session_state.portfolio_entries = []

    # ---- SYMBOL RESOLUTION (OUTSIDE FORM) ----
    st.markdown("#### 🔍 Step 1: Search for Asset")
    
    col1, col2 = st.columns(2)
    with col1:
        asset_input = st.text_input(
            "Asset / Company name*",
            placeholder="e.g., Apple, AAPL, Reliance, TCS"
        )
    with col2:
        region = st.selectbox(
            "Region*",
            ["USA", "India", "Europe", "Asia", "Global", "Other"]
        )

    # Show suggestions if user typed something
    if asset_input:
        suggestions = resolve_equity_symbol(asset_input, region)

        if suggestions:
            st.markdown("**Did you mean:**")
            for idx, s in enumerate(suggestions):
                if st.button(
                    f"✓ Use {s['symbol']} — {s['name']} (Last close: ${s['price']:.2f})",
                    key=f"select_{s['symbol']}_{idx}"
                ):
                    st.session_state.pending_symbol = s["symbol"]
                    st.session_state.pending_price = s["price"]
                    
                    log_event("symbol_resolved", {
                        "input": asset_input,
                        "resolved_symbol": s["symbol"]
                    })
                    
                    st.success(f"✅ Selected: {s['symbol']}")
                    st.rerun()
        else:
            st.warning("⚠️ No matching equity found. Try refining the name.")

    # ---- ADD POSITION FORM ----
    if st.session_state.pending_symbol:
        st.markdown("---")
        st.markdown("#### ➕ Step 2: Add Position to Portfolio")
        
        st.info(f"**Selected:** {st.session_state.pending_symbol} @ ${st.session_state.pending_price:.2f}")

        with st.form("add_position_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                quantity = st.number_input(
                    "Quantity*",
                    min_value=0.0001,
                    value=1.0,
                    step=0.1,
                    format="%.4f"
                )
            
            with col2:
                asset_class = st.selectbox(
                    "Asset Class*",
                    ["Equity", "Crypto", "Bonds", "Commodities", "Real Estate", "Cash", "Other"]
                )

            add_position = st.form_submit_button("➕ Add to Portfolio", use_container_width=True)

            if add_position:
                new_entry = {
                    "Asset": st.session_state.pending_symbol,
                    "Region": region,
                    "Class": asset_class,
                    "Quantity": quantity,
                    "Price": st.session_state.pending_price
                }

                st.session_state.portfolio_entries.append(new_entry)

                log_event("position_added", {
                    "asset": st.session_state.pending_symbol,
                    "asset_class": asset_class,
                    "quantity": quantity,
                    "price_source": "yfinance_last_close"
                })

                st.success(f"✅ Added {st.session_state.pending_symbol} to portfolio!")
                
                # Reset pending
                st.session_state.pending_symbol = None
                st.session_state.pending_price = None
                
                st.rerun()

    # ---- PORTFOLIO PREVIEW ----
    if st.session_state.portfolio_entries:
        st.markdown("---")
        st.markdown("#### 📊 Your Portfolio Preview")

        df = pd.DataFrame(st.session_state.portfolio_entries)
        df["Value"] = df["Quantity"] * df["Price"]
        total = df["Value"].sum()
        df["Weight (%)"] = (df["Value"] / total * 100).round(2)

        # Display with delete option
        for idx, row in df.iterrows():
            col1, col2 = st.columns([5, 1])
            with col1:
                st.text(f"{row['Asset']} | {row['Region']} | {row['Class']} | "
                       f"Qty: {row['Quantity']:.4f} @ ${row['Price']:.2f} = ${row['Value']:,.2f} ({row['Weight (%)']:.1f}%)")
            with col2:
                if st.button("🗑️", key=f"delete_{idx}"):
                    st.session_state.portfolio_entries.pop(idx)
                    st.rerun()

        st.markdown(f"**💰 Total Portfolio Value: ${total:,.2f}**")

        # Confirm button
        if st.button("✅ Confirm Portfolio & Start Analysis", type="primary", use_container_width=True):
            if len(df) < 2:
                st.error("❌ Please add at least 2 positions.")
            else:
                st.session_state.user_portfolio = df
                st.session_state.portfolio_entered = True

                log_event("portfolio_confirmed", {
                    "num_positions": len(df),
                    "total_value": float(total),
                    "time_spent_seconds": (datetime.utcnow() - st.session_state.session_start).seconds
                })

                st.success("🎉 Portfolio saved! Redirecting...")
                st.rerun()
    else:
        st.warning("👆 Search and select an asset above to start building your portfolio")

    # ---- DEMO PORTFOLIO OPTION ----
    st.markdown("---")
    st.markdown("### 🎮 Or Try With Demo Portfolio")
    st.info("Load a sample portfolio with real market prices (updated daily)")
    
    if st.button("📊 Load Demo Portfolio with Live Prices", use_container_width=True):
        with st.spinner("Fetching live market prices..."):
            demo_entries = load_demo_portfolio_with_live_prices()
            
            if demo_entries:
                st.session_state.portfolio_entries = demo_entries
                
                log_event("demo_portfolio_loaded", {
                    "num_positions": len(demo_entries)
                })
                
                st.success("✅ Demo portfolio loaded with live prices!")
                st.rerun()
            else:
                st.error("❌ Failed to load demo portfolio. Please try manually adding positions.")

# ================= DECISION ANALYSIS SCREEN =================
def show_analysis():
    portfolio = st.session_state.user_portfolio
    total_value = portfolio["Value"].sum()
    
    pnl_pct = 0.6
    pnl_val = round(total_value * pnl_pct / 100, 0)
    
    st.title("GLOQONT")
    st.caption("What happens to your portfolio if you do this?")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**User:** {st.session_state.user_name} | **Email:** {st.session_state.user_email}")
    with col2:
        if st.button("📝 Edit Portfolio"):
            st.session_state.portfolio_entered = False
            st.rerun()
    
    st.markdown("---")
    
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
    
    mode = st.radio(
        "Decision Context",
        ["Reflexive Mode (short-term, convex risk)", "Compounding Mode (long-term, drawdown risk)"],
        horizontal=True
    )
    
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
    
    if submit and decision_text.strip():
        st.session_state.simulation_count += 1
        log_event("simulation_run", {
            "decision": decision_text,
            "magnitude": magnitude,
            "decision_type": decision_type,
            "simulation_number": st.session_state.simulation_count
        })
        
        target = analyze_decision(decision_text, portfolio)
        c = consequence_engine(target, magnitude, portfolio, total_value, mode)
        
        show_consequences(target, c, portfolio, total_value, decision_text, mode)
        
        log_event("results_viewed", {
            "target": target,
            "risk_multiplier": c["multiplier"],
            "blocked": c["block"]
        })

# ================= DECISION PARSER =================
def analyze_decision(text, portfolio):
    text = text.lower()
    
    for asset in portfolio["Asset"]:
        if asset.lower() in text:
            return asset
    
    for region in portfolio["Region"].unique():
        if region.lower() in text:
            return region
    
    for asset_class in portfolio["Class"].unique():
        if asset_class.lower() in text:
            return asset_class
    
    return "Macro / Multi-Asset"

# ================= CONSEQUENCE ENGINE =================
def consequence_engine(target, magnitude, portfolio, total_value, mode):
    if target in portfolio["Asset"].values:
        w = portfolio.loc[portfolio["Asset"] == target, "Weight (%)"].iloc[0]
    elif target in portfolio["Region"].values:
        w = portfolio.loc[portfolio["Region"] == target, "Weight (%)"].sum()
    elif target in portfolio["Class"].values:
        w = portfolio.loc[portfolio["Class"] == target, "Weight (%)"].sum()
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


# ================= TRANSMISSION GRAPH LOGIC =================
def build_transmission_graph(decision_text, portfolio, c):
    text = decision_text.lower()

    # ---- Step 1: Detect macro drivers ----
    macro_drivers = []
    if any(k in text for k in ["rate", "hike", "cut", "policy"]):
        macro_drivers.append(("Interest Rates", 1.2))
    if any(k in text for k in ["inflation", "cpi", "prices"]):
        macro_drivers.append(("Inflation", 1.0))
    if any(k in text for k in ["liquidity", "credit", "crisis", "stress"]):
        macro_drivers.append(("Liquidity", 1.3))
    if any(k in text for k in ["growth", "recession", "slowdown"]):
        macro_drivers.append(("Growth", 1.1))
    if any(k in text for k in ["fx", "currency", "dollar", "rupee", "euro"]):
        macro_drivers.append(("FX", 1.0))

    if not macro_drivers:
        return None  # graph not applicable

    nodes = []
    edges = []

    # ---- Step 2: Portfolio node ----
    nodes.append({
        "id": "portfolio",
        "type": "portfolio",
        "label": "Your Portfolio",
        "severity": 0
    })

    # ---- Step 3: Region aggregation ----
    region_weights = (
        portfolio.groupby("Region")["Weight (%)"].sum().to_dict()
    )

    # ---- Step 4: Build graph ----
    for macro, macro_factor in macro_drivers:
        macro_id = macro.lower().replace(" ", "_")

        nodes.append({
            "id": macro_id,
            "type": "macro",
            "label": macro,
            "severity": macro_factor * c["multiplier"]
        })

        for region, weight in region_weights.items():
            region_id = region.lower().replace(" ", "_")

            severity = weight * c["multiplier"] * macro_factor

            nodes.append({
                "id": region_id,
                "type": "region",
                "label": region,
                "severity": round(severity, 2)
            })

            edges.append({
                "from": macro_id,
                "to": region_id,
                "weight": round(severity, 2)
            })

            region_assets = portfolio[portfolio["Region"] == region]

            for _, row in region_assets.iterrows():
                asset_id = row["Asset"]

                asset_severity = row["Weight (%)"] * c["multiplier"]

                nodes.append({
                    "id": asset_id,
                    "type": "asset",
                    "label": asset_id,
                    "severity": round(asset_severity, 2)
                })

                edges.append({
                    "from": region_id,
                    "to": asset_id,
                    "weight": round(asset_severity, 2)
                })

                edges.append({
                    "from": asset_id,
                    "to": "portfolio",
                    "weight": round(row["Weight (%)"], 2)
                })

    # ---- Step 5: Deduplicate nodes ----
    unique_nodes = {n["id"]: n for n in nodes}.values()

    return {
        "nodes": list(unique_nodes),
        "edges": edges
    }

# ================= TRANSMISSION GRAPH RENDERER =================
def render_network_graph(graph_data):
    if not graph_data:
        return

    net = Network(
        height="420px",
        width="100%",
        directed=True,
        bgcolor="#0e1117",
        font_color="white"
    )

    # Fixed layout – no physics
    net.toggle_physics(False)

    # Color mapping by severity
    def node_color(severity):
        if severity > 5:
            return "#ff4d4d"   # Critical
        elif severity > 2:
            return "#f5a623"   # Elevated
        return "#6fcf97"       # Neutral

    # ---- Add nodes ----
    for n in graph_data["nodes"]:
        net.add_node(
            n["id"],
            label=n["label"],
            title=f"Severity: {n['severity']}",
            color=node_color(n["severity"]),
            shape={
                "macro": "diamond",
                "region": "ellipse",
                "asset": "box",
                "portfolio": "star"
            }.get(n["type"], "dot")
        )

    # ---- Add edges ----
    for e in graph_data["edges"]:
        net.add_edge(
            e["from"],
            e["to"],
            value=e["weight"],
            title=f"Impact weight: {e['weight']}"
        )

    # ---- Render to temp HTML ----
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        st.components.v1.html(
            open(tmp.name, "r", encoding="utf-8").read(),
            height=450,
            scrolling=False
        )



# ================= CONSEQUENCES DISPLAY =================
def show_consequences(target, c, portfolio, total_value, decision_text, mode):
    st.markdown("## 🔴 Decision Consequences")
    
    # ================= MARKET CONTEXT =================
    st.markdown("### 📰 Market Context (Last 24h)")

    news_items = pick_market_headlines()

    for n in news_items:
        if n["sentiment"] == "Negative":
            st.error(f"🔻 {n['title']}")
        elif n["sentiment"] == "Positive":
            st.success(f"🔺 {n['title']}")
        else:
            st.info(f"ℹ️ {n['title']}")

    st.caption("Market news is provided for context only, not as a recommendation.")

    # ================= TRANSMISSION GRAPH =================
        # ================= TRANSMISSION GRAPH =================
    if target == "Macro / Multi-Asset":
        graph_data = build_transmission_graph(decision_text, portfolio, c)

        if graph_data:
            st.markdown("### 🕸️ Impact Transmission Path")
            st.caption(
                "How this macro event propagates through regions, assets, and into your portfolio."
            )
            render_network_graph(graph_data)


    st.markdown("---")
    
    st.markdown("### 🟢 If You Do Nothing")
    st.markdown(
        "• Portfolio risk remains unchanged\n"
        "• Expected drift: +0.6%\n"
        "• No acceleration of downside"
    )
    
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
    
    st.markdown("### 📊 Portfolio Impact Distribution")
    st.table(pd.DataFrame({
        "Scenario": ["Worst Case", "Best Case", "Expected"],
        "Portfolio Change (%)": [c["worst"], c["best"], c["expected"]]
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
        portfolio[["Asset", "Weight (%)"]]
        .sort_values("Weight (%)", ascending=False),
        use_container_width=True
    )
    
    st.markdown("### 🚨 Irreversibility Check")
    
    capital_loss = abs(c["worst"]) * total_value / 100
    opportunity_loss = capital_loss * 0.6
    
    st.markdown(
        f"If this goes wrong, what cannot be undone:\n\n"
        f"• Capital lost: ~${capital_loss:,.0f}\n"
        f"• Time to recover: ~{c['break_time']} {c['unit']}\n"
        f"• Opportunity cost: ~${opportunity_loss:,.0f}"
    )
    
    show_irreversible_heatmap(c)
    show_portfolio_exposure(c, portfolio, total_value)
    
    observed = round(c["expected"] * np.random.uniform(0.5, 1.4), 2)
    st.session_state.decision_log.append({
        "time": now(),
        "decision": decision_text,
        "target": target,
        "expected_pct": c["expected"],
        "observed_pct": observed,
        "portfolio_value": total_value
    })
    
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
                heatmap[i, j] = 1
            elif score < 75:
                heatmap[i, j] = 2
            else:
                heatmap[i, j] = 3
    
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
    
    equity_mask = portfolio["Class"] == "Equity"
    macro_mask = portfolio["Region"] != "USA"
    liquidity_mask = portfolio["Class"].isin(["Crypto"])
    
    base_multiplier = 3.0
    base_irrev = portfolio["Weight (%)"][portfolio["Weight (%)"] * base_multiplier > IRREVERSIBLE_THRESHOLD].sum()
    
    decision_irrev = 0.0
    if c["multiplier"] > IRREVERSIBLE_THRESHOLD:
        decision_irrev = c["weight"]
    
    total_irrev_after = min(100.0, base_irrev + decision_irrev)
    
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

# ================= FOUNDER ANALYTICS =================
def show_founder_analytics():
    st.markdown("## 🧠 Founder Analytics (Internal Only)")

    if not os.path.exists(ANALYTICS_FILE):
        st.info("No analytics data yet.")
        return

    df = pd.read_csv(ANALYTICS_FILE)

    if df.empty:
        st.info("No analytics data yet.")
        return

    signups = df[df["event"] == "user_signup"]["user_email"].nunique()
    activations = df[df["event"] == "portfolio_confirmed"]["user_email"].nunique()
    activation_rate = (activations / signups * 100) if signups > 0 else 0

    st.markdown("### 📌 Core Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Signups", signups)
    col2.metric("Activated Users", activations)
    col3.metric("Activation Rate", f"{activation_rate:.1f}%")

    st.markdown("### 🔻 Signup → Activation Funnel")
    funnel_df = pd.DataFrame({
        "Stage": ["Signed Up", "Portfolio Confirmed"],
        "Users": [signups, activations]
    })
    st.bar_chart(funnel_df.set_index("Stage"))

    sims = df[df["event"] == "simulation_run"]
    if not sims.empty:
        sims_per_user = sims.groupby("user_email").size()
        st.markdown("### 🔁 Simulations per User")
        st.bar_chart(sims_per_user)
        st.metric("Avg Simulations / User", f"{sims_per_user.mean():.2f}")

    feedback = df[df["event"].str.startswith("feedback")]
    if not feedback.empty:
        sentiment = feedback["event"].value_counts().rename_axis("Sentiment").reset_index(name="Count")
        st.markdown("### 💬 Feedback Sentiment")
        st.bar_chart(sentiment.set_index("Sentiment"))

    st.markdown("### 📁 Raw Analytics Data")
    st.download_button(
        "Download analytics_events.csv",
        df.to_csv(index=False),
        file_name="analytics_events.csv"
    )


# main logic

def main():
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


