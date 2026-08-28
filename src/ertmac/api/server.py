import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

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
    version="1.0.0"
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load NWIS Historical DDR API
VERIFIED_EVENTS_PATH = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"
nwis_historical_api: Optional[NWISHistoricalAPI] = None
if VERIFIED_EVENTS_PATH.exists():
    nwis_historical_api = NWISHistoricalAPI(str(VERIFIED_EVENTS_PATH))


def verify_auth_token(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
):
    """
    Production-safe Authentication dependency.
    Accepts X-API-Key or Authorization Bearer token.
    Falls back to development token if environment AUTH_REQUIRED is false.
    """
    auth_required = os.getenv("AUTH_REQUIRED", "false").lower() == "true"
    if not auth_required:
        return True

    expected_token = os.getenv("AUTH_TOKEN", "ps121-dev-secret-key")
    token = x_api_key
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1]

    if token != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key or Bearer token.")
    return True


def validate_well_id(well_id: str, state_mgr: ApplicationStateManager = Depends(get_app_state)):
    wells = [w["well_id"] for w in state_mgr.get_available_wells()]
    if well_id not in wells and not well_id.startswith("15/9"):
        raise HTTPException(status_code=404, detail=f"Well ID '{well_id}' not found. Available wells: {wells}")
    return well_id


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": "eRTMAC-NWIS Orchestration Backend",
        "data_source": SCIENTIFIC_LABEL
    }


@app.get("/api/wells", response_model=WellsResponse, tags=["Wells"])
def list_wells(
    state_mgr: ApplicationStateManager = Depends(get_app_state),
    authenticated: bool = Depends(verify_auth_token)
):
    """Returns list of available Volve wells."""
    return {"wells": state_mgr.get_available_wells()}


@app.get("/api/wells/{well_id:path}/state", response_model=WellStateResponse, tags=["Stream State"])
def get_well_state(
    well_id: str = Depends(validate_well_id),
    state_mgr: ApplicationStateManager = Depends(get_app_state),
    authenticated: bool = Depends(verify_auth_token)
):
    """Returns current stream state, depth position, latest sensor, and ML gate status."""
    return state_mgr.get_well_state(well_id)


@app.get("/api/wells/{well_id:path}/sensors/latest", tags=["Sensors"])
def get_latest_sensor(
    well_id: str = Depends(validate_well_id),
    state_mgr: ApplicationStateManager = Depends(get_app_state),
    authenticated: bool = Depends(verify_auth_token)
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
    authenticated: bool = Depends(verify_auth_token)
):
    """Returns strictly emitted causal sensor records <= cutoff_md. Never exposes future rows."""
    return state_mgr.get_sensor_history(well_id, cutoff_md=cutoff_md)


@app.get("/api/wells/{well_id:path}/events", response_model=EventsResponse, tags=["NWIS Intelligence"])
def get_offset_events(
    well_id: str = Depends(validate_well_id),
    current_md: float = Query(3000.0, description="Current depth position in meters"),
    radius: float = Query(100.0, description="Search radius in meters"),
    event_type: Optional[str] = Query(None, description="Optional event type filter"),
    authenticated: bool = Depends(verify_auth_token)
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
    authenticated: bool = Depends(verify_auth_token)
):
    """Consumes existing ML result. Returns ML_NOT_READY when readiness gate blocks inference."""
    return state_mgr.get_risk_status(well_id)


# Application WebSocket Gateway
@app.websocket("/api/ws/wells/{well_id:path}")
async def websocket_gateway(websocket: WebSocket, well_id: str):
    """
    Application WebSocket Gateway.
    Transmits typed messages to frontend clients:
    - sensor_update
    - ml_update
    - stream_status
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected for well '{well_id}'")
    state_mgr = get_app_state()

    try:
        # Transmit initial stream status
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

                # Broadcast typed sensor_update event
                await websocket.send_json({
                    "type": "sensor_update",
                    "data": st["latest_sensor"]
                })

                # Broadcast typed ml_update event
                await websocket.send_json({
                    "type": "ml_update",
                    "data": st["ml"]
                })

                # Broadcast stream_status event
                await websocket.send_json({
                    "type": "stream_status",
                    "data": {
                        "status": st["stream_status"],
                        "current_md": st["current_md"],
                        "samples_received": current_count
                    }
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for well '{well_id}'")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
