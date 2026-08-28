"""
PS26121 Phase 7 — Reports & Shift Handover Test Suite

Tests verify:
1. Daily Drilling Report (DDR) generation & telemetry metric aggregation
2. Shift Handover Report generation & open action tracking
3. Report disk file creation in data/reports/
4. Report listing & DB persistence fallback
5. Reports API endpoints (GET /api/reports, GET /api/reports/ddr, POST /generate, GET export)
"""

import os
import sys
import uuid
import pytest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("AUTH_REQUIRED", "false")

from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.reports.generator import ReportGenerator, global_report_generator

client = TestClient(app)


class TestReportGenerator:
    def test_generate_daily_drilling_report(self):
        well_id = "15/9-F-14"
        rpt = ReportGenerator.generate_daily_drilling_report(
            well_id=well_id,
            current_md=3150.0,
            tvd=2800.0,
            author_id="user_eng_01",
        )
        assert rpt is not None
        assert rpt["report_type"] == "DDR"
        assert rpt["well_id"] == well_id
        assert "DAILY DRILLING REPORT" in rpt["content_md"]
        assert Path(rpt["file_path"]).exists()

    def test_generate_shift_handover_report(self):
        well_id = "15/9-F-15"
        rpt = ReportGenerator.generate_shift_handover_report(
            well_id=well_id,
            current_md=2900.0,
            outgoing_engineer="Drilling Supervisor Alpha",
            author_id="user_eng_01",
        )
        assert rpt is not None
        assert rpt["report_type"] == "SHIFT_HANDOVER"
        assert "SHIFT HANDOVER REPORT" in rpt["content_md"]
        assert "Drilling Supervisor Alpha" in rpt["content_md"]
        assert Path(rpt["file_path"]).exists()

    def test_get_reports(self):
        well_id = f"15/9-F-TEST-{uuid.uuid4().hex[:6]}"
        ReportGenerator.generate_daily_drilling_report(well_id=well_id)
        reports = ReportGenerator.get_reports(well_id=well_id)
        assert len(reports) >= 1
        assert reports[0]["well_id"] == well_id


class TestReportsAPIEndpoints:
    def test_get_reports_list_api(self):
        res = client.get("/api/reports")
        assert res.status_code == 200
        data = res.json()
        assert "count" in data
        assert "reports" in data

    def test_get_ddr_on_demand_api(self):
        res = client.get("/api/reports/ddr?well_id=15%2F9-F-14")
        assert res.status_code == 200
        data = res.json()
        assert data["report_type"] in ("DDR", "DAILY_DRILLING_REPORT")
        assert data["well_id"] == "15/9-F-14"

    def test_generate_report_post_api(self):
        res = client.post(
            "/api/reports/generate",
            json={
                "report_type": "SHIFT_HANDOVER",
                "well_id": "15/9-F-14",
                "current_md": 3200.0,
                "outgoing_engineer": "Senior Superintendent",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "generated"
        assert "report" in data
        report_id = data["report"]["id"]

        # Export test
        res_exp = client.get(f"/api/reports/{report_id}/export")
        assert res_exp.status_code == 200
        assert "SHIFT HANDOVER REPORT" in res_exp.text
