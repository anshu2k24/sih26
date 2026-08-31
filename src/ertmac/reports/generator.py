"""
PS26121 eRTMAC-NWIS — Production Report Generation & Shift Handover Engine
Generates authentic Daily Drilling Reports (DDR), Shift Handover Reports, Incident Summaries,
and exports formatted Markdown / PDF / Text documentation.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ertmac.auth.supabase_client import get_supabase_admin
from ertmac.alerts.engine import global_alert_engine
from ertmac.timeline.engine import OperationalTimelineEngine
from ertmac.audit.logger import global_audit_service

logger = logging.getLogger("ertmac.reports.generator")

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

_in_memory_reports: List[Dict[str, Any]] = []


def _clean_uuid(val: Optional[str]) -> Optional[str]:
    """Returns val if it is a valid UUID and not dev fallback UUID, else None."""
    if not val:
        return None
    try:
        u = str(uuid.UUID(str(val)))
        if u == "00000000-0000-0000-0000-000000000001":
            return None
        return u
    except (ValueError, TypeError):
        return None


class ReportGenerator:
    @staticmethod
    def generate_daily_drilling_report(
        well_id: str = "15/9-F-14",
        current_md: float = 3050.0,
        tvd: Optional[float] = 2750.0,
        sensor_summary: Optional[Dict[str, Any]] = None,
        author_id: str = "00000000-0000-0000-0000-000000000001",
        organization_id: str = "00000000-0000-0000-0000-000000000001",
    ) -> Dict[str, Any]:
        """Generates a Daily Drilling Report (DDR)."""
        report_id = f"RPT_DDR_{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()

        alerts = global_alert_engine.get_active_alerts(well_id=well_id)
        timeline = OperationalTimelineEngine.get_timeline(well_id=well_id, limit=20)

        sensor_data = sensor_summary or {
            "avg_rop_mhr": 24.5,
            "avg_wob_kkg": 12.8,
            "avg_rpm": 120.0,
            "avg_flow_in_lpm": 2800.0,
            "avg_spp_bar": 215.0,
        }

        content_md = f"""# EQUINOR VOLVE FIELD — DAILY DRILLING REPORT (DDR)
**Report ID:** {report_id}
**Wellbore:** {well_id}
**Generated Date:** {now}
**Measured Depth (MD):** {current_md:.1f} m | **TVD:** {tvd:.1f} m

## 1. DRILLING PARAMETERS SUMMARY
- **Average Rate of Penetration (ROP):** {sensor_data.get('avg_rop_mhr', 24.5)} m/hr
- **Weight on Bit (WOB):** {sensor_data.get('avg_wob_kkg', 12.8)} kkg
- **Surface RPM:** {sensor_data.get('avg_rpm', 120.0)} rpm
- **Mud Flow Rate In:** {sensor_data.get('avg_flow_in_lpm', 2800.0)} L/min
- **Standpipe Pressure (SPP):** {sensor_data.get('avg_spp_bar', 215.0)} bar

## 2. OPERATIONAL ALERTS & INCIDENTS ({len(alerts)})
"""
        for a in alerts[:5]:
            content_md += f"- **[{a['severity']}] {a['title']}** @ {a['current_md']:.1f}m — Status: {a['status']}\n  *Evidence:* {a['evidence']}\n"

        content_md += "\n## 3. SHIFT TIMELINE LOGS\n"
        for t in timeline[:8]:
            content_md += f"- `{t['timestamp']}` [{t['event_category']}] {t['title']}: {t['description']}\n"

        content_md += "\n---\n*Provenanced from Equinor Volve USROP Dataset & NPD Official Well Coordinates.*"

        storage_path = f"reports/{organization_id}/{report_id}.md"
        try:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            export_path = REPORTS_DIR / f"{report_id}.md"
            export_path.write_text(content_md, encoding="utf-8")
        except Exception:
            pass

        db = get_supabase_admin()
        if db:
            try:
                db.storage.from_("reports").upload(
                    path=f"{organization_id}/{report_id}.md",
                    file=content_md.encode("utf-8"),
                    file_options={"content-type": "text/markdown", "upsert": "true"}
                )
                storage_path = f"reports/{organization_id}/{report_id}.md"
            except Exception as e:
                logger.debug(f"Storage upload for report {report_id}: {e}")

        local_file_path = str(export_path) if export_path and export_path.exists() else storage_path

        report_record = {
            "id": report_id,
            "report_id": report_id,
            "organization_id": organization_id,
            "well_id": well_id,
            "report_type": "DDR",
            "title": f"Equinor Volve Daily Drilling Report — Well {well_id}",
            "file_path": local_file_path,
            "storage_path": storage_path,
            "generated_by": author_id if len(author_id) == 36 and author_id != "00000000-0000-0000-0000-000000000001" else None,
            "current_md": current_md,
            "tvd": tvd,
            "content_md": content_md,
            "summary_data": {
                "alerts_count": len(alerts),
                "sensor_summary": sensor_data,
            },
            "created_at": now,
        }

        _in_memory_reports.insert(0, report_record)
        ReportGenerator._persist_to_db(report_record)

        global_audit_service.log_event(
            actor_id=author_id,
            actor_role="DRILLING_ENGINEER",
            action="DDR_REPORT_GENERATED",
            resource_type="REPORT",
            resource_id=report_id,
            well_id=well_id,
            organization_id=organization_id,
        )

        return report_record

    @staticmethod
    def generate_shift_handover_report(
        well_id: str = "15/9-F-14",
        current_md: float = 3050.0,
        outgoing_engineer: str = "Drilling Superintendent",
        author_id: str = "00000000-0000-0000-0000-000000000001",
        organization_id: str = "00000000-0000-0000-0000-000000000001",
    ) -> Dict[str, Any]:
        """Generates a Shift Handover Report for incoming/outgoing drilling crews."""
        report_id = f"RPT_HND_{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()

        alerts = global_alert_engine.get_active_alerts(well_id=well_id)
        open_alerts = [a for a in alerts if a["status"] in ("ACTIVE", "ACKNOWLEDGED", "INVESTIGATING")]
        timeline = OperationalTimelineEngine.get_timeline(well_id=well_id, limit=15)

        content_md = f"""# DRILLING OPERATIONS — SHIFT HANDOVER REPORT
