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
    # Ensure OUS is a boolean
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
        
        try:
            history = dexcom.get_glucose_readings(minutes=hours_back * 60, max_count=288)
        except Exception:
            history = dexcom.get_glucose_readings(period=hours_back * 60, max_count=288)
            
        return current, history, status
    except Exception as e:
        return None, None, f"❌ Error: {str(e)}"

# --- UI Layout ---
st.title("🩸 Glucose Command Center")

# Sidebar Controls
st.sidebar.header("System Status")
hours = st.sidebar.slider("View History (Hours)", 1, 24, 6)
st.sidebar.markdown("---")
st.sidebar.header("Target Range")
low_limit = st.sidebar.number_input("Low Limit (mg/dL)", value=70)
high_limit = st.sidebar.number_input("High Limit (mg/dL)", value=180)

# Execute fetch
result, readings, conn_status = fetch_dexcom_data(hours)
st.sidebar.markdown(f"**Connection:** {conn_status}")

if result is None:
    st.warning("Sensor data is currently unavailable.")
    st.info("💡 Ensure 'Share' is ON in your mobile app and you have at least one 'Follower' invited.")
else:
    # 4. Calculate Advanced Metrics
    if readings:
        df = pd.DataFrame([{"Time": r.datetime, "Glucose": r.value} for r in readings])
        
        # Calculate Average
        avg_glucose = df['Glucose'].mean()
        
        # Calculate Time in Range (TIR)
        in_range_count = len(df[(df['Glucose'] >= low_limit) & (df['Glucose'] <= high_limit)])
        tir_percentage = (in_range_count / len(df)) * 100
        
        # Calculate GMI (Estimated A1c)
        # Formula: 3.31 + (0.02392 * avg_glucose)
        gmi = 3.31 + (0.02392 * avg_glucose)

        # 5. Display Metrics Bar
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current", f"{result.value}", result.trend_arrow)
        m2.metric("Avg Glucose", f"{int(avg_glucose)}")
        m3.metric("Time in Range", f"{tir_percentage:.1f}%")
        m4.metric("Est. A1c (GMI)", f"{gmi:.1f}%")

        # 6. Interactive History Chart
        st.markdown("### Glucose History")
        
        # The main glucose line
        chart = alt.Chart(df).mark_line(point=True, color='#5271ff').encode(
            x='Time:T',
            y=alt.Y('Glucose:Q', scale=alt.Scale(domain=[40, 400])),
            tooltip=['Time', 'Glucose']
        ).properties(height=400).interactive()
        
        # 🟩 Green Target Range Shading
        range_df = pd.DataFrame([{'s': low_limit, 'e': high_limit}])
        range_box = alt.Chart(range_df).mark_rect(opacity=0.1, color='green').encode(
            y='s:Q', y2='e:Q'
        )

        # 🟥 Red "Low" Shading (from 0 to your low_limit)
        low_df = pd.DataFrame([{'s': 0, 'e': low_limit}])
        low_box = alt.Chart(low_df).mark_rect(opacity=0.1, color='red').encode(
            y='s:Q', y2='e:Q'
        )

        # 🟧 Orange "High" Range Shading (from high_limit to 400)
        high_df = pd.DataFrame([{'s': high_limit, 'e': 400}])
        high_box = alt.Chart(high_df).mark_rect(opacity=0.1, color='orange').encode(
            y='s:Q', y2='e:Q'
        )

        # Combine all layers
        # Layering order matters: put boxes first so the line stays on top
        st.altair_chart(low_box + range_box + high_box + chart, use_container_width=True)
        
        with st.expander("Show Recent Log"):
            st.dataframe(df.sort_values(by="Time", ascending=False))
    else:
        st.metric("Current Glucose", f"{result.value}", result.trend_arrow)
        st.warning("No historical data found for the selected time period.")
