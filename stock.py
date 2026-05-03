import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import ta

st.set_page_config(page_title="FinVista Nexus V2", layout="wide", page_icon="📈")
API_KEY = "1bc0db9c325f481280365f8a685740c2"

st.markdown("<style>.main {background-color: #0E1117;} .stMetric {background-color: #262730; padding: 15px; border-radius: 10px; border: 1px solid #3d3d5c;} .stButton>button {background-color: #00C853; color: white; border-radius: 8px; font-weight: bold;} h1 {color: #00C853; text-align: center;}</style>", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_data(symbol):
    try:
        sym = symbol.upper().strip()
        sym = sym.replace(".NS", "")
        indian_stocks = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ADANIENT","TATAMOTORS","ITC","WIPRO","LT","AXISBANK","KOTAKBANK","BAJFINANCE","MARUTI","HCLTECH","ASIANPAINT","SUNPHARMA","TITAN","ULTRACEMCO","BANKNIFTY"]
        if sym in indian_stocks:
            sym = sym + ".NS"
        elif sym == "SENSEX":
            sym = "BSE:SENSEX"
        elif sym == "NIFTY":
             sym = "NIFTY 50"
        elif sym == "SENSEX":
            sym = "SENSEX"
        elif sym == "BANKNIFTY":
            sym = "NIFTY BANK"
        url = f"https://api.twelvedata.com/time_series?symbol={sym}&interval=1day&outputsize=500&apikey={API_KEY}"
        r = requests.get(url).json()
        if "status" in r and r["status"] == "error":
            st.error(f"API Error: {r['message']}")
            return None, None
        if "values" not in r:
            st.error("Data nahi mila. Symbol check karo: RELIANCE, TCS, AAPL, NIFTY")
            return None, None
        df = pd.DataFrame(r["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime").sort_index()
        df = df.astype(float)
        df['EMA20'] = ta.trend.ema_indicator(df['close'], window=20)
        df['EMA50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)
        macd = ta.trend.MACD(df['close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        bb = ta.volatility.BollingerBands(df['close'])
        df['BB_High'] = bb.bollinger_hband()
        df['BB_Low'] = bb.bollinger_lband()
        q_url = f"https://api.twelvedata.com/quote?symbol={sym}&apikey={API_KEY}"
        q = requests.get(q_url).json()
        info = {
            "name": q.get("name", symbol),
            "close": float(q.get("close", 0)),
            "percent_change": float(q.get("percent_change", 0)),
            "high": float(q.get("high", 0)),
            "low": float(q.get("low", 0)),
            "open": float(q.get("open", 0)),
            "volume": int(float(q.get("volume", 0))),
            "high_52": float(q.get("fifty_two_week", {}).get("high", 0)),
            "low_52": float(q.get("fifty_two_week", {}).get("low", 0)),
        }
        return df, info
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None, None

def nexus_signal(df, info):
    score = 0
    signals = []
    rsi = df['RSI'].iloc[-1]
    if rsi < 30:
        score += 2; signals.append("🟢 RSI Oversold <30: Bounce aa sakta")
    elif rsi > 70:
        score -= 2; signals.append("🔴 RSI Overbought >70: Giravat aa sakti")
    else:
        signals.append(f"🟡 RSI Neutral: {rsi:.1f}")
    if df['EMA20'].iloc[-1] > df['EMA50'].iloc[-1] and df['EMA20'].iloc[-2] <= df['EMA50'].iloc[-2]:
        score += 3; signals.append("🟢 EMA Golden Cross: 20 EMA ne 50 EMA ko upar kata")
    elif df['EMA20'].iloc[-1] < df['EMA50'].iloc[-1] and df['EMA20'].iloc[-2] >= df['EMA50'].iloc[-2]:
        score -= 3; signals.append("🔴 EMA Death Cross: 20 EMA ne 50 EMA ko neeche kata")
    if df['MACD'].iloc[-1] > df['MACD_Signal'].iloc[-1] and df['MACD'].iloc[-2] <= df['MACD_Signal'].iloc[-2]:
        score += 2; signals.append("🟢 MACD Bullish Crossover")
    elif df['MACD'].iloc[-1] < df['MACD_Signal'].iloc[-1]:
        score -= 1; signals.append("🔴 MACD Bearish")
    if info['close'] < df['BB_Low'].iloc[-1]:
        score += 1; signals.append("🟢 Price BB Lower band ke neeche: Oversold")
    elif info['close'] > df['BB_High'].iloc[-1]:
        score -= 1; signals.append("🔴 Price BB Upper band ke upar: Overbought")
    if score >= 4:
        verdict = "STRONG BUY 🚀"; color = "#00C853"
    elif score >= 2:
        verdict = "BUY 📈"; color = "#64DD17"
    elif score <= -4:
        verdict = "STRONG SELL 💀"; color = "#D50000"
    elif score <= -2:
        verdict = "SELL 📉"; color = "#FF1744"
    else:
        verdict = "NEUTRAL ⚖️"; color = "#FFD600"
    return verdict, color, score, signals

def plot_advanced_chart(df, symbol, info):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2], subplot_titles=(f'{symbol} Price', 'RSI', 'MACD'))
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='orange', width=1), name='EMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='blue', width=1), name='EMA 50'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='gray', width=1, dash='dot'), name='BB High'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='gray', width=1, dash='dot'), name='BB Low', fill='tonexty'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='blue', width=2), name='MACD'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='orange', width=2), name='Signal'), row=3, col=1)
    fig.update_layout(template="plotly_dark", height=800, showlegend=True, xaxis_rangeslider_visible=False, hovermode='x unified')
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="RSI", range=[0,100], row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    st.plotly_chart(fig, use_container_width=True)

st.title("FinVista Nexus V2.0 💎")
st.caption("AI-Powered Stock Analysis - Duniya ka sabse tez signal system")

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["RELIANCE", "TCS", "NIFTY"]
if 'ticker' not in st.session_state:
    st.session_state.ticker = "RELIANCE"

st.sidebar.header("📌 My Watchlist")
for stock in st.session_state.watchlist:
    if st.sidebar.button(stock, key=f"wl_{stock}"):
        st.session_state.ticker = stock

col1, col2, col3 = st.columns([3,1,1])
with col1:
    ticker = st.text_input("Stock Symbol Daalo", value=st.session_state.get('ticker', 'RELIANCE'), placeholder="RELIANCE, TCS, AAPL, NIFTY, SENSEX", label_visibility="collapsed")
with col2:
    if st.button("🔍 ANALYZE", use_container_width=True):
        st.session_state.ticker = ticker.upper()
with col3:
    if st.button("⭐ ADD", use_container_width=True):
        if ticker.upper() not in st.session_state.watchlist:
            st.session_state.watchlist.append(ticker.upper())
            st.rerun()

if st.session_state.get('ticker'):
    with st.spinner('Nexus AI data la raha hai...'):
        df, info = get_data(st.session_state.ticker)
    if df is not None:
        st.subheader(f"{info['name']}")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("LTP", f"₹{info['close']:.2f}", f"{info['percent_change']:.2f}%")
        m2.metric("Open", f"₹{info['open']:.2f}")
        m3.metric("High", f"₹{info['high']:.2f}")
        m4.metric("Low", f"₹{info['low']:.2f}")
        m5.metric("Volume", f"{info['volume']:,}")
        verdict, color, score, signals = nexus_signal(df, info)
        st.markdown(f"<h2 style='text-align: center; color: {color};'>NEXUS SIGNAL: {verdict} | Score: {score}/10</h2>", unsafe_allow_html=True)
        with st.expander("🧠 AI Signal Breakdown - Kyun Ye Signal Aaya"):
            for signal in signals:
                st.write(signal)
            st.info("Disclaimer: Ye educational analysis hai. Investment advice nahi hai. Risk aapka hai.")
        plot_advanced_chart(df, st.session_state.ticker, info)
        with st.expander("📊 Last 20 Days Data"):
            st.dataframe(df.tail(20)[['open','high','low','close','volume','RSI']].round(2))
else:
    st.info("👆 Upar stock ka naam daalo aur ANALYZE dabao. Example: RELIANCE, NIFTY, AAPL")
    st.warning("⚠️ Ye tool sirf learning ke liye hai. Real trading se pehle expert se salah lo.")
