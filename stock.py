import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import feedparser

st.set_page_config(page_title="FinVista Nexus", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

API_KEY = "1bc0db9c325f481280365f8a685740c2"

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
 .stButton>button {background: linear-gradient(135deg, #00d9ff 0%, #7a00ff 100%); color: white; border: none; border-radius: 12px; font-family: 'Rajdhani', sans-serif; font-weight: 700; letter-spacing: 1px;}
 .stButton>button:hover {box-shadow: 0 0 30px #00d9ff; transform: scale(1.02);}
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

@st.cache_data(ttl=600)
def get_data(symbol):
    try:
        sym = symbol.upper().strip()
        indian_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "ADANIENT", "TATAMOTORS", "ITC", "WIPRO"]
        if sym in indian_stocks:
            sym = sym + ".NS"
        
        url = f"https://api.twelvedata.com/time_series?symbol={sym}&interval=1day&outputsize=365&apikey={API_KEY}"
        r = requests.get(url, timeout=15).json()
        if "values" not in r or r.get("status") == "error":
            st.error(f"API Error: {r.get('message', 'Unknown error')}")
            return None, None, None

        df = pd.DataFrame(r["values"])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime').sort_index()
        df = df.astype(float)

        q_url = f"https://api.twelvedata.com/quote?symbol={sym}&apikey={API_KEY}"
        q = requests.get(q_url, timeout=15).json()

        s_url = f"https://api.twelvedata.com/statistics?symbol={sym}&apikey={API_KEY}"
        s = requests.get(s_url, timeout=15).json()

        info = {
            "name": q.get("name", symbol),
            "exchange": q.get("exchange", "N/A"),
            "market_cap": float(q.get("market_cap", 0)),
            "pe_ratio": float(s.get("statistics", {}).get("valuations_metrics", {}).get("trailing_pe", 0)) if s.get("statistics") else 0,
            "high_52": float(q.get("fifty_two_week", {}).get("high", 0)),
            "low_52": float(q.get("fifty_two_week", {}).get("low", 0)),
        }

        return df, info, q
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
            return None, None, None

mode = st.selectbox("Select Mode", ["TERMINAL", "CHART"], label_visibility="collapsed")

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
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index, open=hist['open'], high=hist['high'], low=hist['low'], close=hist['close'], name='Price', increasing_line_color='#00ff88', decreasing_line_color='#ff0055'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA20'], line=dict(color='#00d9ff', width=2), name='SMA 20'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], line=dict(color='#7a00ff', width=2), name='SMA 50'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], line=dict(color='#ffaa00', width=2), name='SMA 200'))
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Rajdhani"))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("""<div style='text-align: center; font-family: Rajdhani, sans-serif; color: #444; font-size: 0.7rem;'>FINVISTA NEXUS GENESIS v1.0 | ANTI-FRAGILE ARCHITECTURE | POWERED BY TWELVE DATA</div>""", unsafe_allow_html=True)
