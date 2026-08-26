import streamlit as st
import pandas as pd
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent
sys.path.append(str(REPO_ROOT / "scripts"))
sys.path.append(str(REPO_ROOT / "src"))

try:
    from nwis_api import NWISHistoricalAPI
except ImportError:
    st.error("Failed to load NWISHistoricalAPI. Please run from repo root.")
    st.stop()

st.set_page_config(page_title="eRTMAC-NWIS", layout="wide")

@st.cache_resource
def load_api():
    verified_path = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"
    if not verified_path.exists():
        st.error(f"Missing {verified_path}")
        st.stop()
    return NWISHistoricalAPI(str(verified_path))

api = load_api()

def check_ml_readiness():
    from ertmac.ml.ingestion import IngestionValidator
    events_path = REPO_ROOT / "data" / "raw" / "oil_ertmac_events.parquet"
    sensors_path = REPO_ROOT / "data" / "raw" / "oil_ertmac_sensors.parquet"
    if not events_path.exists() or not sensors_path.exists():
        return False, "OIL/eRTMAC data not found"
    try:
        df_events = pd.read_parquet(events_path)
        df_sensors = pd.read_parquet(sensors_path)
        validator = IngestionValidator()
        is_ready, msg = validator.check_readiness(df_events, df_sensors)
        return is_ready, msg
    except Exception as e:
        return False, f"Error: {e}"

ml_ready, ml_msg = check_ml_readiness()

st.title("eRTMAC-NWIS")

st.sidebar.header("Drilling Parameters")
all_wells = sorted(api.df_events['wellbore_id'].dropna().unique().tolist())
active_well = st.sidebar.selectbox("Active Well ID", all_wells, index=0)
current_md = st.sidebar.number_input("Current MD (m)", min_value=0.0, value=3000.0, step=10.0)
radius = st.sidebar.selectbox("Depth Radius (m)", [25.0, 50.0, 100.0, 150.0, 200.0, 250.0, 500.0], index=2)

result = api.get_intelligence_by_depth(active_well, current_md, radius)

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Historical NWIS Intelligence")
    st.write(f"**{result['risk_summary']}**")
    
    if result["nearby_events"]:
        st.subheader("Nearby Historical Events")
        for ev in result["nearby_events"]:
            with st.expander(f"{ev['event_type']} @ {ev['onset_md']}m (Distance: {ev['depth_distance_m']:.1f}m) in {ev['offset_wellbore']}"):
                st.write(f"**Evidence:** {ev['primary_evidence']}")
                st.write(f"**Mitigation:** {ev['mitigation']}")
                st.write(f"**Source Record:** `{ev['source_ddr_record']}`")

with col2:
    st.header("Predictive Risk")
    if ml_ready:
        st.success("ML Pipeline Active")
        st.info("Risk scores will be calculated here using the loaded causal models.")
        # Future: model.predict_proba(current_sensor_payload)
    else:
        st.error("ML BLOCKED — NEED REAL DATA")
        st.write(f"**Status:** {ml_msg}")
        st.markdown("""
        **Required for activation:**
        - `data/raw/oil_ertmac_events.parquet`
        - `data/raw/oil_ertmac_sensors.parquet`
        - Minimum 5 independent well groups with verified events and overlapping telemetry.
        """)
