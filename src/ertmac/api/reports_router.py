"""
PS26121 eRTMAC-NWIS — Reports & Shift Handover Router
Provides API endpoints for generating, listing, and exporting DDR and Shift Handover reports.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ertmac.auth.rbac import (
    get_current_user,
    require_permission,
    UserSession,
    Permission,
)
from ertmac.reports.generator import ReportGenerator, global_report_generator

logger = logging.getLogger("ertmac.api.reports")

router = APIRouter(prefix="/api/reports", tags=["Reports & Shift Handover"])


class GenerateReportRequest(BaseModel):
    well_id: str = "15/9-F-14"
    report_type: str = "DDR"  # DDR, SHIFT_HANDOVER, INCIDENT_SUMMARY
    current_md: Optional[float] = 3050.0
    outgoing_engineer: Optional[str] = "Drilling Superintendent"


@router.get("")
def list_reports(
    well_id: Optional[str] = Query(None, description="Optional wellbore filter"),
    limit: int = Query(50, ge=1, le=200),
    user: UserSession = Depends(require_permission(Permission.VIEW_REPORTS)),
):
    """Lists generated reports."""
    reports = ReportGenerator.get_reports(well_id=well_id, limit=limit)
    return {"count": len(reports), "reports": reports}


@router.get("/ddr")
def get_ddr_report(
    well_id: str = Query("15/9-F-14"),
    user: UserSession = Depends(require_permission(Permission.VIEW_REPORTS)),
):
    """Generates and returns an on-demand Daily Drilling Report (DDR) for a well."""
    return ReportGenerator.generate_daily_drilling_report(
        well_id=well_id,
        current_md=3050.0,
        tvd=2750.0,
        author_id=user.user_id,
        organization_id=user.organization_id,
    )


@router.post("/generate")
def generate_report_endpoint(
    body: GenerateReportRequest,
    user: UserSession = Depends(require_permission(Permission.GENERATE_REPORTS)),
):
    """Generates a DDR, Shift Handover, or Incident Summary Report."""
    well_id = body.well_id or "15/9-F-14"
    md = body.current_md or 3050.0

    if body.report_type == "SHIFT_HANDOVER":
        report = ReportGenerator.generate_shift_handover_report(
            well_id=well_id,
            current_md=md,
            outgoing_engineer=body.outgoing_engineer or user.user_id,
            author_id=user.user_id,
            organization_id=user.organization_id,
        )
    else:
        report = ReportGenerator.generate_daily_drilling_report(
            well_id=well_id,
            current_md=md,
            tvd=md * 0.9,
            author_id=user.user_id,
            organization_id=user.organization_id,
        )

    return {"status": "generated", "report": report}


@router.get("/{report_id}/export")
def export_report_file(
    report_id: str,
    user: UserSession = Depends(require_permission(Permission.VIEW_REPORTS)),
):
    """Downloads the generated report Markdown file."""
    reports = ReportGenerator.get_reports(limit=200)
    rep = next((r for r in reports if str(r.get("id")) == report_id or str(r.get("report_id")) == report_id), None)
    if not rep or not rep.get("file_path"):
        raise HTTPException(status_code=404, detail="Report file not found.")

    file_path = Path(rep["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file does not exist on disk.")

    return FileResponse(
        path=str(file_path),
        filename=f"{report_id}.md",
        media_type="text/markdown",
    )
