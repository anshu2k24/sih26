import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
import sys

# Setup paths to import our historical API
REPO_ROOT = Path(__file__).resolve().parent
sys.path.append(str(REPO_ROOT / "scripts"))
sys.path.append(str(REPO_ROOT / "src"))

try:
    from nwis_api import NWISHistoricalAPI
except ImportError:
    st.error("Failed to load NWISHistoricalAPI. Please run from repo root.")
    st.stop()

st.set_page_config(page_title="eRTMAC-NWIS Demo", layout="wide")

@st.cache_resource
def load_api():
    verified_path = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"
    if not verified_path.exists():
        st.error(f"Missing {verified_path}")
        st.stop()
    return NWISHistoricalAPI(str(verified_path))

api = load_api()

# ---------------------------------------------------------
# SESSION STATE FOR DEMO SCENARIOS
# ---------------------------------------------------------
if 'demo_well' not in st.session_state: st.session_state['demo_well'] = "NO 15/9-19 ST2"
if 'demo_md' not in st.session_state: st.session_state['demo_md'] = 3000.0
if 'demo_radius' not in st.session_state: st.session_state['demo_radius'] = 100.0
if 'demo_filter' not in st.session_state: st.session_state['demo_filter'] = "ALL"

def set_scenario(well, md, radius, ev_filter):
    st.session_state['demo_well'] = well
    st.session_state['demo_md'] = md
    st.session_state['demo_radius'] = radius
    st.session_state['demo_filter'] = ev_filter

# Sidebar
st.sidebar.title("NWIS Configuration")

st.sidebar.subheader("One-Click Demo Scenarios")
st.sidebar.button("Mud Loss Proximity", on_click=set_scenario, args=("NO 15/9-19 ST2", 2900.0, 150.0, "FORMATION_MUD_LOSS"))
st.sidebar.button("Tight Hole Proximity", on_click=set_scenario, args=("NO 15/9-19 A", 3250.0, 100.0, "Tight Hole"))
st.sidebar.button("Stuck Pipe Proximity", on_click=set_scenario, args=("NO 15/9-F-11 B", 2600.0, 200.0, "Stuck Pipe"))

st.sidebar.markdown("---")
st.sidebar.subheader("Manual Context")

all_wells = sorted(api.df_events['wellbore_id'].dropna().unique().tolist())
all_event_types = ["ALL"] + sorted(api.df_events['event_type'].dropna().unique().tolist())

# Selectboxes that default to session state
active_well = st.sidebar.selectbox("Active Well ID", all_wells, index=all_wells.index(st.session_state['demo_well']) if st.session_state['demo_well'] in all_wells else 0)
current_md = st.sidebar.number_input("Current MD (m)", min_value=0.0, value=st.session_state['demo_md'], step=10.0)
radius = st.sidebar.selectbox("Depth Radius (m)", [25.0, 50.0, 100.0, 150.0, 200.0, 250.0, 500.0], index=[25.0, 50.0, 100.0, 150.0, 200.0, 250.0, 500.0].index(st.session_state['demo_radius']))
event_filter = st.sidebar.selectbox("Filter Historical Event", all_event_types, index=all_event_types.index(st.session_state['demo_filter']))

# Query API
evt = event_filter if event_filter != "ALL" else None
result = api.get_intelligence_by_depth(active_well, current_md, radius, evt)

# ---------------------------------------------------------
# MAIN LAYOUT
# ---------------------------------------------------------
st.title("eRTMAC-NWIS: Nearby Wells Intelligence System")
st.markdown("*An AI-Powered Offset Well Knowledge and Decision Support Platform*")

st.info("**Why this matters:** This Historical Intelligence layer warns drilling engineers when they are approaching depths where severe operational issues (like Mud Losses or Stuck Pipe) occurred in offset wells. This institutional memory provides immediate situational awareness based on explicitly verified DDR evidence, allowing engineers to proactively deploy proven mitigations before an incident happens.")

col1, col2 = st.columns([2, 1])

with col1:
    st.header("HISTORICAL INTELLIGENCE")
    if result["nearby_events"]:
        st.warning(f"**{result['risk_summary']}**")
        st.write(f"**Relevant Offset Wells:** {', '.join(result['relevant_wells'])}")
        
        # Depth Visualization
        df_chart = pd.DataFrame(result["nearby_events"])
        # Create an Altair chart
        c = alt.Chart(df_chart).mark_circle(size=100).encode(
            y=alt.Y('onset_md:Q', title='Measured Depth (m)', scale=alt.Scale(reverse=True, domain=[current_md - radius - 50, current_md + radius + 50])),
            x=alt.X('depth_distance_m:Q', title='Distance from Active Well (m)'),
            color='event_type:N',
            tooltip=['offset_wellbore', 'event_type', 'onset_md', 'depth_distance_m']
        ).properties(height=300, title="Event Proximity Profile")
        
        # Add horizontal line for current MD
        rule = alt.Chart(pd.DataFrame({'md': [current_md]})).mark_rule(color='red', strokeDash=[5,5]).encode(y='md:Q')
        st.altair_chart(c + rule, use_container_width=True)

        # Event List
        st.subheader("Nearby Historical Events")
        for ev in result["nearby_events"]:
            with st.expander(f"{ev['event_type']} in {ev['offset_wellbore']} @ {ev['onset_md']}m (Distance: {ev['depth_distance_m']:.1f}m)"):
                st.write(f"**Primary Evidence:** {ev['primary_evidence']}")
                st.write(f"**Mitigation Applied:** {ev['mitigation']}")
                st.write(f"**Resolution:** {ev['resolution']}")
                st.write(f"**Source DDR Record:** `{ev['source_ddr_record']}`")
    else:
        st.success(f"**{result['risk_summary']}**")
        st.write("Drilling path appears historically clear of reported incidents within this specific depth window and well group.")

with col2:
    st.header("Future Predictive Layer")
    st.error("STATUS: PREDICTIVE ML BLOCKED\n\nREASON: Real OIL/eRTMAC telemetry not provided.")
    st.info("This section is securely locked to preserve scientific integrity. No synthetic data, fabricated probabilities, or fake risk scores will be displayed.")
    st.markdown("""
    **Required Inputs to Unlock:**
    - High-frequency WITSML/eRTMAC telemetry
    - Real-time DDR synchronization
    - >= 5 Positive Offset Wells
    
    Once ingested, causal machine learning models (e.g., LightGBM) will provide real-time probabilistic risk forecasting here.
    """)

st.markdown("---")
st.caption(f"Provenance Contract: {result['provenance']}")
