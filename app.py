import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import time
import requests

REPO_ROOT = Path(__file__).resolve().parent
sys.path.append(str(REPO_ROOT / "scripts"))
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.streaming import SensorStreamClient, SCIENTIFIC_LABEL
from ertmac.api.state import get_app_state

st.set_page_config(page_title="eRTMAC-NWIS Operational Drilling Intelligence Studio", layout="wide")

@st.cache_resource
def load_historical_api():
    from nwis_api import NWISHistoricalAPI
    verified_path = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"
    if not verified_path.exists():
        st.error(f"Missing {verified_path}")
        st.stop()
    return NWISHistoricalAPI(str(verified_path))

api = load_historical_api()
app_state = get_app_state()

def check_ml_readiness():
    events_path = REPO_ROOT / "data" / "raw" / "oil_ertmac_events.parquet"
    sensors_path = REPO_ROOT / "data" / "raw" / "oil_ertmac_sensors.parquet"
    if not events_path.exists() or not sensors_path.exists():
        return False, "OIL/eRTMAC data not found"
    try:
        from ertmac.ml.ingestion import IngestionValidator
        df_events = pd.read_parquet(events_path)
        df_sensors = pd.read_parquet(sensors_path)
        validator = IngestionValidator()
        is_ready, msg, _ = validator.check_readiness(df_events, df_sensors)
        return is_ready, msg
    except Exception as e:
        return False, f"Error: {e}"

ml_ready, ml_msg = check_ml_readiness()

st.title("eRTMAC-NWIS Operational Console")
st.caption(f"**SCIENTIFIC CLASSIFICATION**: `{SCIENTIFIC_LABEL}`")

# Sidebar Controls
st.sidebar.header("Drilling Controls & Well Selection")

available_wells = [w["well_id"] for w in app_state.get_available_wells()]
active_well = st.sidebar.selectbox("Active Well ID", available_wells, index=0)

stream_info = app_state.get_well_state(active_well)
stream_status = stream_info["stream_status"]

if stream_status == "LIVE":
    st.sidebar.success("Stream Status: **🟢 LIVE**")
else:
    st.sidebar.warning(f"Stream Status: **🔴 {stream_status}**")
    st.sidebar.caption("Run `python scripts/run_sensor_stream.py --well 15/9-F-15 --speed 50` to activate live sensor stream.")

current_md = st.sidebar.number_input(
    "Current MD (m)",
    min_value=0.0,
    value=float(stream_info["current_md"]) if stream_info["current_md"] > 0 else 3000.0,
    step=10.0
)
radius = st.sidebar.selectbox("Depth Radius (m)", [25.0, 50.0, 100.0, 150.0, 200.0, 250.0, 500.0], index=2)

st.sidebar.markdown("---")
st.sidebar.markdown("### System Provenance")
st.sidebar.write(f"**Dataset**: Volve USROP Parquet Replay")
st.sidebar.write(f"**Label**: {SCIENTIFIC_LABEL}")
st.sidebar.write("**Backend API**: FastAPI Orchestration Gateway")

# Section 1: Live Sensor Telemetry Dashboard
st.markdown(f"## Live Sensor Telemetry (`{SCIENTIFIC_LABEL}`)")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    if stream_status == "LIVE":
        st.metric("Connection", "🟢 LIVE")
    else:
        st.metric("Connection", "🔴 STREAM DISCONNECTED", delta="-Offline", delta_color="inverse")
with col2:
    st.metric("Active Well", stream_info["well_id"])
with col3:
    st.metric("Current MD", f"{stream_info['current_md']:.2f} m" if stream_info['current_md'] > 0 else f"{current_md:.2f} m")
with col4:
    st.metric("TVD", f"{stream_info['tvd']:.2f} m" if stream_info['tvd'] is not None else "N/A")
with col5:
    st.metric("Samples Received", f"{stream_info['samples_received']}")

