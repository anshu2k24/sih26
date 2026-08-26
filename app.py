import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Setup paths to import our historical API
REPO_ROOT = Path(__file__).resolve().parent
sys.path.append(str(REPO_ROOT / "scripts"))
try:
    from nwis_api import NWISHistoricalAPI
except ImportError:
    st.error("Failed to load NWISHistoricalAPI. Please run from repo root.")
    st.stop()

# Basic Page Config (Minimal styling as requested)
st.set_page_config(page_title="NWIS Prototype", layout="wide")
st.title("eRTMAC-NWIS: Historical Intelligence Prototype")
st.markdown("**Status:** Historical Retrieval (ACTIVE) | Predictive ML (BLOCKED AWAITING REAL SENSOR DATA)")

# Data Loader
@st.cache_resource
def load_api():
    verified_path = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"
    if not verified_path.exists():
        st.error(f"Missing {verified_path}")
        st.stop()
    return NWISHistoricalAPI(str(verified_path))

api = load_api()
all_wells = sorted(api.df_events['wellbore_id'].dropna().unique().tolist())
all_event_types = ["ALL"] + sorted(api.df_events['event_type'].dropna().unique().tolist())

# Sidebar Inputs
st.sidebar.header("Active Well Context")
active_well = st.sidebar.selectbox("Active Well ID", all_wells)
current_md = st.sidebar.number_input("Current MD (m)", min_value=0.0, value=3000.0, step=10.0)
radius = st.sidebar.selectbox("Depth Radius (m)", [25.0, 50.0, 100.0, 250.0], index=2)
event_filter = st.sidebar.selectbox("Filter Historical Event", all_event_types)

# Query Backend
evt = event_filter if event_filter != "ALL" else None
result = api.get_intelligence_by_depth(active_well, current_md, radius, evt)

# Display Risk Summary
st.header("Intelligence Summary")
if result["nearby_events"]:
    st.warning(f"**{result['risk_summary']}**")
    st.write(f"Relevant Offset Wells: {', '.join(result['relevant_wells'])}")
    if result["historical_mitigations"]:
        st.write("**Historical Mitigations Used in this Zone:**")
        for m in result["historical_mitigations"]:
            st.write(f"- {m}")
else:
    st.success(f"**{result['risk_summary']}**")

# Display Depth Timeline / Event List
st.header("Historical Offset Events")
if result["nearby_events"]:
    for ev in result["nearby_events"]:
        with st.expander(f"{ev['event_type']} @ {ev['onset_md']}m (Distance: {ev['depth_distance_m']:.1f}m) in {ev['offset_wellbore']}"):
            st.write(f"**Domain:** {ev['event_domain']}")
            st.write(f"**Primary Evidence:** {ev['primary_evidence']}")
            st.write(f"**Mitigation:** {ev['mitigation']}")
            st.write(f"**Resolution:** {ev['resolution']}")
            st.markdown("---")
            st.write(f"**Similarity Score:** {ev['similarity_score']} ({ev['similarity_reasons']})")
            st.write(f"**Provenance DDR Record:** `{ev['source_ddr_record']}`")
else:
    st.info("No historical events found within the depth window.")

# Disclaimer
st.markdown("---")
st.caption(f"Provenance Contract: {result['provenance']}")
