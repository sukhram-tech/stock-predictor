import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import ta
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime
import yfinance as yf

st.set_page_config(page_title="FinVista Nexus", layout="wide", page_icon="📊", initial_sidebar_state="collapsed")

API_KEY = "1bc0db9c325f481280365f8a685740c2"

st.markdown("""
<style>
    .main {background-color: #0B0E11;}
    .stMetric {background-color: #151A1F; padding: 20px; border-radius: 8px; border: 1px solid #1E2329;}
    .stButton>button {background-color: #F0B90B; color: #0B0E11; border-radius: 4px; font-weight: 600; width: 100%; border: none; padding: 10px;}
    .stButton>button:hover {background-color: #F8D12F;}
    h1 {color: #F0B90B; font-weight: 700; letter-spacing: -1px;}
    h2 {color: #EAECEF; font-weight: 600;}
    .signal-box {padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0px;}
    hr {border-color: #1E2329;}
</style>
""", unsafe_allow_html=True)

def is_indian_stock(symbol):
    indian = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ADANIENT","TATAMOTORS","ITC","WIPRO","LT","AXISBANK","KOTAKBANK","BAJFINANCE","MARUTI","HCLTECH","ASIANPAINT","SUNPHARMA","TITAN","ULTRACEMCO","NIFTY","SENSEX","BANKNIFTY","^NSEI","^BSESN"]
    return symbol.upper().replace(".NS","").replace("^","") in indian

