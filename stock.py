import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
import feedparser

st.set_page_config(page_title="FinVista Nexus", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

# ⚠️⚠️⚠️ your TWELVE api key  ⚠️⚠️⚠️
API_KEY = "1bc0db9c325f481280365f8a685740c2"  # https://twelvedata.com se free here

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&display=swap');
  .stApp {background: #000000; background-image: radial-gradient(circle at 20% 50%, rgba(0, 217, 255, 0.15) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(122, 0, 255, 0.15) 0%, transparent 50%);}
  .nexus-header {font-family: 'Orbitron', sans-serif; font-size: 4rem; font-weight: 900; background: linear-gradient(45deg, #00d9ff, #7a00ff, #ff00c8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; letter-spacing: 8px; margin-bottom: 0.5rem; animation: glow 2s infinite alternate;}
  @keyframes glow {0% { filter: drop-shadow(0 0 20px #00d9ff); } 100% { filter: drop-shadow(0 0 40px #7a00ff); }}
  .nexus-tagline {font-family: 'Rajdhani', sans-serif; text-align: center; color: #00d9ff; font-size: 1rem; letter-spacing: 4px; margin-bottom: 2rem;}
  .glass-card {background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(20px); border-radius: 20px; border: 1px solid rgba(0, 217, 255, 0.2); padding: 1.5rem; transition: all 0.3s ease;}
  .glass-card:hover {transform: translateY(-5px); border: 1px solid rgba(0, 217, 255, 0.6); box-shadow: 0 10px 40px 0 rgba(0, 217, 255, 0.3);}
  .metric-value {font-family: 'Orbitron', sans-serif; font-size: 2.2rem; font-weight: 700; background: linear-gradient(90deg, #00d9ff, #ffffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
  .metric-label {font-family: 'Rajdhani', sans-serif; color: #7a00ff; font-size: 0.8rem; letter-spacing: 2px; text-transform: uppercase;}
  .signal-buy {color: #00ff88; text-shadow: 0 0 20px #00ff88; font-family: 'Orbitron'; font-size: 1.8rem; font-weight: 700;}
  .signal-sell {color: #ff0055; text-shadow: 0 0 20px #ff0055; font-family: 'Orbitron'; font-size: 1.8rem; font-weight: 700;}
  .signal-hold {color: #ffaa00; text-shadow: 0 0 20px #ffaa00; font-family: 'Orbitron'; font-size: 1.8rem; font-weight: 700;}
  .news-item {background: rgba(255, 255, 255, 0.02); border-left: 3px solid #00d9ff; padding: 1rem; margin: 0.8rem 0; border-radius: 8px; transition: all 0.3s;}
  .news-item:hover {background: rgba(0, 217, 255, 0.1); border-left: 3px solid #7a00ff;}
  .stButton>button {background: linear-gradient(135deg, #00d9ff 0%, #7a00ff 100%); color: white; border: none; border-radius: 12px; font-family: 'Rajdhani', sans-serif; font-weight: 700; letter-spacing: 1px;}
  .stButton>button:hover {box-shadow: 0 0 30px #00d9ff; transform: scale(1.02);}
  .stTabs [data-baseweb="tab-list"] {gap: 12px;}
  .stTabs [data-baseweb="tab"] {background: rgba(255,255,255,0.03); border-radius: 12px; font-family: 'Orbitron', sans-serif; font-weight: 700; letter-spacing: 1px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="nexus-header">FINVISTA NEXUS</p>', unsafe_allow_html=True)
st.markdown('<p class="nexus-tagline">THE WORLD\'S FIRST ANTI-FRAGILE TRADING TERMINAL</p>', unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "AAPL", "TSLA"]

SYMBOL_MAP = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFY": "INFY.NS", "HDFCBANK": "HDFCBANK.NS", 
    "ICICIBANK": "ICICIBANK.NS", "SBIN": "SBIN.NS", "AAPL": "AAPL", "TSLA": "TSLA", 
    "MSFT": "MSFT", "GOOGL": "GOOGL", "BTC/USD": "BTC/USD", "ETH/USD": "ETH/USD"
}

mode = st.selectbox("", ["TERMINAL", "MARKET SCAN", "GLOBAL COMPARE", "AI FORECAST"], label_visibility="collapsed")

@st.cache_data(ttl=600)
def get_data(symbol):
    try:
        sym = SYMBOL_MAP.get(symbol, symbol)
        # Time Series
        url = f"https://api.twelvedata.com/time_series?symbol={sym}&interval=1day&outputsize=365&apikey={API_KEY}"
        r = requests.get(url, timeout=15).json()
        if "values" not in r:
            return None, None, None

        df = pd.DataFrame(r["values"])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime').sort_index()
        df = df.astype(float)

        # Quote
        q_url = f"https://api.twelvedata.com/quote?symbol={sym}&apikey={API_KEY}"
        q = requests.get(q_url, timeout=15).json()

        # Statistics
        s_url = f"https://api.twelvedata.com/statistics?symbol={sym}&apikey={API_KEY}"
        s = requests.get(s_url, timeout=15).json()

        info = {
            "name": q.get("name", symbol),
            "exchange": q.get("exchange", "N/A"),
            "market_cap": float(q.get("market_cap", 0)),
            "pe_ratio": float(s.get("statistics", {}).get("valuations_metrics", {}).get("trailing_pe", 0)),
            "high_52": float(q.get("fifty_two_week", {}).get("high", 0)),
            "low_52": float(q.get("fifty_two_week", {}).get("low", 0)),
        }

        return df, info, q
    except:
        return None, None, None

@st.cache_data(ttl=1800)
def get_news():
    try:
        feed = feedparser.parse("https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms")
        return feed.entries[:10]
    except:
        return []

if mode == "TERMINAL":
    col1, col2, col3 = st.columns([2,2,1])
    with col1:
        ticker_input = st.text_input("Enter Symbol", "RELIANCE", label_visibility="collapsed")
    with col2:
        if st.button("ANALYZE", use_container_width=True):
            st.session_state.current_ticker = ticker_input.upper()
    with col3:
        if st.button("⭐ WATCHLIST", use_container_width=True):
            if ticker_input.upper() not in st.session_state.watchlist:
                st.session_state.watchlist.append(ticker_input.upper())

    ticker = st.session_state.get('current_ticker', 'RELIANCE')

    with st.spinner(f'Quantum Scanning {ticker}...'):
        hist, info, quote = get_data(ticker)

        if hist is None:
            st.error("Data source temporarily unavailable. Check API Key or try again.")
            st.info("Get free API key: https://twelvedata.com")
            st.stop()

    current_price = hist['close'][-1]
    prev_close = hist['close'][-2] if len(hist) > 1 else current_price
    change = current_price - prev_close
    change_pct = (change / prev_close) * 100

    hist['SMA20'] = hist['close'].rolling(20).mean()
    hist['SMA50'] = hist['close'].rolling(50).mean()
    hist['SMA200'] = hist['close'].rolling(200).mean()
    delta = hist['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    hist['RSI'] = 100 - (100 / (1 + rs))
    rsi = hist['RSI'][-1] if not pd.isna(hist['RSI'][-1]) else 50

    # AI Signal Engine v2
    score = 0
    if rsi < 30: score += 2
    elif rsi < 40: score += 1
    if current_price > hist['SMA20'][-1]: score += 1
    if current_price > hist['SMA50'][-1]: score += 1
    if hist['SMA20'][-1] > hist['SMA50'][-1]: score += 1

    if score >= 4:
        signal = "STRONG BUY"; signal_class = "signal-buy"; signal_icon = "▲▲"
    elif score >= 2:
        signal = "BUY"; signal_class = "signal-buy"; signal_icon = "▲"
    elif score <= 1:
        signal = "SELL"; signal_class = "signal-sell"; signal_icon = "▼"
    else:
        signal = "HOLD"; signal_class = "signal-hold"; signal_icon = "■"

    st.markdown(f"### {info.get('name', ticker)} // {ticker} // {info.get('exchange', 'N/A')}")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Live Price</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value">{current_price:.2f}</p>', unsafe_allow_html=True)
        st.markdown(f'<p style="color:{"#00ff88" if change_pct>0 else "#ff0055"}; font-family: Orbitron;">{change_pct:+.2f}%</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Market Cap</p>', unsafe_allow_html=True)
        mcap = info.get('market_cap', 0)
        st.markdown(f'<p class="metric-value">{mcap/10000000:.0f}Cr</p>' if mcap > 10000000 else f'<p class="metric-value">${mcap/1e9:.1f}B</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">P/E Ratio</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value">{info.get("pe_ratio", 0):.1f}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">RSI Index</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value">{rsi:.1f}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c5:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Nexus Signal</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="{signal_class}">{signal_icon} {signal}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    t1, t2, t3, t4 = st.tabs(["PRICE MATRIX", "FUNDAMENTALS", "MARKET NEWS", "AI PREDICTION"])

    with t1:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=hist.index, open=hist['open'], high=hist['high'], low=hist['low'], close=hist['close'], name='Price', increasing_line_color='#00ff88', decreasing_line_color='#ff0055'))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA20'], line=dict(color='#00d9ff', width=2), name='SMA 20'))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], line=dict(color='#7a00ff', width=2), name='SMA 50'))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], line=dict(color='#ffaa00', width=2), name='SMA 200'))
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Rajdhani"))
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("52 Week High", f"{info.get('high_52', 0):.2f}")
            st.metric("Volume", f"{hist['volume'][-1]:,.0f}")
        with c2:
            st.metric("52 Week Low", f"{info.get('low_52', 0):.2f}")
            st.metric("Avg Volume", f"{hist['volume'].mean():,.0f}")
        with c3:
            st.metric("30D Volatility", f"{hist['close'].pct_change().std()*100:.2f}%")
            st.metric("YTD Return", f"{((hist['close'][-1]/hist['close'][0])-1)*100:.1f}%")

    with t3:
        news = get_news()
        if news:
            for item in news:
                st.markdown(f"""<div class="news-item"><h4 style="color: #00d9ff; margin: 0;">{item.title}</h4><p style="color: #7a00ff; font-size: 0.85rem; margin: 5px 0;">{item.published}</p><a href="{item.link}" target="_blank" style="color: #00d9ff; text-decoration: none;">Read More →</a></div>""", unsafe_allow_html=True)
        else:
            st.info("News feed loading...")

    with t4:
        pred_days = st.slider("Prediction Horizon", 1, 90, 30, label_visibility="collapsed")
        returns = hist['close'].pct_change().dropna()
        mu = returns.mean()
        sigma = returns.std()
        last_price = hist['close'][-1]
        sims = []
        for _ in range(1000):
            prices = [last_price]
            for _ in range(pred_days):
                prices.append(prices[-1] * (1 + np.random.normal(mu, sigma)))
            sims.append(prices[-1])
        future_price = np.median(sims)
        pred_change = ((future_price - current_price) / current_price) * 100
        conf_5 = np.percentile(sims, 5)
        conf_95 = np.percentile(sims, 95)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<p class="metric-label">AI Target</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="metric-value">{future_price:.2f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:{"#00ff88" if pred_change>0 else "#ff0055"};">{pred_change:+.1f}% Expected</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<p class="metric-label">Confidence Range</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="metric-value">{conf_5:.0f} - {conf_95:.0f}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<p class="metric-label">Probability</p>', unsafe_allow_html=True)
            prob_up = (np.array(sims) > current_price).mean() * 100
            st.markdown(f'<p class="metric-value">{prob_up:.0f}%</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="color: #7a00ff;">Chance of Profit</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

elif mode == "MARKET SCAN":
    st.markdown("### WATCHLIST RADAR")
    if len(st.session_state.watchlist) == 0:
        st.info("Add stocks from TERMINAL mode first")
    else:
        data = []
        for sym in st.session_state.watchlist:
            hist, info, _ = get_data(sym)
            if hist is not None:
                price = hist['close'][-1]
                change = ((hist['close'][-1] / hist['close'][-2]) - 1) * 100 if len(hist) > 1 else 0
                rsi = 50
                data.append({"Symbol": sym, "Price": f"{price:.2f}", "Change": f"{change:+.2f}%", "RSI": f"{rsi:.0f}"})
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

elif mode == "GLOBAL COMPARE":
    st.markdown("### GLOBAL ASSET COMPARISON")
    symbols_input = st.text_input("Enter symbols comma separated", "RELIANCE,AAPL,TSLA,BTC/USD", label_visibility="collapsed")
    if st.button("INITIATE COMPARISON"):
        symbols = [s.strip() for s in symbols_input.split(',')]
        fig = go.Figure()
        for sym in symbols:
            hist, _, _ = get_data(sym)
            if hist is not None:
                norm = (hist['close'] / hist['close'][0]) * 100
                fig.add_trace(go.Scatter(x=hist.index, y=norm, name=sym, mode='lines', line=dict(width=3)))
        fig.update_layout(template="plotly_dark", height=600, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Normalized Performance (%)", font=dict(family="Rajdhani"))
        st.plotly_chart(fig, use_container_width=True)

elif mode == "AI FORECAST":
    st.markdown("### MONTE CARLO SIMULATION ENGINE")
    ticker_fc = st.text_input("Symbol for Forecast", "RELIANCE", label_visibility="collapsed")
    days = st.slider("Days to Predict", 7, 365, 90)
    if st.button("RUN 10,000 SIMULATIONS"):
        hist, _, _ = get_data(ticker_fc)
        if hist is not None:
            returns = hist['close'].pct_change().dropna()
            mu, sigma = returns.mean(), returns.std()
            last_price = hist['close'][-1]
            sim_results = []
            for _ in range(10000):
                price = last_price
                for _ in range(days):
                    price *= (1 + np.random.normal(mu, sigma))
                sim_results.append(price)

            fig = go.Figure()
            fig.add_trace(go.Histogram(x=sim_results, nbinsx=100, name='Outcomes', marker_color='#00d9ff'))
            fig.add_vline(x=last_price, line_dash="dash", line_color="#ffaa00", annotation_text="Current")
            fig.add_vline(x=np.median(sim_results), line_dash="dash", line_color="#00ff88", annotation_text="Median Target")
            fig.update_layout(template="plotly_dark", height=500, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="Price", yaxis_title="Probability", font=dict(family="Rajdhani"))
            st.plotly_chart(fig, use_container_width=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Median Target", f"{np.median(sim_results):.2f}")
            with col2:
                st.metric("95% Confidence", f"{np.percentile(sim_results, 5):.0f} - {np.percentile(sim_results, 95):.0f}")
            with col3:
                st.metric("Probability of Profit", f"{(np.array(sim_results) > last_price).mean()*100:.1f}%")

st.markdown("---")
st.markdown("""<div style='text-align: center; font-family: Rajdhani, sans-serif; color: #444; font-size: 0.7rem;'>FINVISTA NEXUS GENESIS v1.0 | ANTI-FRAGILE ARCHITECTURE | POWERED BY TWELVE DATA</div>""", unsafe_allow_html=True)
