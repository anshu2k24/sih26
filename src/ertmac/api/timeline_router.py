"""
PS26121 eRTMAC-NWIS — Operational Timeline Router
Provides API endpoints for fetching depth-correlated well timeline events and posting shift notes.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from ertmac.auth.rbac import (
    get_current_user,
    require_permission,
    UserSession,
    Permission,
)
from ertmac.timeline.engine import OperationalTimelineEngine

logger = logging.getLogger("ertmac.api.timeline")

router = APIRouter(prefix="/api/wells", tags=["Operational Timeline"])


@router.get("/{well_id:path}/timeline")
def get_well_operational_timeline(
    well_id: str,
    category: Optional[str] = Query("ALL", description="Filter category: ALL, ALERT, NOTE, AUDIT, DOCUMENT"),
    min_md: Optional[float] = Query(None, description="Minimum depth cutoff (MD meters)"),
    max_md: Optional[float] = Query(None, description="Maximum depth cutoff (MD meters)"),
    limit: int = Query(100, ge=1, le=500),
    user: UserSession = Depends(require_permission(Permission.VIEW_TELEMETRY)),
):
    """Retrieves aggregated depth-correlated operational timeline events for a wellbore."""
    events = OperationalTimelineEngine.get_timeline(
        organization_id=user.organization_id,
        well_id=well_id,
        category=category,
        min_md=min_md,
        max_md=max_md,
        limit=limit,
    )
    return {
        "well_id": well_id,
        "count": len(events),
        "timeline_events": events,
    }


@router.post("/{well_id:path}/timeline/notes")
def post_shift_note(
    well_id: str,
    note_text: str = Query(..., description="Operational shift log entry text"),
    current_md: Optional[float] = Query(None, description="Current measured depth MD in meters"),
    user: UserSession = Depends(require_permission(Permission.ACKNOWLEDGE_ALERT)),
):
    """Adds a manual operator shift note entry to the well operational timeline."""
    if not note_text or not note_text.strip():
        raise HTTPException(status_code=400, detail="Note text cannot be empty.")

    entry = OperationalTimelineEngine.add_shift_note(
        well_id=well_id,
        author_id=user.user_id,
        note_text=note_text,
        current_md=current_md,
        organization_id=user.organization_id,
    )
    return {"status": "success", "timeline_event": entry}