@st.cache_data(ttl=300)
def get_data(symbol):
    try:
        sym = symbol.upper().strip()
        currency = "₹" if is_indian_stock(sym) else "$"
        
        # Indian stocks ke liye yfinance use karo
        if is_indian_stock(sym):
            if sym == "NIFTY": ticker = "^NSEI"
            elif sym == "SENSEX": ticker = "^BSESN"
            elif sym == "BANKNIFTY": ticker = "^NSEBANK"
            else: ticker = sym + ".NS"
            
            stock = yf.Ticker(ticker)
            df = stock.history(period="2y")
            if df.empty:
                return None, None, "No data found for this Indian stock"
            
            df = df.rename(columns={"Open":"open", "High":"high", "Low":"low", "Close":"close", "Volume":"volume"})
            df.index.name = "datetime"
            
            info = {
                "name": stock.info.get("longName", symbol),
                "close": df['close'].iloc[-1],
                "percent_change": ((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100,
                "high": df['high'].iloc[-1],
                "low": df['low'].iloc[-1],
                "open": df['open'].iloc[-1],
                "volume": int(df['volume'].iloc[-1]),
                "high_52": df['high'].rolling(252).max().iloc[-1],
                "low_52": df['low'].rolling(252).min().iloc[-1],
                "currency": currency
            }
        else:
            # US stocks ke liye Twelve Data
            url = f"https://api.twelvedata.com/time_series?symbol={sym}&interval=1day&outputsize=500&apikey={API_KEY}"
            r = requests.get(url).json()
            if "status" in r and r["status"] == "error":
                return None, None, f"API Error: {r['message']}"
            if "values" not in r:
                return None, None, "No data available"
            
            df = pd.DataFrame(r["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.set_index("datetime").sort_index()
            df = df.astype(float)
            
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
                "currency": currency
            }
        
        # Technical indicators - dono ke liye common
        df['EMA20'] = ta.trend.ema_indicator(df['close'], window=20)
        df['EMA50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)
        macd = ta.trend.MACD(df['close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        bb = ta.volatility.BollingerBands(df['close'])
        df['BB_High'] = bb.bollinger_hband()
        df['BB_Low'] = bb.bollinger_lband()
        
        return df, info, None
    except Exception as e:
        return None, None, f"System Error: {str(e)}"

def predict_price(df, days=7):
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

def nexus_signal(df, info):
    score = 0
    signals = []
    rsi = df['RSI'].iloc[-1]
    if rsi < 30:
        score += 2; signals.append("RSI indicates oversold territory below 30")
    elif rsi > 70:
        score -= 2; signals.append("RSI indicates overbought territory above 70")
    else:
        signals.append(f"RSI is neutral at {rsi:.1f}")
    if df['EMA20'].iloc[-1] > df['EMA50'].iloc[-1] and df['EMA20'].iloc[-2] <= df['EMA50'].iloc[-2]:
        score += 3; signals.append("EMA Golden Cross detected: Short-term momentum turning positive")
    elif df['EMA20'].iloc[-1] < df['EMA50'].iloc[-1] and df['EMA20'].iloc[-2] >= df['EMA50'].iloc[-2]:
        score -= 3; signals.append("EMA Death Cross detected: Short-term momentum turning negative")
    if df['MACD'].iloc[-1] > df['MACD_Signal'].iloc[-1] and df['MACD'].iloc[-2] <= df['MACD_Signal'].iloc[-2]:
        score += 2; signals.append("MACD bullish crossover confirmed")
    elif df['MACD'].iloc[-1] < df['MACD_Signal'].iloc[-1]:
        score -= 1; signals.append("MACD remains in bearish territory")
    if info['close'] < df['BB_Low'].iloc[-1]:
        score += 1; signals.append("Price trading below lower Bollinger Band")
    elif info['close'] > df['BB_High'].iloc[-1]:
        score -= 1; signals.append("Price trading above upper Bollinger Band")
    
    if score >= 4:
        verdict = "STRONG BUY"; color = "#0ECB81"; bg = "#0ECB8115"
    elif score >= 2:
        verdict = "BUY"; color = "#0ECB81"; bg = "#0ECB8110"
    elif score <= -4:
        verdict = "STRONG SELL"; color = "#F6465D"; bg = "#F6465D15"
    elif score <= -2:
        verdict = "SELL"; color = "#F6465D"; bg = "#F6465D10"
    else:
        verdict = "NEUTRAL"; color = "#F0B90B"; bg = "#F0B90B10"
    return verdict, color, bg, score, signals

def plot_chart(df, pred_df, symbol, info):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='OHLC', increasing_line_color='#0ECB81', decreasing_line_color='#F6465D'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#F0B90B', width=1.5), name='EMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='#3B82F6', width=1.5), name='EMA 50'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='#474D57', width=1, dash='dot'), name='BB Upper', opacity=0.5), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='#474D57', width=1, dash='dot'), name='BB Lower', fill='tonexty', opacity=0.2), row=1, col=1)
    fig.add_trace(go.Scatter(x=pred_df.index, y=pred_df['Predicted Close'], line=dict(color='#F0B90B', width=2, dash='dash'), name='7D Forecast'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#8B5CF6', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#F6465D", opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#0ECB81", opacity=0.5, row=2, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['MACD'], name='MACD', marker_color='#3B82F6', opacity=0.6), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='#F0B90B', width=2), name='Signal'), row=3, col=1)
    fig.update_layout(template="plotly_dark", height=750, showlegend=True, xaxis_rangeslider_visible=False, hovermode='x unified', paper_bgcolor='#0B0E11', plot_bgcolor='#0B0E11', font=dict(family="Inter, sans-serif", color="#EAECEF"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_yaxes(title_text=f"Price {info['currency']}", row=1, col=1, gridcolor="#1E2329")
    fig.update_yaxes(title_text="RSI", range=[0,100], row=2, col=1, gridcolor="#1E2329")
    fig.update_yaxes(title_text="MACD", row=3, col=1, gridcolor="#1E2329")
    fig.update_xaxes(gridcolor="#1E2329")
    return fig

st.markdown("<h1>FinVista Nexus</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #848E9C; margin-top: -10px;'>Institutional-Grade Market Intelligence Platform</p>", unsafe_allow_html=True)
st.markdown("---")

col1, col2 = st.columns([4,1])
with col1:
    symbol = st.text_input("Symbol", placeholder="Enter ticker: TCS, RELIANCE, NIFTY, AAPL", label_visibility="collapsed")
with col2:
    analyze = st.button("Analyze", use_container_width=True)

if analyze and symbol:
    with st.spinner('Fetching market data...'):
        df, info, error = get_data(symbol)
        if error:
            st.error(error)
        elif df is not None:
            verdict, color, bg, score, signals = nexus_signal(df, info)
            pred_df = predict_price(df, 7)
            
            st.markdown(f"""
            <div class='signal-box' style='background-color: {bg}; border: 1px solid {color};'>
                <h2 style='color: {color}; margin: 0;'>{info['name']}</h2>
                <h3 style='color: {color}; margin: 10px 0 0 0;'>{verdict}</h3>
                <p style='color: #848E9C; margin: 5px 0 0 0;'>Nexus Composite Score: {score}/8</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            delta_color = "normal" if info['percent_change'] >= 0 else "inverse"
            c1.metric("Last Price", f"{info['currency']}{info['close']:.2f}", f"{info['percent_change']:.2f}%", delta_color=delta_color)
            c2.metric("Day Range", f"{info['currency']}{info['low']:.2f} - {info['high']:.2f}")
            c3.metric("Volume", f"{info['volume']:,}")
            c4.metric("52W Range", f"{info['currency']}{info['low_52']:.2f} - {info['high_52']:.2f}")
            
            st.markdown("### Technical Analysis")
            st.plotly_chart(plot_chart(df, pred_df, info['name'], info), use_container_width=True)
            
            tab1, tab2, tab3 = st.tabs(["Signal Breakdown", "Price Forecast", "Key Statistics"])
            
            with tab1:
                for sig in signals:
                    st.markdown(f"• {sig}")
            
            with tab2:
                st.dataframe(pred_df.style.format({f"Predicted Close": f"{info['currency']}"+"{:.2f}"}), use_container_width=True)
                st.caption("Forecast based on linear regression of historical closing prices. Not financial advice.")
            
            with tab3:
                d1, d2, d3 = st.columns(3)
                d1.metric("Current RSI", f"{df['RSI'].iloc[-1]:.2f}")
                d2.metric("20D EMA", f"{info['currency']}{df['EMA20'].iloc[-1]:.2f}")
                d3.metric("50D EMA", f"{info['currency']}{df['EMA50'].iloc[-1]:.2f}")
else:
    st.info("Enter a ticker symbol and click Analyze to generate institutional-grade analysis")
    st.markdown("**Popular Symbols:** TCS, RELIANCE, INFY, HDFCBANK, NIFTY, BANKNIFTY, AAPL, TSLA, MSFT")

st.markdown("---")
st.markdown(f"<p style='text-align: center; color: #474D57; font-size: 12px;'>FinVista Nexus V2.3 | Data as of {datetime.now().strftime('%d %b %Y, %H:%M IST')} | For informational purposes only. Not investment advice.</p>", unsafe_allow_html=True)
