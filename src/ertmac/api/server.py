import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Load .env file before any env reads
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Depends, Query
from fastapi.middleware.cors import CORSMiddleware

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
import sys
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.append(str(REPO_ROOT / "scripts"))

from nwis_api import NWISHistoricalAPI
from ertmac.api.state import get_app_state, ApplicationStateManager
from ertmac.api.schemas import (
    WellsResponse,
    WellStateResponse,
    HistoryResponse,
    EventsResponse,
    RiskResponse
)
from ertmac.streaming import SCIENTIFIC_LABEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ertmac.api")

app = FastAPI(
    title="eRTMAC-NWIS Application Backend",
    description=f"Orchestration Backend Layer for SIH 2026 PS121 — {SCIENTIFIC_LABEL}",
    version="2.0.0"
)

# Production Environment Security Validations
is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
auth_required = os.getenv("AUTH_REQUIRED", "false").lower() == "true"

if is_production:
    if not auth_required:
        raise RuntimeError("FATAL CONFIGURATION ERROR: AUTH_REQUIRED must be set to 'true' in production.")
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    if not cors_origins_env or cors_origins_env == "*":
        raise RuntimeError("FATAL CONFIGURATION ERROR: Wildcard '*' in CORS_ORIGINS is strictly forbidden in production. Set explicit frontend origins (e.g. https://app.vercel.app).")
    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
else:
    cors_origins_env = os.getenv("CORS_ORIGINS", "*")
    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] if cors_origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from ertmac.nwis.geospatial import GeospatialIntelligence
from ertmac.nwis.depth_correlation import DepthCorrelationEngine
from ertmac.auth.rbac import get_current_user, UserSession, Permission, require_permission
from ertmac.alerts.engine import global_alert_engine, AlertSeverity, AlertSource
from ertmac.audit.logger import global_audit_service
from ertmac.reports.generator import global_report_generator

# Register the auth router (Phase 1)
from ertmac.api.auth_router import router as auth_router
app.include_router(auth_router)

# Register notifications router (Phase 3)
from ertmac.api.notifications_router import router as notifications_router
app.include_router(notifications_router)

# Register documents router (Phase 4)
from ertmac.api.documents_router import router as documents_router
app.include_router(documents_router)

# Register timeline router (Phase 6)
from ertmac.api.timeline_router import router as timeline_router
app.include_router(timeline_router)

# Register reports router (Phase 7)
from ertmac.api.reports_router import router as reports_router
app.include_router(reports_router)

# Register health & provenance router (Phase 8)
from ertmac.api.health_router import router as health_router
app.include_router(health_router)

# Register analytics router (Phase 9 & 13)
from ertmac.api.analytics_router import router as analytics_router
app.include_router(analytics_router)

# Register PS121 Handwritten Notes OCR router
from ertmac.api.notes_router import router as notes_router
app.include_router(notes_router)

# Register ML Prediction router (Public Endpoints)
from ertmac.api.ml_predict_router import router as ml_predict_router
app.include_router(ml_predict_router)

VERIFIED_EVENTS_PATH = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"
if not is_production and VERIFIED_EVENTS_PATH.exists():
    nwis_historical_api: NWISHistoricalAPI = NWISHistoricalAPI(str(VERIFIED_EVENTS_PATH))
else:
    nwis_historical_api: NWISHistoricalAPI = NWISHistoricalAPI()

geospatial_engine = GeospatialIntelligence()
depth_correlation_engine = DepthCorrelationEngine(
    geospatial_engine=geospatial_engine,
    nwis_historical_api=nwis_historical_api
)


def validate_well_id(well_id: str, state_mgr: ApplicationStateManager = Depends(get_app_state)):
    wells = [w["well_id"] for w in state_mgr.get_available_wells()]
    if well_id not in wells and not well_id.startswith("15/9"):
        raise HTTPException(status_code=404, detail=f"Well ID '{well_id}' not found. Available wells: {wells}")
    return well_id


# ============================================================
# SYSTEM ENDPOINTS
# ============================================================

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": "eRTMAC-NWIS Orchestration Backend",
        "version": "2.0.0",
        "data_source": SCIENTIFIC_LABEL,
        "supabase_configured": bool(os.getenv("SUPABASE_URL")),
        "auth_required": os.getenv("AUTH_REQUIRED", "false").lower() == "true",
    }


