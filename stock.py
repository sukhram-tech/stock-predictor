import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import ta
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import yfinance as yf

st.set_page_config(page_title="FinVista Nexus V3", layout="wide", page_icon="📊", initial_sidebar_state="collapsed")

API_KEY = "1bc0db9c325f481280365f8a685740c2"

st.markdown("""
<style>
    .main {background-color: #0B0E11;}
    .stMetric {background-color: #151A1F; padding: 20px; border-radius: 8px; border: 1px solid #1E2329;}
    .stButton>button {background-color: #F0B90B; color: #0B0E11; border-radius: 4px; font-weight: 600; width: 100%; border: none;}
    .stButton>button:hover {background-color: #F8D12F;}
    h1 {color: #F0B90B; font-weight: 700; letter-spacing: -1px;}
    h2 {color: #EAECEF; font-weight: 600;}
    .signal-box {padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0px;}
    hr {border-color: #1E2329;}
    .stSlider > div > div > div {background-color: #F0B90B;}
</style>
""", unsafe_allow_html=True)

def is_indian_stock(symbol):
    indian = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ADANIENT","TATAMOTORS","ITC","WIPRO","LT","AXISBANK","KOTAKBANK","BAJFINANCE","MARUTI","HCLTECH","ASIANPAINT","SUNPHARMA","TITAN","ULTRACEMCO","NIFTY","SENSEX","BANKNIFTY","^NSEI","^BSESN","^NSEBANK"]
    return symbol.upper().replace(".NS","").replace("^","") in indian

@st.cache_data(ttl=300)
def get_data(symbol):
    try:
        sym = symbol.upper().strip()
        currency = "₹" if is_indian_stock(sym) else "$"
        
        if is_indian_stock(sym):
            if sym == "NIFTY": ticker = "^NSEI"
            elif sym == "SENSEX": ticker = "^BSESN"
            elif sym == "BANKNIFTY": ticker = "^NSEBANK"
            else: ticker = sym + ".NS"
            stock = yf.Ticker(ticker)
            df = stock.history(period="2y")
            if df.empty: return None, None, "No data found for this Indian stock"
            df = df.rename(columns={"Open":"open", "High":"high", "Low":"low", "Close":"close", "Volume":"volume"})
            df.index.name = "datetime"
            info = {
                "name": stock.info.get("longName", symbol),
                "close": df['close'].iloc[-1],
                "percent_change": ((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100,
                "high": df['high'].iloc[-1], "low": df['low'].iloc[-1], "open": df['open'].iloc[-1],
                "volume": int(df['volume'].iloc[-1]),
                "high_52": df['high'].rolling(252).max().iloc[-1],
                "low_52": df['low'].rolling(252).min().iloc[-1],
                "currency": currency
            }
        else:
            url = f"https://api.twelvedata.com/time_series?symbol={sym}&interval=1day&outputsize=500&apikey={API_KEY}"
            r = requests.get(url).json()
            if "status" in r and r["status"] == "error": return None, None, f"API Error: {r['message']}"
            if "values" not in r: return None, None, "No data available"
            df = pd.DataFrame(r["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.set_index("datetime").sort_index().astype(float)
            q_url = f"https://api.twelvedata.com/quote?symbol={sym}&apikey={API_KEY}"
            q = requests.get(q_url).json()
            info = {
                "name": q.get("name", symbol), "close": float(q.get("close", 0)),
                "percent_change": float(q.get("percent_change", 0)), "high": float(q.get("high", 0)),
                "low": float(q.get("low", 0)), "open": float(q.get("open", 0)),
                "volume": int(float(q.get("volume", 0))),
                "high_52": float(q.get("fifty_two_week", {}).get("high", 0)),
                "low_52": float(q.get("fifty_two_week", {}).get("low", 0)),
                "currency": currency
            }
        
        # Advanced Indicators
        df['EMA20'] = ta.trend.ema_indicator(df['close'], window=20)
        df['EMA50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['EMA200'] = ta.trend.ema_indicator(df['close'], window=200)
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)
        macd = ta.trend.MACD(df['close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Hist'] = macd.macd_diff()
        bb = ta.volatility.BollingerBands(df['close'])
        df['BB_High'] = bb.bollinger_hband()
        df['BB_Low'] = bb.bollinger_lband()
        df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'])
        df['VWAP'] = ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
        
        return df, info, None
    exception as e:
        return None, None, f"System Error: {str(e)}"

def predict_price(df, days):
    df_pred = df[['close']].copy()
    df_pred['days'] = range(len(df_pred))
    X = df_pred[['days']]
    y = df_pred['close']
    model = LinearRegression()
    model.fit(X, y)
    future_days = np.array(range(len(df_pred), len(df_pred) + days)).reshape(-1, 1)
    predictions = model.predict(future_days)
    last_date = df.index[-1]
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days)
    pred_df = pd.DataFrame({'Predicted Close': predictions}, index=future_dates)
    return pred_df

def get_support_resistance(df):
    recent = df['close'].tail(60)
    resistance = recent.max()
    support = recent.min()
    return support, resistance

def nexus_signal(df, info):
    score = 0
    signals = []
    rsi = df['RSI'].iloc[-1]
    if rsi < 30: score += 2; signals.append("RSI indicates oversold territory below 30 - Potential reversal zone")
    elif rsi > 70: score -= 2; signals.append("RSI indicates overbought territory above 70 - Caution advised")
    else: signals.append(f"RSI is neutral at {rsi:.1f}")
    
    if df['EMA20'].iloc[-1] > df['EMA50'].iloc[-1] and df['EMA20'].iloc[-2] <= df['EMA50'].iloc[-2]:
        score += 3; signals.append("EMA Golden Cross: 20 EMA crossed above 50 EMA - Bullish momentum")
    elif df['EMA20'].iloc[-1] < df['EMA50'].iloc[-1] and df['EMA20'].iloc[-2] >= df['EMA50'].iloc[-2]:
        score -= 3; signals.append("EMA Death Cross: 20 EMA crossed below 50 EMA - Bearish momentum")
    
    if df['close'].iloc[-1] > df['EMA200'].iloc[-1]:
