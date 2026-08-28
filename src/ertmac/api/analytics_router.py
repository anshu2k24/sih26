"""
PS26121 eRTMAC-NWIS — Operational Analytics Router (Phase 9 & 13)

Provides endpoints for well profile analytics, historical event distributions,
alert trends, and platform KPI metrics.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query, HTTPException

from ertmac.auth.rbac import get_current_user, UserSession, Permission, require_permission
from ertmac.alerts.engine import global_alert_engine
from ertmac.audit.logger import global_audit_service
from ertmac.reports.generator import global_report_generator

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Well Intelligence"])


@router.get("/summary")
def get_analytics_summary(
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Returns platform-wide operational KPIs and data inventory summaries."""
    alerts = global_alert_engine.get_active_alerts()

    severity_counts = {
        "CRITICAL": sum(1 for a in alerts if a.get("severity") == "CRITICAL"),
        "HIGH": sum(1 for a in alerts if a.get("severity") == "HIGH"),
        "MEDIUM": sum(1 for a in alerts if a.get("severity") == "MEDIUM"),
        "LOW": sum(1 for a in alerts if a.get("severity") == "LOW"),
    }

    status_counts = {
        "ACTIVE": sum(1 for a in alerts if a.get("status") == "ACTIVE"),
        "ACKNOWLEDGED": sum(1 for a in alerts if a.get("status") == "ACKNOWLEDGED"),
        "INVESTIGATING": sum(1 for a in alerts if a.get("status") == "INVESTIGATING"),
        "RESOLVED": sum(1 for a in alerts if a.get("status") == "RESOLVED"),
    }

    return {
        "status": "SUCCESS",
        "total_active_alerts": len([a for a in alerts if a.get("status") != "RESOLVED"]),
        "total_alerts": len(alerts),
        "alert_severity_breakdown": severity_counts,
        "alert_status_breakdown": status_counts,
        "monitored_wells_count": 5,
        "nwis_dataset_source": "Equinor Volve 15/9 Field (Ver. 2.0)",
        "knowledge_records_count": 274,
    }


@router.get("/wells/{well_id:path}/profile")
def get_well_profile_analytics(
    well_id: str,
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """
    Returns full well profile analytics: event type distribution, depth range breakdown,
    and historical hazard severity counts.
    """
    # Sample analytics payload based on Volve historical dataset structure
    well_profiles: Dict[str, Dict[str, Any]] = {
        "15/9-F-14": {
            "well_id": "15/9-F-14",
            "field": "Volve",
            "operator": "Equinor (Statoil)",
            "spud_year": 2008,
            "total_depth_md_m": 3405.0,
            "max_tvd_m": 3150.0,
            "drilling_days": 42,
            "historical_events_count": 86,
            "event_type_distribution": {
                "Pack-off": 24,
                "Tight Hole": 18,
                "Equipment Failure": 15,
                "FORMATION_MUD_LOSS": 12,
                "Kick": 8,
                "Stuck Pipe": 9,
            },
            "depth_range_distribution": [
                {"range": "0 - 1000 m", "event_count": 5, "primary_risk": "Surface casing wear"},
                {"range": "1000 - 2000 m", "event_count": 18, "primary_risk": "Reactive shales"},
                {"range": "2000 - 3000 m", "event_count": 45, "primary_risk": "Tight hole & Pack-offs"},
                {"range": "3000 - 3500 m", "event_count": 18, "primary_risk": "Differential sticking"},
            ],
            "severity_breakdown": {"CRITICAL": 14, "HIGH": 28, "MEDIUM": 32, "LOW": 12},
        },
        "15/9-F-12": {
            "well_id": "15/9-F-12",
            "field": "Volve",
            "operator": "Equinor (Statoil)",
            "spud_year": 2008,
            "total_depth_md_m": 3250.0,
            "max_tvd_m": 3020.0,
            "drilling_days": 38,
            "historical_events_count": 64,
            "event_type_distribution": {
                "Pack-off": 16,
                "Tight Hole": 14,
                "Equipment Failure": 12,
                "FORMATION_MUD_LOSS": 10,
                "Kick": 5,
                "Stuck Pipe": 7,
            },
            "depth_range_distribution": [
                {"range": "0 - 1000 m", "event_count": 4, "primary_risk": "Spudding issues"},
                {"range": "1000 - 2000 m", "event_count": 15, "primary_risk": "Hole cleaning"},
                {"range": "2000 - 3000 m", "event_count": 35, "primary_risk": "Swab & Surge"},
                {"range": "3000 - 3500 m", "event_count": 10, "primary_risk": "Lost circulation"},
            ],
            "severity_breakdown": {"CRITICAL": 9, "HIGH": 21, "MEDIUM": 24, "LOW": 10},
        },
    }

    # Default profile for other offset wells
    profile = well_profiles.get(well_id, {
        "well_id": well_id,
        "field": "Volve",
        "operator": "Equinor (Statoil)",
        "spud_year": 2008,
        "total_depth_md_m": 3300.0,
        "max_tvd_m": 3050.0,
        "drilling_days": 40,
        "historical_events_count": 50,
        "event_type_distribution": {
            "Tight Hole": 15,
            "Pack-off": 12,
            "Equipment Failure": 10,
            "FORMATION_MUD_LOSS": 8,
            "Stuck Pipe": 5,
        },
        "depth_range_distribution": [
            {"range": "0 - 1000 m", "event_count": 6, "primary_risk": "Tophole drilling"},
            {"range": "1000 - 2000 m", "event_count": 14, "primary_risk": "Shale instability"},
            {"range": "2000 - 3000 m", "event_count": 22, "primary_risk": "Tight hole"},
            {"range": "3000 - 3500 m", "event_count": 8, "primary_risk": "Depleted reservoir losses"},
        ],
        "severity_breakdown": {"CRITICAL": 8, "HIGH": 16, "MEDIUM": 18, "LOW": 8},
    })

    return {"status": "SUCCESS", "profile": profile}


@router.get("/alerts/trend")
def get_alerts_trend(
    user: UserSession = Depends(require_permission(Permission.VIEW_ALERTS)),
):
    """Returns alert generation trends for dashboard visualization."""
    return {
        "status": "SUCCESS",
        "trend": [
            {"date": "2026-08-22", "CRITICAL": 1, "HIGH": 2, "MEDIUM": 4, "LOW": 3},
            {"date": "2026-08-23", "CRITICAL": 0, "HIGH": 3, "MEDIUM": 5, "LOW": 2},
            {"date": "2026-08-24", "CRITICAL": 2, "HIGH": 1, "MEDIUM": 3, "LOW": 4},
            {"date": "2026-08-25", "CRITICAL": 0, "HIGH": 4, "MEDIUM": 6, "LOW": 2},
            {"date": "2026-08-26", "CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 5},
            {"date": "2026-08-27", "CRITICAL": 0, "HIGH": 1, "MEDIUM": 4, "LOW": 3},
            {"date": "2026-08-28", "CRITICAL": 1, "HIGH": 3, "MEDIUM": 2, "LOW": 1},
        ]
    }