# ============================================================
# WELL ENDPOINTS
# ============================================================

@app.get("/api/wells", response_model=WellsResponse, tags=["Wells"])
def list_wells(
    state_mgr: ApplicationStateManager = Depends(get_app_state),
    user: UserSession = Depends(require_permission(Permission.VIEW_WELLS)),
):
    """Returns list of available Volve wells."""
    return {"wells": state_mgr.get_available_wells()}


@app.get("/api/wells/{well_id:path}/state", response_model=WellStateResponse, tags=["Stream State"])
def get_well_state(
    well_id: str = Depends(validate_well_id),
    state_mgr: ApplicationStateManager = Depends(get_app_state),
    user: UserSession = Depends(require_permission(Permission.VIEW_TELEMETRY)),
):
    """Returns current stream state, depth position, latest sensor, and ML gate status."""
    return state_mgr.get_well_state(well_id)


@app.get("/api/wells/{well_id:path}/sensors/latest", tags=["Sensors"])
def get_latest_sensor(
    well_id: str = Depends(validate_well_id),
    state_mgr: ApplicationStateManager = Depends(get_app_state),
    user: UserSession = Depends(require_permission(Permission.VIEW_TELEMETRY)),
):
    """Returns the latest emitted sensor record."""
    latest = state_mgr.get_latest_sensor(well_id)
    if not latest:
        return {"status": "NO_TELEMETRY", "well_id": well_id, "latest_sensor": None}
    return {"status": "SUCCESS", "well_id": well_id, "latest_sensor": latest}


@app.get("/api/wells/{well_id:path}/sensors/history", response_model=HistoryResponse, tags=["Sensors"])
def get_sensor_history(
    well_id: str = Depends(validate_well_id),
    cutoff_md: Optional[float] = Query(None, description="Optional upper MD cutoff limit"),
    state_mgr: ApplicationStateManager = Depends(get_app_state),
    user: UserSession = Depends(require_permission(Permission.VIEW_TELEMETRY)),
):
    """Returns strictly emitted causal sensor records <= cutoff_md. Never exposes future rows."""
    return state_mgr.get_sensor_history(well_id, cutoff_md=cutoff_md)


