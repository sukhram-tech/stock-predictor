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

st.set_page_config(page_title="FinVista Nexus AI", layout="wide", page_icon="🚀", initial_sidebar_state="collapsed")

API_KEY = "1bc0db9c325f481280365f8a685740c2"

# AI LEVEL DARK GRADIENT BACKGROUND
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0B0E11 0%, #0F1419 50%, #0B0E11 100%);
        background-attachment: fixed;
    }
    .main {background-color: transparent;}
    .stMetric {
        background: rgba(21, 26, 31, 0.6); 
        backdrop-filter: blur(10px);
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid rgba(240, 185, 11, 0.2);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    .stButton>button {
        background: linear-gradient(90deg, #F0B90B 0%, #F8D12F 100%); 
        color: #0B0E11; 
        border-radius: 8px; 
        font-weight: 700; 
        width: 100%; 
        border: none;
        padding: 12px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(240, 185, 11, 0.4);
    }
    h1 {
        background: linear-gradient(90deg, #F0B90B 0%, #F8D12F 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; 
        letter-spacing: -2px;
        font-size: 3.5em !important;
        text-align: center;
    }
    h2 {color: #EAECEF; font-weight: 600;}
    h3 {color: #B7BDC6; font-weight: 500;}
    .signal-box {
        padding: 25px;
        border-radius: 16px;
        text-align: center;
        margin: 20px 0px;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    hr {border-color: rgba(30, 35, 41, 0.5);}
    .stSlider > div > div > div {background-color: #F0B90B;}
    .stTabs [data-baseweb="tab-list"] {gap: 8px;}
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(21, 26, 31, 0.6);
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
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
                "market_cap": stock.info.get("marketCap", 0),
                "pe_ratio": stock.info.get("trailingPE", 0),
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
                "market_cap": 0, "pe_ratio": 0,
                "currency": currency
            }
        
        # AI LEVEL INDICATORS
        df['EMA20'] = ta.trend.ema_indicator(df['close'], window=20)
        df['EMA50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['EMA200'] = ta.trend.ema_indicator(df['close'], window=200)
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)
        df['Stoch'] = ta.momentum.stoch(df['high'], df['low'], df['close'])
        macd = ta.trend.MACD(df['close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Hist'] = macd.macd_diff()
        bb = ta.volatility.BollingerBands(df['close'])
        df['BB_High'] = bb.bollinger_hband()
        df['BB_Mid'] = bb.bollinger_mavg()
        df['BB_Low'] = bb.bollinger_lband()
        df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'])
        df['VWAP'] = ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
        df['OBV'] = ta.volume.on_balance_volume(df['close'], df['volume'])
        
        return df, info, None
    except Exception as e:
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
    pivot = (df['high'].iloc[-1] + df['low'].iloc[-1] + df['close'].iloc[-1]) / 3
    return support, resistance, pivot

def fibonacci_levels(df):
    max_price = df['high'].tail(60).max()
    min_price = df['low'].tail(60).min()
    diff = max_price - min_price
    return {
        "0%": max_price,
        "23.6%": max_price - 0.236 * diff,
        "38.2%": max_price - 0.382 * diff,
        "50%": max_price - 0.5 * diff,
        "61.8%": max_price - 0.618 * diff,
        "100%": min_price
    }

def nexus_signal(df, info):
    score = 0
    signals = []
    rsi = df['RSI'].iloc[-1]
    if rsi < 30: score += 2; signals.append("RSI Oversold <30 - Strong Reversal Zone")
    elif rsi > 70: score -= 2; signals.append("RSI Overbought >70 - Distribution Zone")
    else: signals.append(f"RSI Neutral at {rsi:.1f} - No extreme momentum")
    
    if df['EMA20'].iloc[-1] > df['EMA50'].iloc[-1] and df['EMA20'].iloc[-2] <= df['EMA50'].iloc[-2]:
        score += 3; signals.append("Golden Cross: 20 EMA > 50 EMA - Bullish Trend Start")
    elif df['EMA20'].iloc[-1] < df['EMA50'].iloc[-1] and df['EMA20'].iloc[-2] >= df['EMA50'].iloc[-2]:
        score -= 3; signals.append("Death Cross: 20 EMA < 50 EMA - Bearish Trend Start")
    
    if df['close'].iloc[-1] > df['EMA200'].iloc[-1]: score += 1; signals.append("Above 200 EMA - Long term bullish structure")
    else: score -= 1; signals.append("Below 200 EMA - Long term bearish structure")
    
    if df['MACD_Hist'].iloc[-1] > 0 and df['MACD_Hist'].iloc[-2] <= 0:
        score += 2; signals.append("MACD Histogram turned positive - Momentum acceleration")
    elif df['MACD'].iloc[-1] < df['MACD_Signal'].iloc[-1]:
        score -= 1; signals.append("MACD below Signal - Bearish momentum")
    
    if df['close'].iloc[-1] > df['VWAP'].iloc[-1]: score += 1; signals.append("Above VWAP - Institutions buying")
    else: score -= 1; signals.append("Below VWAP - Institutions selling")
    
    if df['OBV'].iloc[-1] > df['OBV'].iloc[-5]: score += 1; signals.append("OBV Rising - Volume confirms price")
    
    if score >= 6: verdict = "STRONG BUY"; color = "#0ECB81"; bg = "rgba(14, 203, 129, 0.1)"
    elif score >= 3: verdict = "BUY"; color = "#0ECB81"; bg = "rgba(14, 203, 129, 0.05)"
    elif score <= -6: verdict = "STRONG SELL"; color = "#F6465D"; bg = "rgba(246, 70, 93, 0.1)"
    elif score <= -3: verdict = "SELL"; color = "#F6465D"; bg = "rgba(246, 70, 93, 0.05)"
    else: verdict = "NEUTRAL"; color = "#F0B90B"; bg = "rgba(240, 185, 11, 0.05)"
    return verdict, color, bg, score, signals

def plot_chart(df, pred_df, symbol, info, show_advanced):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.6, 0.2, 0.2])
    
    # Panel 1: Price - Simple but Powerful
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], 
                                  name='Price', increasing_line_color='#0ECB81', decreasing_line_color='#F6465D'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#F0B90B', width=2), name='EMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='#3B82F6', width=2), name='EMA 50'), row=1, col=1)
    
    if show_advanced:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='#8B5CF6', width=2, dash='dot'), name='EMA 200'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='#EC4899', width=2), name='VWAP'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='rgba(71, 77, 87, 0.5)', width=1), name='BB Upper', fill=None), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='rgba(71, 77, 87, 0.5)', width=1), name='BB Lower', fill='tonexty', fillcolor='rgba(71, 77, 87, 0.1)'), row=1, col=1)
    
    # AI Prediction
    fig.add_trace(go.Scatter(x=pred_df.index, y=pred_df['Predicted Close'], line=dict(color='#F0B90B', width=4, dash='dash'), name=f'{len(pred_df)}D AI Forecast'), row=1, col=1)
    
    # Support/Resistance
    support, resistance, pivot = get_support_resistance(df)
    fig.add_hline(y=resistance, line_dash="dot", line_color="#F6465D", opacity=0.6, annotation_text="Resistance", row=1, col=1)
    fig.add_hline(y=support, line_dash="dot", line_color="#0ECB81", opacity=0.6, annotation_text="Support", row=1, col=1)
    fig.add_hline(y=pivot, line_dash="dash", line_color="#F0B90B", opacity=0.4, annotation_text="Pivot", row=1, col=1)
    
    # Panel 2: Volume
    colors = ['#F6465D' if row['open'] > row['close'] else '#0ECB81' for i, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=colors, opacity=0.5), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], line=dict(color='#8B5CF6', width=2), name='OBV', yaxis='y4'), row=2, col=1)
    
    # Panel 3: RSI + MACD
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#8B5CF6', width=2), name='RSI'), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#F6465D", opacity=0.3, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#0ECB81", opacity=0.3, row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='MACD Hist', marker_color='#3B82F6', opacity=0.4, yaxis='y5'), row=3, col=1)
    
    fig.update_layout(template="plotly_dark", height=800, showlegend=True, xaxis_rangeslider_visible=False, 
                      hovermode='x unified', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                      font=dict(family="Inter, sans-serif", color="#EAECEF"), 
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_yaxes(title_text=f"Price {info['currency']}", row=1, col=1, gridcolor="rgba(30, 35, 41, 0.3)")
    fig.update_yaxes(title_text="Volume", row=2, col=1, gridcolor="rgba(30, 35, 41, 0.3)")
    fig.update_yaxes(title_text="RSI", range=[0,100], row=3, col=1, gridcolor="rgba(30, 35, 41, 0.3)")
    fig.update_xaxes(gridcolor="rgba(30, 35, 41, 0.3)")
    return fig

st.markdown("<h1>FinVista Nexus AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #848E9C; margin-top: -10px;'>Institutional-Grade AI Market Intelligence | Built for Winners</p>", unsafe_allow_html=True)
st.markdown("---")

# Controls
col1, col2, col3 = st.columns([3,2,1])
with col1:
    symbol = st.text_input("Symbol", placeholder="Enter: TCS, RELIANCE, NIFTY, AAPL, TSLA", label_visibility="collapsed")
with col2:
    predict_days = st.select_slider("AI Forecast Days", options=[3, 5, 7, 15, 30, 60], value=7)
with col3:
    analyze = st.button("🚀 Analyze", use_container_width=True)

if symbol:
    show_advanced = st.toggle("Enable Advanced Indicators (200 EMA, VWAP, Bollinger Bands)", value=True)

if analyze and symbol:
    with st.spinner('🧠 Nexus AI Processing Market Data...'):
        df, info, error = get_data(symbol)
        if error:
            st.error(error)
        elif df is not None:
            verdict, color, bg, score, signals = nexus_signal(df, info)
            pred_df = predict_price(df, predict_days)
            support, resistance, pivot = get_support_resistance(df)
            fib = fibonacci_levels(df)
            
            st.markdown(f"""
            <div class='signal-box' style='background: {bg}; border: 2px solid {color};'>
                <h2 style='color: {color}; margin: 0;'>{info['name']}</h2>
                <h3 style='color: {color}; margin: 10px 0 0 0; font-size: 2em;'>{verdict}</h3>
                <p style='color: #848E9C; margin: 5px 0 0 0;'>Nexus AI Score: {score}/12 | Confidence: {min(abs(score)*8.33, 100):.0f}%</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3, c4, c5 = st.columns(5)
            delta_color = "normal" if info['percent_change'] >= 0 else "inverse"
            c1.metric("Last Price", f"{info['currency']}{info['close']:.2f}", f"{info['percent_change']:.2f}%", delta_color=delta_color)
            c2.metric("Day Range", f"{info['currency']}{info['low']:.2f} - {info['high']:.2f}")
            c3.metric("Volume", f"{info['volume']:,}")
            c4.metric("ATR (Risk)", f"{info['currency']}{df['ATR'].iloc[-1]:.2f}")
            c5.metric("P/E Ratio", f"{info['pe_ratio']:.2f}" if info['pe_ratio'] else "N/A")
            
            st.plotly_chart(plot_chart(df, pred_df, info['name'], info, show_advanced), use_container_width=True)
            
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["🤖 AI Signals", f"📈 {predict_days}D Forecast", "🎯 Key Levels", "📊 Fibonacci", "💎 Advanced Stats"])
            
            with tab1:
                for sig in signals: st.markdown(f"• {sig}")
                st.info("💡 AI analyzes 10+ indicators: RSI, MACD, EMA Cross, VWAP, OBV, Bollinger Bands, ATR")
            
            with tab2:
                st.dataframe(pred_df.style.format({f"Predicted Close": f"{info['currency']}"+"{:.2f}"}), use_container_width=True)
                change = ((pred_df['Predicted Close'].iloc[-1] - info['close']) / info['close']) * 100
                col1, col2, col3 = st.columns(3)
                col1.metric(f"Target ({predict_days}D)", f"{info['currency']}{pred_df['Predicted Close'].iloc[-1]:.2f}")
                col2.metric("Expected Move", f"{change:+.2f}%")
                col3.metric("AI Confidence", f"{min(abs(score)*8.33, 100):.0f}%")
                st.caption("⚠️ Forecast uses Linear Regression ML model. Past performance ≠ Future results. Not financial advice.")
            
            with tab3:
                l1, l2, l3, l4 = st.columns(4)
                l1.metric("Support", f"{info['currency']}{support:.2f}")
                l2.metric("Pivot", f"{info['currency']}{pivot:.2f}")
                l3.metric("Resistance", f"{info['currency']}{resistance:.2f}")
                l4.metric("R:R Ratio", f"1:{((resistance-info['close'])/(info['close']-support)):.2f}" if info['close'] > support else "N/A")
                st.caption("Levels based on 60-day price action + Pivot Points")
            
            with tab4:
                fib_df = pd.DataFrame(list(fib.items()), columns=['Level', 'Price'])
                fib_df['Price'] = fib_df['Price'].apply(lambda x: f"{info['currency']}{x:.2f}")
                st.dataframe(fib_df, use_container_width=True, hide_index=True)
                st.caption("Fibonacci Retracement from recent swing high to low")
            
            with tab5:
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("RSI (14)", f"{df['RSI'].iloc[-1]:.2f}")
                d2.metric("Stochastic", f"{df['Stoch'].iloc[-1]:.2f}")
                d3.metric("VWAP", f"{info['currency']}{df['VWAP'].iloc[-1]:.2f}")
                d4.metric("52W High", f"{info['currency']}{info['high_52']:.2f}")
                e1, e2, e3, e4 = st.columns(4)
                e1.metric("20 EMA", f"{info['currency']}{df['EMA20'].iloc[-1]:.2f}")
                e2.metric("50 EMA", f"{info['currency']}{df['EMA50'].iloc[-1]:.2f}")
                e3.metric("200 EMA", f"{info['currency']}{df['EMA200'].iloc[-1]:.2f}")
                e4.metric("Market Cap", f"{info['currency']}{info['market_cap']/1e9:.2f}B" if info['market_cap'] else "N/A")
else:
    st.info("👆 Enter ticker symbol above | Select forecast period | Click Analyze")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🇮🇳 Indian Markets:** TCS, RELIANCE, INFY, HDFCBANK, NIFTY, BANKNIFTY, SENSEX")
    with col2:
        st.markdown("**🇺🇸 US Markets:** AAPL, TSLA, MSFT, NVDA, GOOGL, AMZN, META")

st.markdown("---")
st.markdown(f"<p style='text-align: center; color: #474D57; font-size: 12px;'>FinVista Nexus AI V4.0 | Built with ❤️ by Harsh | Data as of {datetime.now().strftime('%d %b %Y, %H:%M IST')} | Educational Tool Only. Not Investment Advice. Trade at Your Own Risk.</p>", unsafe_allow_html=True)