**Report ID:** {report_id}
**Wellbore:** {well_id}
**Shift Handover Time:** {now}
**Outgoing Engineer:** {outgoing_engineer}
**Current Measured Depth (MD):** {current_md:.1f} m

## 1. CRITICAL OPEN ACTIONS & UNRESOLVED ALERTS ({len(open_alerts)})
"""
        if not open_alerts:
            content_md += "- **NOMINAL:** No open unresolved alerts. System status Nominal.\n"
        else:
            for a in open_alerts:
                content_md += f"- **[{a['severity']}] {a['title']}** (Status: {a['status']}) — Assigned: {a.get('assigned_to', 'Unassigned')}\n  *Action Required:* {a['evidence']}\n"

        content_md += "\n## 2. SHIFT LOG SUMMARY & NOTES\n"
        for t in timeline[:10]:
            content_md += f"- `{t['timestamp']}` [{t['event_category']}] {t['title']} ({t['description']})\n"

        content_md += "\n## 3. HANDOVER SIGN-OFF & ACKNOWLEDGMENT\n- Outgoing Supervisor Sign-off: [PENDING SIGN-OFF]\n- Incoming Supervisor Sign-off: [PENDING ACKNOWLEDGMENT]"

        export_path = None
        storage_path = f"reports/{organization_id}/{report_id}.md"
        try:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            export_path = REPORTS_DIR / f"{report_id}.md"
            export_path.write_text(content_md, encoding="utf-8")
        except Exception:
            pass

        db = get_supabase_admin()
        if db:
            try:
                db.storage.from_("reports").upload(
                    path=f"{organization_id}/{report_id}.md",
                    file=content_md.encode("utf-8"),
                    file_options={"content-type": "text/markdown", "upsert": "true"}
                )
                storage_path = f"reports/{organization_id}/{report_id}.md"
            except Exception as e:
                logger.debug(f"Storage upload for handover report {report_id}: {e}")

        local_file_path = str(export_path) if export_path and export_path.exists() else storage_path

        report_record = {
            "id": report_id,
            "report_id": report_id,
            "organization_id": organization_id,
            "well_id": well_id,
            "report_type": "SHIFT_HANDOVER",
            "title": f"Shift Handover Report — Well {well_id}",
            "file_path": local_file_path,
            "storage_path": storage_path,
            "generated_by": author_id if len(author_id) == 36 and author_id != "00000000-0000-0000-0000-000000000001" else None,
            "current_md": current_md,
            "content_md": content_md,
            "summary_data": {
                "open_alerts_count": len(open_alerts),
                "outgoing_engineer": outgoing_engineer,
            },
            "created_at": now,
        }

        _in_memory_reports.insert(0, report_record)
        ReportGenerator._persist_to_db(report_record)

        global_audit_service.log_event(
            actor_id=author_id,
            action="SHIFT_HANDOVER_REPORT_GENERATED",
            resource_type="REPORT",
            resource_id=report_id,
            well_id=well_id,
            organization_id=organization_id,
        )

        return report_record

    @staticmethod
    def _persist_to_db(record: Dict[str, Any]) -> None:
        db = get_supabase_admin()
        if db:
            try:
                db_payload = {
                    "organization_id": record["organization_id"],
                    "well_id": record["well_id"],
                    "report_type": record["report_type"],
                    "title": record["title"],
                    "storage_path": record.get("file_path"),
                    "payload": {
                        "current_md": record.get("current_md"),
                        "tvd": record.get("tvd"),
                        "content_md": record.get("content_md"),
                        "summary_data": record.get("summary_data"),
                    },
                }
                clean_author = _clean_uuid(record.get("generated_by"))
                if clean_author:
                    db_payload["generated_by"] = clean_author

                res = db.table("reports").insert(db_payload).execute()
                if res.data and len(res.data) > 0:
                    record["id"] = str(res.data[0]["id"])
            except Exception as e:
                logger.warning(f"Failed to persist report to DB: {e}")

    @staticmethod
    def get_reports(well_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        db_records: List[Dict[str, Any]] = []
        db = get_supabase_admin()
        if db:
            try:
                query = db.table("reports").select("*").order("created_at", desc=True).limit(limit)
                if well_id:
                    query = query.eq("well_id", well_id)
                res = query.execute()
                if res.data:
                    for r in res.data:
                        payload = r.get("payload") or {}
                        db_records.append({
                            "id": str(r.get("id")),
                            "report_id": str(r.get("id")),
                            "well_id": r.get("well_id"),
                            "report_type": r.get("report_type"),
                            "title": r.get("title"),
                            "file_path": r.get("storage_path"),
                            "current_md": payload.get("current_md"),
                            "tvd": payload.get("tvd"),
                            "content_md": payload.get("content_md"),
                            "summary_data": payload.get("summary_data"),
                            "created_at": r.get("created_at"),
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch reports from DB: {e}")

        combined = list(db_records)
        for r in _in_memory_reports:
            r_id = str(r.get("id") or r.get("report_id"))
            if well_id and r.get("well_id") != well_id:
                continue
            if not any(str(d.get("id") or d.get("report_id")) == r_id for d in combined):
                combined.append(r)

        return combined[:limit]


global_report_generator = ReportGenerator()
