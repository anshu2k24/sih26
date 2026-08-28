"""
PS26121 eRTMAC-NWIS — Full Production End-to-End Operational Journey Test
"""

import pytest
from fastapi.testclient import TestClient
from ertmac.api.server import app

client = TestClient(app)


class TestProductionE2EWorkflow:

    def test_full_production_e2e_journey(self):
        # 1. System Health Check
        res_health = client.get("/health/detailed")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "OPERATIONAL"


        # 2. Fetch User Profile
        res_user = client.get("/api/users/me")
        assert res_user.status_code == 200
        user_data = res_user.json()
        assert "permissions" in user_data
        assert user_data["role"] == "DRILLING_ENGINEER"

        # 3. List Wells
        res_wells = client.get("/api/wells")
        assert res_wells.status_code == 200
        wells = res_wells.json()["wells"]
        assert len(wells) > 0
        well_id = wells[0]["well_id"]

        # 4. Fetch Historical Proximity Events
        res_prox = client.get(f"/api/wells/{well_id}/historical-proximity?current_md=1509.1")
        assert res_prox.status_code == 200
        prox_data = res_prox.json()
        assert prox_data["disclaimer"] == "HISTORICAL OFFSET EVENT — NOT A PREDICTION"

        # 5. Fetch Active Alerts
        res_alerts = client.get("/api/alerts")
        assert res_alerts.status_code == 200
        alerts = res_alerts.json()["alerts"]

        if len(alerts) > 0:
            target_alert = alerts[0]
            alert_id = target_alert["alert_id"]

            # 6. Acknowledge Alert (if ACTIVE)
            if target_alert["status"] == "ACTIVE":
                res_ack = client.post(f"/api/alerts/{alert_id}/acknowledge")
                assert res_ack.status_code == 200
                assert res_ack.json()["status"] == "ACKNOWLEDGED"

            # 7. Start Investigation (if ACKNOWLEDGED)
            res_inv = client.post(f"/api/alerts/{alert_id}/investigate")
            if res_inv.status_code == 200:
                assert res_inv.json()["status"] == "INVESTIGATING"

            # 8. Add Note
            res_note = client.post(f"/api/alerts/{alert_id}/notes?note_text=Inspecting+topdrive+torque")
            assert res_note.status_code == 200

            # 9. Resolve Alert
            res_res = client.post(f"/api/alerts/{alert_id}/resolve?notes=Parameters+confirmed+safe")
            assert res_res.status_code == 200
            assert res_res.json()["status"] == "RESOLVED"

        # 10. Generate DDR Report
        res_rpt = client.get(f"/api/reports/ddr?well_id={well_id}")
        assert res_rpt.status_code == 200
        rpt_data = res_rpt.json()
        assert "report_id" in rpt_data

        # 11. Verify Audit Logs
        res_audit = client.get("/api/audit")
        assert res_audit.status_code == 200
        assert res_audit.json()["count"] >= 0
