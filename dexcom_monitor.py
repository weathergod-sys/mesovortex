import streamlit as st
from pydexcom import Dexcom
import pandas as pd
import altair as alt

# 1. Page Config
st.set_page_config(page_title="My Glucose Center", layout="wide")

# 2. Secure Credential Handling
try:
    USER = st.secrets["DEXCOM_USER"]
    PASS = st.secrets["DEXCOM_PASS"]
    # Force OUS to be a boolean (True/False)
    OUS = bool(st.secrets["IS_OUS"])
except Exception:
    st.error("Credentials missing! Please set them in Streamlit Cloud Secrets.")
    st.stop()

# 3. Data Fetching
@st.cache_data(ttl=300)
def fetch_dexcom_data(hours_back):
    target_region = "ous" if OUS else "us"
    status = "Unknown"
    
    try:
        dexcom = Dexcom(username=USER, password=PASS, region=target_region)
        status = "✅ Connected to Dexcom"
        current = dexcom.get_current_glucose_reading()
        
        # Nested try to handle different pydexcom versions
        try:
            history = dexcom.get_glucose_readings(minutes=hours_back * 60, max_count=288)
        except Exception:
            history = dexcom.get_glucose_readings(period=hours_back * 60, max_count=288)
            
        return current, history, status
    except Exception as e:
        # This is line 45 - it now correctly matches the 'try' at line 31
        return None, None, f"❌ Error: {str(e)}"

# --- UI Layout ---
st.title("🩸 Glucose Command Center")
st.sidebar.header("System Status")
hours = st.sidebar.slider("View History (Hours)", 1, 24, 6)

result, readings, conn_status = fetch_dexcom_data(hours)
st.sidebar.markdown(f"**Connection:** {conn_status}")

if result is None:
    st.warning("Sensor data is currently unavailable.")
    st.info("If connected, ensure 'Share' is ON in your mobile app and you have at least one 'Follower' invited.")
else:
    st.metric("Current Glucose", f"{result.value} mg/dL", result.trend_arrow)
    if readings:
        df = pd.DataFrame([{"Time": r.datetime, "Glucose": r.value} for r in readings])
        chart = alt.Chart(df).mark_line().encode(x='Time:T', y='Glucose:Q')
        st.altair_chart(chart, use_container_width=True)
