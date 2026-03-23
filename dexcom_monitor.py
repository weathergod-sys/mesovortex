import streamlit as st
from pydexcom import Dexcom
import pandas as pd
import altair as alt

# 1. Page Config
st.set_page_config(page_title="My Glucose Center", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 45px; color: #5271ff; }
    </style>
    """, unsafe_allow_html=True)

# 2. Secure Credential Handling
try:
    USER = st.secrets["DEXCOM_USER"]
    PASS = st.secrets["DEXCOM_PASS"]
    OUS = st.secrets["IS_OUS"]
except Exception:
    st.error("Credentials not found! Check your Streamlit Cloud Secrets settings.")
    st.stop()

# 3. Cached Data Fetching
@st.cache_data(ttl=300) 
def fetch_dexcom_data(hours_back):
    # pydexcom requires exactly "us" or "ous"
    # The previous "eu" was causing the ArgumentError
    target_region = "ous" if OUS else "us"
    
    try:
        dexcom = Dexcom(username=USER, password=PASS, region=target_region)
        current = dexcom.get_current_glucose_reading()
        
        # Handle different library versions for history fetching
        try:
            history = dexcom.get_glucose_readings(minutes=hours_back * 60, max_count=288)
        except TypeError:
            history = dexcom.get_glucose_readings(period=hours_back * 60, max_count=288)
            
        return current, history
    except Exception as e:
        # CRITICAL: We log the error but return None. 
        # Caching a 'None' value is safe; caching a pydexcom Error object is not.
        print(f"Internal Dexcom Error: {e}") 
        return None, None

# --- Dashboard UI ---
st.title("🩸 Glucose Command Center")

hours = st.sidebar.slider("View History (Hours)", 1, 24, 6)
low_limit = st.sidebar.number_input("Low Target", value=70)
high_limit = st.sidebar.number_input("High Target", value=180)

# Fetch data and handle potential connection issues
result, readings = fetch_dexcom_data(hours)

if isinstance(result, Exception):
    st.error(f"Dexcom API Error: {result}")
    st.info("💡 Troubleshooting Checklist:\n"
            "1. Open your Dexcom mobile app and ensure **'Share'** is ON.\n"
            "2. Ensure you have at least one **'Follower'** added (you can invite your own second email).\n"
            "3. If outside the USA, ensure `IS_OUS` is set to `true` in your secrets.")
    st.stop()

current_reading = result

if current_reading and readings:
    # Alert Styling for Lows
    if current_reading.value <= low_limit:
        st.error(f"🚨 LOW ALERT: {current_reading.value} mg/dL")
        st.markdown("<style>.stApp {background-color: #4a0000 !important;}</style>", unsafe_allow_html=True)

    # Calculate Metrics
    df = pd.DataFrame([{"Time": r.datetime, "Glucose": r.value} for r in readings])
    avg = df['Glucose'].mean()
    tir = (len(df[(df['Glucose'] >= low_limit) & (df['Glucose'] <= high_limit)]) / len(df)) * 100
    gmi = 3.31 + (0.02392 * avg)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current", f"{current_reading.value}", current_reading.trend_arrow)
    c2.metric("Average", f"{int(avg)}")
    c3.metric("In Range", f"{tir:.1f}%")
    c4.metric("Est. A1c", f"{gmi:.1f}%")

    # Interactive Chart
    chart = alt.Chart(df).mark_line(point=True, color='#5271ff').encode(
        x='Time:T',
        y=alt.Y('Glucose:Q', scale=alt.Scale(domain=[40, 400])),
        tooltip=['Time', 'Glucose']
    ).properties(height=400).interactive()
    
    range_box = alt.Chart(pd.DataFrame([{'s': low_limit, 'e': high_limit}])).mark_rect(opacity=0.1, color='green').encode(y='s:Q', y2='e:Q')
    st.altair_chart(range_box + chart, use_container_width=True)

    with st.expander("Show Recent Log"):
        st.table(df.head(10))
else:
    st.warning("Sensor data is currently unavailable.")