# Telemetry Parameter Metrics
rec = stream_info.get("latest_sensor")
if rec:
    st.markdown("### Real-Time Drilling Parameters")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("ROP (m/h)", f"{rec.get('rop', 0.0):.2f}" if rec.get('rop') is not None else "N/A")
        st.metric("WOB (kkgf)", f"{rec.get('wob', 0.0):.2f}" if rec.get('wob') is not None else "N/A")
    with m2:
        st.metric("RPM (rpm)", f"{rec.get('rpm', 0.0):.1f}" if rec.get('rpm') is not None else "N/A")
        st.metric("Torque (kN.m)", f"{rec.get('torque', 0.0):.2f}" if rec.get('torque') is not None else "N/A")
    with m3:
        st.metric("Hookload (kkgf)", f"{rec.get('hookload', 0.0):.2f}" if rec.get('hookload') is not None else "N/A")
        st.metric("SPP (kPa)", f"{rec.get('spp', 0.0):.1f}" if rec.get('spp') is not None else "N/A")
    with m4:
        st.metric("Flow In (L/min)", f"{rec.get('flow_in', 0.0):.1f}" if rec.get('flow_in') is not None else "N/A")
        st.metric("Mud Density (g/cm³)", f"{rec.get('mud_density', 0.0):.2f}" if rec.get('mud_density') is not None else "N/A")

# Live Charts Grid
history_data = app_state.get_sensor_history(active_well)
if history_data["records"]:
    df_chart = pd.DataFrame(history_data["records"])
    st.markdown("### Real-Time Telemetry Trend Charts")
    ch1, ch2 = st.columns(2)
    with ch1:
        st.caption("MD vs ROP (m/h)")
        st.line_chart(df_chart.set_index("md")[["rop"]].dropna())
        st.caption("MD vs WOB (kkgf)")
        st.line_chart(df_chart.set_index("md")[["wob"]].dropna())
        st.caption("MD vs RPM (rpm)")
        st.line_chart(df_chart.set_index("md")[["rpm"]].dropna())
        st.caption("MD vs Torque (kN.m)")
        st.line_chart(df_chart.set_index("md")[["torque"]].dropna())
    with ch2:
        st.caption("MD vs Hookload (kkgf)")
        st.line_chart(df_chart.set_index("md")[["hookload"]].dropna())
        st.caption("MD vs SPP (kPa)")
        st.line_chart(df_chart.set_index("md")[["spp"]].dropna())
        st.caption("MD vs Flow In (L/min)")
        st.line_chart(df_chart.set_index("md")[["flow_in"]].dropna())
        st.caption("MD vs Mud Density (g/cm³)")
        st.line_chart(df_chart.set_index("md")[["mud_density"]].dropna())

st.markdown("---")

# Section 2: Historical Intelligence vs Predictive Risk ML Panel
nwis_result = api.get_intelligence_by_depth(active_well, current_md, radius)
col_intel, col_risk = st.columns([2, 1])

with col_intel:
    st.header("Historical NWIS Intelligence")
    st.write(f"**{nwis_result['risk_summary']}**")
    
    if nwis_result["nearby_events"]:
        st.subheader("Nearby Historical Events")
        for ev in nwis_result["nearby_events"]:
            with st.expander(f"{ev['event_type']} @ {ev['onset_md']}m (Distance: {ev['depth_distance_m']:.1f}m) in {ev['offset_wellbore']}"):
                st.write(f"**Evidence:** {ev['primary_evidence']}")
                st.write(f"**Mitigation:** {ev['mitigation']}")
                st.write(f"**Source Record:** `{ev['source_ddr_record']}`")

with col_risk:
    st.header("Predictive Risk")
    ml_status_info = stream_info["ml"]

    if ml_ready and not ml_status_info.get("is_blocked", True):
        st.success("ML Pipeline Active")
        st.write(f"**Causal Risk Score:** `{ml_status_info.get('risk_score', 0.0):.4f}`")
    else:
        st.error("ML BLOCKED — NEED REAL DATA")
        st.warning("Prediction: UNAVAILABLE")
        st.write(f"**Status:** {ml_status_info.get('gate_reason', ml_msg)}")
        st.markdown("""
        **Required for activation:**
        - `data/raw/oil_ertmac_events.parquet`
        - `data/raw/oil_ertmac_sensors.parquet`
        - Minimum 5 independent well groups with verified events and overlapping telemetry.
        """)

# Rerun for live stream rendering
if stream_status == "LIVE":
    time.sleep(1.0)
    st.rerun()
