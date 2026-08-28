from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class WellItem(BaseModel):
    well_id: str
    status: str = "available"

class WellsResponse(BaseModel):
    wells: List[WellItem]

class SensorTelemetrySchema(BaseModel):
    well_id: str
    timestamp: str
    md: float
    tvd: Optional[float] = None
    rop: Optional[float] = None
    wob: Optional[float] = None
    rpm: Optional[float] = None
    torque: Optional[float] = None
    hookload: Optional[float] = None
    spp: Optional[float] = None
    flow_in: Optional[float] = None
    mud_density: Optional[float] = None

class MLResultSchema(BaseModel):
    status: str
    is_blocked: bool
    gate_reason: str
    cutoff_md: float
    risk_score: Optional[float] = None
    features_constructed: int = 0

class WellStateResponse(BaseModel):
    well_id: str
    stream_status: str
    data_source: str
    current_md: float
    tvd: Optional[float] = None
    last_timestamp: str
    samples_received: int
    latest_sensor: Optional[Dict[str, Any]] = None
    ml: Dict[str, Any]

class HistoryResponse(BaseModel):
    well_id: str
    cutoff_md: float
    count: int
    records: List[Dict[str, Any]]

class EventsResponse(BaseModel):
    active_well: str
    current_md: float
    search_radius_m: float
    risk_summary: str
    nearby_events: List[Dict[str, Any]]
    provenance: str

class RiskResponse(BaseModel):
    well_id: str
    status: str
    is_blocked: bool
    risk_score: Optional[float] = None
    reason: str
    features_constructed: int = 0