@app.get("/api/wells/{well_id:path}/events", response_model=EventsResponse, tags=["NWIS Intelligence"])
def get_offset_events(
    well_id: str = Depends(validate_well_id),
    current_md: float = Query(3000.0, description="Current depth position in meters"),
    radius: float = Query(100.0, description="Search radius in meters"),
    event_type: Optional[str] = Query(None, description="Optional event type filter"),
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Retrieves offset DDR / NWIS event intelligence from Equinor Volve semantic dataset."""
    if not nwis_historical_api:
        raise HTTPException(status_code=503, detail="NWIS Historical API dataset unavailable.")
    res = nwis_historical_api.get_intelligence_by_depth(
        active_well_id=well_id,
        current_md=current_md,
        radius=radius,
        event_type=event_type
    )
    return res


@app.get("/api/wells/{well_id:path}/risk", response_model=RiskResponse, tags=["ML Risk"])
def get_risk_status(
    well_id: str = Depends(validate_well_id),
    state_mgr: ApplicationStateManager = Depends(get_app_state),
    user: UserSession = Depends(require_permission(Permission.VIEW_PREDICTIONS)),
):
    """Consumes existing ML result. Returns ML_NOT_READY when readiness gate blocks inference."""
    return state_mgr.get_risk_status(well_id)


@app.get("/api/wells/{well_id:path}/nearby", tags=["Geospatial"])
def get_nearby_wells(
    well_id: str = Depends(validate_well_id),
    radius_km: float = Query(5.0, description="Search radius in kilometers"),
    user: UserSession = Depends(require_permission(Permission.VIEW_WELLS)),
):
    """Returns offset wells within radius_km of active well, sorted by Haversine distance."""
    nearby = geospatial_engine.find_nearby_wells(well_id, radius_km=radius_km)
    active_meta = geospatial_engine.coords.get(well_id, {})
    return {
        "active_well": well_id,
        "active_well_metadata": active_meta,
        "radius_km": radius_km,
        "count": len(nearby),
        "nearby_wells": nearby
    }


@app.get("/api/wells/{well_id:path}/intelligence", tags=["NWIS Intelligence"])
def get_well_full_intelligence(
    well_id: str,
    active_well_id: Optional[str] = Query(None),
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Returns complete historical DDR intelligence, well profile, and all verified events."""
    if not nwis_historical_api:
        raise HTTPException(status_code=503, detail="NWIS Historical API dataset unavailable.")

    res = nwis_historical_api.get_well_full_intelligence(well_id)

    distance_km = None
    distance_m = None

    if geospatial_engine.coordinates_available:
        well_meta = geospatial_engine.coords.get(well_id, {})
        res["well_metadata"] = well_meta

        if active_well_id and active_well_id in geospatial_engine.coords and well_id in geospatial_engine.coords:
            from ertmac.nwis.geospatial import haversine_distance_km
            a_meta = geospatial_engine.coords[active_well_id]
            w_meta = geospatial_engine.coords[well_id]
            if a_meta.get("latitude") and w_meta.get("latitude"):
                dist_km = haversine_distance_km(
                    a_meta["latitude"], a_meta["longitude"],
                    w_meta["latitude"], w_meta["longitude"]
                )
                distance_km = round(dist_km, 3)
                distance_m = round(dist_km * 1000.0, 1)
    else:
        res["well_metadata"] = {"well_id": well_id, "status": "Historical"}

    res["active_well_id"] = active_well_id
    res["distance_km"] = distance_km
    res["distance_m"] = distance_m
    return res


# ============================================================
# KNOWLEDGE REPOSITORY
# ============================================================

@app.get("/api/knowledge/search", tags=["Knowledge Repository"])
def search_knowledge(
    q: Optional[str] = Query(None),
    well_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    document_source: Optional[str] = Query(None),
    min_md: Optional[float] = Query(None),
    max_md: Optional[float] = Query(None),
    sort_by: str = Query("depth_asc"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Searches verified historical drilling knowledge records deterministically."""
    if not nwis_historical_api:
        raise HTTPException(status_code=503, detail="NWIS Historical API dataset unavailable.")

    return nwis_historical_api.search_knowledge(
        q=q,
        well_id=well_id,
        event_type=event_type,
        domain=domain,
        document_source=document_source,
        min_md=min_md,
        max_md=max_md,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )


# ============================================================
# HISTORICAL DEPTH CORRELATION
# ============================================================

@app.get("/api/wells/{active_well_id:path}/historical-proximity", tags=["NWIS Depth Correlation"])
def get_historical_depth_proximity(
    active_well_id: str,
    current_md: float = Query(3000.0),
    radius_km: float = Query(5.0),
    depth_window_m: float = Query(50.0),
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """
    Deterministically correlates active well current_md position against historical events
    in nearby offset wells. SURFACES PROXIMITY ALERTS WITH EXPLICIT NOT-A-PREDICTION DISCLAIMERS.
    """
    return depth_correlation_engine.evaluate_historical_proximity(
        active_well_id=active_well_id,
        current_md=current_md,
        radius_km=radius_km,
        depth_window_m=depth_window_m
    )


# ============================================================
# ALERT ENGINE
# ============================================================

@app.get("/api/alerts", tags=["Alert Engine"])
def get_alerts(
    well_id: Optional[str] = Query(None),
    user: UserSession = Depends(require_permission(Permission.VIEW_ALERTS)),
):
    """Returns active and historical operational drilling alerts."""
    alerts = global_alert_engine.get_active_alerts(well_id)
    return {"count": len(alerts), "alerts": alerts}


@app.get("/api/alerts/{alert_id}", tags=["Alert Engine"])
def get_alert_detail(
    alert_id: str,
    user: UserSession = Depends(require_permission(Permission.VIEW_ALERTS)),
):
    """Returns a single alert by ID."""
    alert = global_alert_engine._get_alert_item(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert.to_dict()


@app.post("/api/alerts/{alert_id}/acknowledge", tags=["Alert Engine"])
def acknowledge_alert(
    alert_id: str,
    user: UserSession = Depends(require_permission(Permission.ACKNOWLEDGE_ALERT)),
):
    """Acknowledges an active operational alert. Requires ACKNOWLEDGE_ALERT permission."""
    alt = global_alert_engine.acknowledge_alert(alert_id, user.user_id)
    if not alt:
        raise HTTPException(status_code=404, detail="Alert not found.")
    global_audit_service.log_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        action="ALERT_ACKNOWLEDGED",
        resource_type="ALERT",
        resource_id=alert_id,
        well_id=alt.well_id,
        organization_id=user.organization_id,
    )
    return alt.to_dict()


@app.post("/api/alerts/{alert_id}/investigate", tags=["Alert Engine"])
def start_investigation(
    alert_id: str,
    user: UserSession = Depends(require_permission(Permission.INVESTIGATE_ALERT)),
):
    """Moves alert to INVESTIGATING status."""
    alt = global_alert_engine.start_investigation(alert_id, user.user_id)
    if not alt:
        raise HTTPException(status_code=404, detail="Alert not found.")
    global_audit_service.log_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        action="ALERT_INVESTIGATION_STARTED",
        resource_type="ALERT",
        resource_id=alert_id,
        well_id=alt.well_id,
        organization_id=user.organization_id,
    )
    return alt.to_dict()


@app.post("/api/alerts/{alert_id}/assign", tags=["Alert Engine"])
def assign_alert(
    alert_id: str,
    assignee_id: str = Query(..., description="UUID or identifier of user to assign alert to"),
    user: UserSession = Depends(require_permission(Permission.INVESTIGATE_ALERT)),
):
    """Assigns an alert to a team member."""
    alt = global_alert_engine.assign_alert(alert_id, assignee_id)
    if not alt:
        raise HTTPException(status_code=404, detail="Alert not found.")
    global_audit_service.log_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        action="ALERT_ASSIGNED",
        resource_type="ALERT",
        resource_id=alert_id,
        well_id=alt.well_id,
        organization_id=user.organization_id,
        payload={"assigned_to": assignee_id},
    )
    return alt.to_dict()


@app.get("/api/alerts/{alert_id}/notes", tags=["Alert Engine"])
def get_alert_notes(
    alert_id: str,
    user: UserSession = Depends(require_permission(Permission.VIEW_ALERTS)),
):
    """Returns notes added to an alert."""
    return {"alert_id": alert_id, "notes": global_alert_engine.get_notes(alert_id)}


@app.post("/api/alerts/{alert_id}/notes", tags=["Alert Engine"])
def add_alert_note(
    alert_id: str,
    note_text: str = Query(..., description="Note content"),
    user: UserSession = Depends(require_permission(Permission.INVESTIGATE_ALERT)),
):
    """Adds an operational note to an alert."""
    if not note_text or not note_text.strip():
        raise HTTPException(status_code=400, detail="Note text cannot be empty.")

    note = global_alert_engine.add_note(alert_id, user.user_id, note_text)
    global_audit_service.log_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        action="ALERT_NOTE_ADDED",
        resource_type="ALERT",
        resource_id=alert_id,
        organization_id=user.organization_id,
        payload={"note_text": note_text},
    )
    return {"status": "success", "note": note}


@app.post("/api/alerts/{alert_id}/resolve", tags=["Alert Engine"])
def resolve_alert(
    alert_id: str,
    notes: str = Query(..., description="Resolution summary is required"),
    user: UserSession = Depends(require_permission(Permission.RESOLVE_ALERT)),
):
    """Resolves an operational alert with mandatory investigation notes."""
    if not notes or not notes.strip():
        raise HTTPException(
            status_code=400,
            detail="Resolution summary is required. Provide notes query parameter."
        )
    alt = global_alert_engine.resolve_alert(alert_id, user.user_id, notes)
    if not alt:
        raise HTTPException(status_code=404, detail="Alert not found.")
    global_audit_service.log_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        action="ALERT_RESOLVED",
        resource_type="ALERT",
        resource_id=alert_id,
        well_id=alt.well_id,
        organization_id=user.organization_id,
    )
    return alt.to_dict()


# ============================================================
# AUDIT TRAIL
# ============================================================

@app.get("/api/audit", tags=["Audit Trail"])
def get_audit_logs(
    well_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: UserSession = Depends(require_permission(Permission.VIEW_AUDIT)),
):
    """Returns immutable operational audit log events. Supabase-backed when configured."""
    events = global_audit_service.get_events(
        well_id=well_id,
        action=action,
        actor_id=actor_id,
        organization_id=user.organization_id,
        limit=limit,
        offset=offset,
    )
    return {"count": len(events), "events": events}


# ============================================================
# REPORTS
# ============================================================

@app.get("/api/reports/ddr", tags=["Reports"])
def generate_ddr_report(
    well_id: str = Query("15/9-F-14"),
    user: UserSession = Depends(require_permission(Permission.GENERATE_REPORTS)),
):
    """Generates Daily Drilling Report (DDR) summary from live telemetry and Volve DDR data."""
    st = get_app_state().get_well_state(well_id)
    rpt = global_report_generator.generate_daily_drilling_report(
        well_id=well_id,
        current_md=st["current_md"],
        tvd=st.get("tvd"),
        sensor_summary=st["latest_sensor"] or {}
    )
    global_audit_service.log_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        action="REPORT_GENERATED",
        resource_type="REPORT",
        resource_id=rpt["report_id"],
        well_id=well_id,
        organization_id=user.organization_id,
    )
    return rpt


# ============================================================
# SETTINGS
# ============================================================

from pydantic import BaseModel
from ertmac.config.settings import get_system_settings as fetch_sys_settings
from ertmac.notifications.preferences import (
    get_user_preferences,
    update_user_preferences,
    delete_user_preferences,
)

class SystemSettingsUpdateRequest(BaseModel):
    search_radius_km_default: Optional[float] = None
    depth_window_m_default: Optional[float] = None
    notification_recipient_email: Optional[str] = None
    email_enabled: Optional[bool] = None
    critical_alerts: Optional[bool] = None
    high_alerts: Optional[bool] = None
    medium_alerts: Optional[bool] = None
    historical_alerts: Optional[bool] = None
    system_notifications: Optional[bool] = None
    report_notifications: Optional[bool] = None

@app.get("/api/settings", tags=["Configuration"])
def get_system_settings(user: UserSession = Depends(get_current_user)):
    """Returns custom Supabase settings for the individual authenticated user."""
    user_prefs = get_user_preferences(user.user_id, default_email=user.email)
    sys_env = fetch_sys_settings()
    return {
        **sys_env,
        **user_prefs,
        "user_id": user.user_id,
        "user_email": user.email,
        "user_role": user.role.value,
    }

from ertmac.config.settings import get_system_settings as fetch_sys_settings, update_system_settings as save_sys_settings

@app.put("/api/settings", tags=["Configuration"])
def update_system_settings_endpoint(
    request: SystemSettingsUpdateRequest,
    user: UserSession = Depends(get_current_user),
):
    """Creates or updates individual user configuration in Supabase and syncs runtime settings."""
    updates = {k: v for k, v in request.model_dump(exclude_unset=True).items() if v is not None}
    updated = update_user_preferences(user.user_id, updates, default_email=user.email)
    sys_env = save_sys_settings(updates)
    
    global_audit_service.log_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        action="USER_SETTINGS_UPDATED",
        resource_type="SETTINGS",
        resource_id=f"USER_SETTINGS_{user.user_id}",
        organization_id=user.organization_id,
        payload=updates,
    )
    return {
        **sys_env,
        **updated,
        "user_id": user.user_id,
        "user_email": user.email,
        "user_role": user.role.value,
    }

@app.delete("/api/settings", tags=["Configuration"])
def delete_system_settings_endpoint(
    user: UserSession = Depends(get_current_user),
):
    """Deletes individual user custom settings from Supabase and resets to default configuration."""
    reset_prefs = delete_user_preferences(user.user_id, default_email=user.email)
    global_audit_service.log_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        action="USER_SETTINGS_RESET",
        resource_type="SETTINGS",
        resource_id=f"USER_SETTINGS_{user.user_id}",
        organization_id=user.organization_id,
        payload={"reset": True},
    )
    sys_env = fetch_sys_settings()
    return {
        **sys_env,
        **reset_prefs,
        "user_id": user.user_id,
        "user_email": user.email,
        "user_role": user.role.value,
    }




# ============================================================
# WEBSOCKET GATEWAY (preserved from Phase 1)
# ============================================================

from ertmac.auth.rbac import authenticate_websocket_session

@app.websocket("/api/ws/wells/{well_id:path}")
async def websocket_gateway(websocket: WebSocket, well_id: str):
    """
    Application WebSocket Gateway.
    Transmits typed messages to authenticated frontend clients:
    - sensor_update
    - ml_update
    - stream_status
    """
    session = authenticate_websocket_session(websocket, well_id=well_id)
    if not session:
        await websocket.close(code=1008, reason="Authentication failed or token invalid")
        return

    await websocket.accept()
    logger.info(f"WebSocket client connected for well '{well_id}' (User: {session.email}, Org: {session.organization_id})")
    state_mgr = get_app_state()


    try:
        st = state_mgr.get_well_state(well_id)
        await websocket.send_json({
            "type": "stream_status",
            "data": {
                "well_id": well_id,
                "status": st["stream_status"],
                "data_source": SCIENTIFIC_LABEL
            }
        })

        last_count = -1
        while True:
            await asyncio.sleep(0.1)
            st = state_mgr.get_well_state(well_id)
            current_count = st["samples_received"]

            if current_count != last_count and st["latest_sensor"] is not None:
                last_count = current_count
                ml = st["ml"]
                current_md = st["current_md"]

                await websocket.send_json({
                    "type": "sensor_update",
                    "data": st["latest_sensor"]
                })

                await websocket.send_json({
                    "type": "ml_update",
                    "data": ml
                })

                await websocket.send_json({
                    "type": "stream_status",
                    "data": {
                        "status": st["stream_status"],
                        "current_md": current_md,
                        "samples_received": current_count
                    }
                })

                # Fire alert if Isolation Forest detects anomaly (risk_score == 1.0)
                if ml.get("status") == "SUCCESS" and ml.get("risk_score") == 1.0:
                    sensor = st["latest_sensor"] or {}
                    features = ml.get("features", {})

                # ── Helper: safe format ───────────────────────────────────
                    def _fv(key: str, unit: str = "", fmt: str = ".1f") -> str:
                        v = sensor.get(key)
                        return f"{v:{fmt}}{unit}" if v is not None else "N/A"

                    def _fd(key: str):
                        v = features.get(key)
                        return float(v) if v is not None else None

                    # ── Domain-rules hazard classifier ───────────────────────
                    d_torque = _fd("delta_torque")
                    d_wob    = _fd("delta_wob")
                    d_rop    = _fd("delta_rop")
                    d_spp    = _fd("delta_spp")
                    d_flow   = _fd("delta_flow_in")
                    mse_val  = _fd("mse")
                    dxc_val  = _fd("dxc")

                    rop  = float(sensor.get("rop",  0.0) or 0.0)
                    torq = float(sensor.get("torque", 0.0) or 0.0)

                    hazard_title   = "Drilling Anomaly Detected"
                    hazard_verdict = "Telemetry has deviated significantly from the normal operational envelope. Verify all channels."
                    severity_tag   = AlertSeverity.HIGH

                    # Priority-ordered domain rules
                    if (d_spp is not None and d_flow is not None and d_spp < -15 and d_flow > 50 and rop > 5):
                        hazard_title   = "⚠ POSSIBLE WELL KICK"
                        hazard_verdict = (f"SPP dropped {abs(d_spp):.1f} bar while flow-in increased {d_flow:.0f} L/min — classic kick signature. "
                                          f"Pit volume gain check IMMEDIATELY. ROP={rop:.1f} m/h suggests active influx.")
                        severity_tag   = AlertSeverity.CRITICAL

                    elif (d_spp is not None and d_flow is not None and d_spp < -10 and d_flow < -80):
                        hazard_title   = "⚠ POSSIBLE MUD LOSS / LOST CIRCULATION"
                        hazard_verdict = (f"SPP down {abs(d_spp):.1f} bar AND flow-in down {abs(d_flow):.0f} L/min — thief zone or fracture taking fluid. "
                                          f"Check return flow and pit levels. Consider LCM pill.")
                        severity_tag   = AlertSeverity.CRITICAL

                    elif (d_torque is not None and d_wob is not None and d_torque > 5 and d_wob < -10 and rop < 2):
                        hazard_title   = "⚠ POSSIBLE STUCK PIPE / PACK-OFF"
                        hazard_verdict = (f"Torque surged +{d_torque:.1f} kNm, WOB dropped {abs(d_wob):.1f} kN, ROP fell to {rop:.1f} m/h — "
                                          f"differential sticking or pack-off precursor. Reciprocate/rotate string immediately. Do NOT apply excessive overpull.")
                        severity_tag   = AlertSeverity.CRITICAL

                    elif (mse_val is not None and d_rop is not None and mse_val > 50000 and d_rop < -3):
                        hazard_title   = "Bit Balling / Hard Formation Change"
                        hazard_verdict = (f"Mechanical Specific Energy at {mse_val:.0f} kJ/m³ while ROP dropped {abs(d_rop):.1f} m/h — "
                                          f"bit consuming far more energy per metre. Likely bit balling (clay) or hard stringer. Consider reaming or weight reduction.")

                    elif (d_spp is not None and d_torque is not None and d_spp < -12 and abs(d_torque) < 2 and rop < 3):
                        hazard_title   = "Possible Bit / String Washout"
                        hazard_verdict = (f"SPP fell {abs(d_spp):.1f} bar with no torque change — pressure loss without mechanical resistance points to a washout in BHA or bit nozzles. "
                                          f"Pull to shoe and assess BHA integrity.")

                    elif d_torque is not None and d_torque > 8:
                        hazard_title   = "Elevated Torque — Tight Hole / Formation Interaction"
                        hazard_verdict = (f"Torque increased {d_torque:.1f} kNm over the causal window. Possible tight hole, ledge, or reactive formation. "
                                          f"Reduce WOB, increase RPM, or circulate to condition mud before continuing.")

                    elif dxc_val is not None and dxc_val < 0.8:
                        hazard_title   = "D-Exponent Pore Pressure Warning"
                        hazard_verdict = (f"Corrected D-exponent = {dxc_val:.3f} (below 1.0) — formation is drilling faster than normal compaction trend, "
                                          f"a pore pressure increase signature. Review mud weight and ECD margins immediately.")

                    # Sensor snapshot + top signals
                    sensor_snapshot = (f"ROP={_fv('rop', ' m/h')} | WOB={_fv('wob', ' kN')} | SPP={_fv('spp', ' bar')} | "
                                       f"Torque={_fv('torque', ' kNm')} | RPM={_fv('rpm', ' rpm', '.0f')} | "
                                       f"Flow={_fv('flow_in', ' L/min', '.0f')} | MudDensity={_fv('mud_density', ' g/cc')}")

                    delta_map = {"delta_rop": "ΔROP", "delta_wob": "ΔWOB", "delta_spp": "ΔSPP",
                                 "delta_torque": "ΔTorque", "delta_flow_in": "ΔFlow", "mse": "MSE", "dxc": "D-exp"}
                    sig_list = sorted([(lbl, float(features[k])) for k, lbl in delta_map.items() if features.get(k) is not None],
                                      key=lambda x: abs(x[1]), reverse=True)
                    top_signals = "  |  ".join(f"{lbl}={v:+.2f}" for lbl, v in sig_list[:5]) or "N/A"

                    evidence = (f"PROBABLE CAUSE: {hazard_verdict}\n\n"
                                f"SENSOR READINGS @ MD {current_md:.1f}m:\n{sensor_snapshot}\n\n"
                                f"TOP SIGNALS (30m causal window): {top_signals}\n\n"
                                f"Model: IsolationForest | Contamination: 2% | Estimators: 100 | Verdict: ANOMALY")

                    new_alert = global_alert_engine.create_alert(
                        well_id=well_id,
                        title=hazard_title,
                        description=f"IsoForest anomaly @ MD {current_md:.1f}m — {hazard_title}",
                        severity=severity_tag,
                        source=AlertSource.ML_PREDICTION,
                        current_md=current_md,
                        evidence=evidence,
                        source_record="UNSUPERVISED ML ANOMALY — HUMAN VERIFICATION REQUIRED",
                        dedup_key=f"iso_forest:{well_id}:{round(current_md / 50.0)}"
                    )
                    if new_alert:
                        logger.info(f"ML Anomaly Alert created: {new_alert.alert_id} at MD={current_md:.1f}m")
                        await websocket.send_json({
                            "type": "alert_created",
                            "data": new_alert.to_dict()
                        })

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for well '{well_id}'")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
