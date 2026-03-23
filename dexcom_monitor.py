import streamlit as st
from pydexcom import Dexcom
import pandas as pd
import altair as alt
import time

# 1. Page Config & Custom Styling
st.set_page_config(page_title="My Glucose Center", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 45px; color: #5271ff; }
    </style>
    """, unsafe_allow_html=True)

# 2. Secure Credential Handling
# To run locally, create a folder named .streamlit and a file named secrets.toml
# Content of secrets.toml: 
# DEXCOM_USER = "your_user"
# DEXCOM_PASS = "your_pass"
# IS_OUS = false
try:
    USER = st.secrets["DEXCOM_USER"]
    PASS = st.secrets["DEXCOM_PASS"]
    OUS = st.secrets["IS_OUS"]
except Exception:
    st.error("Credentials not found! Please set up st.secrets.")
    st.stop()

# 3. Cached Data Fetching (Reduces server load)
@st.cache_data(ttl=300) # Only fetch from Dexcom every 5 minutes
def fetch_dexcom_data(hours_back):
    region = "eu" if OUS else "us"
    dexcom = Dexcom(username=USER, password=PASS, region=region)
    
    current = dexcom.get_current_glucose_reading()
    # Try 'minutes' if your pydexcom version is older
    try:
        history = dexcom.get_glucose_readings(minutes=hours_back * 60, max_count=288)
    except TypeError:
        history = dexcom.get_glucose_readings(period=hours_back * 60, max_count=288)
        
    return current, history

# --- Dashboard Logic ---
st.title("🩸 Glucose Command Center")

# Sidebar Controls
hours = st.sidebar.slider("View History (Hours)", 1, 24, 6)
low_limit = st.sidebar.number_input("Low Target", value=70)
high_limit = st.sidebar.number_input("High Target", value=180)

current_reading, readings = fetch_dexcom_data(hours)

if current_reading:
    # Alert Styling
    if current_reading.value <= low_limit:
        st.error(f"🚨 LOW ALERT: {current_reading.value} mg/dL")
        st.markdown("<style>.stApp {background-color: #4a0000 !important;}</style>", unsafe_allow_html=True)

    # Metrics Row
    df = pd.DataFrame([{"Time": r.datetime, "Glucose": r.value} for r in readings])
    avg = df['Glucose'].mean()
    tir = (len(df[(df['Glucose'] >= low_limit) & (df['Glucose'] <= high_limit)]) / len(df)) * 100
    gmi = 3.31 + (0.02392 * avg)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current", f"{current_reading.value}", current_reading.trend_arrow)
    c2.metric("Average", f"{int(avg)}")
    c3.metric("In Range", f"{tir:.1f}%")
    c4.metric("Est. A1c", f"{gmi:.1f}%")

    # The Interactive Chart
    chart = alt.Chart(df).mark_line(point=True, color='#5271ff').encode(
        x='Time:T',
        y=alt.Y('Glucose:Q', scale=alt.Scale(domain=[40, 400])),
        tooltip=['Time', 'Glucose']
    ).properties(height=400).interactive()

    # Target Range Shading
    range_box = alt.Chart(pd.DataFrame([{'s': 70, 'e': 180}])).mark_rect(opacity=0.1, color='green').encode(y='s:Q', y2='e:Q')
    
    st.altair_chart(range_box + chart, use_container_width=True)

    # Recent Log Table
    with st.expander("Show Recent Log"):
        st.table(df.head(10))

else:
    st.warning("Waiting for sensor data...")

# Auto-refresh loop
time.sleep(300)
st.rerun()
