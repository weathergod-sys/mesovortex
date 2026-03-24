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
    OUS = bool(st.secrets["IS_OUS"])
except Exception:
    st.error("Credentials missing! Please set them in Streamlit Cloud Secrets.")
    st.stop()

# 3. Data Fetching with Status Reporting
@st.cache_data(ttl=300)
def fetch_dexcom_data(hours_back):
    target_region = "ous" if OUS else "us"
    status = "Unknown"
    
    try:
        dexcom = Dexcom(username=USER, password=PASS, region=target_region)
        status = "✅ Connected to Dexcom"
        
        current = dexcom.get_current_glucose_reading()
        
        try:
            history = dexcom.get_glucose_readings(minutes=hours_back * 60, max_count=288)
        except TypeError:
            history = dexcom.get_glucose_readings(period=hours_back * 60, max_count=288)
            
        return current, history, status
        try:
    dexcom = Dexcom(username=USER, password=PASS, region=target_region)
    current = dexcom.get_current_glucose_reading()
    
    # DEBUG LOGS
    if current is None:
        print("DEBUG: Authentication successful, but get_current_glucose_reading() returned None.")
    else:
        print(f"DEBUG: Successfully fetched reading: {current.value}")
    except Exception as e:
        return None, None, f"❌ Error: {str(e)}"

# --- Sidebar Status ---
st.sidebar.header("System Status")
hours = st.sidebar.slider("View History (Hours)", 1, 24, 6)

# Fetch data
result, readings, conn_status = fetch_dexcom_data(hours)

st.sidebar.markdown(f"**Connection:** {conn_status}")

# --- Logic for "Unavailable" Data ---
if result is None:
    st.title("🩸 Glucose Command Center")
    st.warning("Sensor data is currently unavailable.")
    
    with st.expander("Why am I seeing this?"):
        st.write("""
        1. **Check Dexcom App:** Ensure 'Share' is toggled **ON** in your phone app.
        2. **Followers:** You must have at least one follower invited (even if they haven't accepted).
        3. **Region:** If you are outside the USA, ensure `IS_OUS = true` in secrets.
        4. **Sensor Status:** If your sensor is warming up or in 'Sensor Error' mode, no data will appear here.
        """)
else:
    # Original Dashboard Logic
    st.title("🩸 Glucose Command Center")
    # ... (rest of your metrics and chart code)
