"""
PS26121 — Automated Email Rate Limiting & Login Account Routing Tests
Verifies:
1. Dynamic configuration of email_rate_limit_per_sec (default 4/sec) and send_to_login_account in Settings API.
2. Sliding-window rate limiting of email dispatches (max 4 emails per second).
3. 5th email in a 1-second burst is throttled and flagged as 'RATE_LIMITED'.
4. Recovery after the 1-second rolling window expires.
"""

import time
import uuid
import pytest
from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.config.settings import get_system_settings, update_system_settings
from ertmac.notifications.delivery import NotificationDeliveryEngine, email_rate_limiter

client = TestClient(app)


class TestEmailRateLimitingAndSettings:

    def setup_method(self):
        email_rate_limiter.reset()
        update_system_settings({
            "email_rate_limit_per_sec": 4,
            "send_to_login_account": True,
            "notification_recipient_email": "operator@company.com"
        })

    def test_settings_includes_rate_limit_and_login_account(self):
        # 1. GET settings
        res = client.get("/api/settings")
        assert res.status_code == 200
        data = res.json()
        assert "email_rate_limit_per_sec" in data
        assert "send_to_login_account" in data
        assert data["email_rate_limit_per_sec"] == 4

        # 2. PUT custom rate limit and routing
        update_payload = {
            "email_rate_limit_per_sec": 3,
            "send_to_login_account": True,
        }
        res_put = client.put("/api/settings", json=update_payload)
        assert res_put.status_code == 200
        put_data = res_put.json()
        assert put_data["email_rate_limit_per_sec"] == 3
        assert put_data["send_to_login_account"] is True

        # Restore
        update_system_settings({"email_rate_limit_per_sec": 4})

    def test_email_rate_limit_enforcement_max_4_per_sec(self, monkeypatch):
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        monkeypatch.setattr(NotificationDeliveryEngine, "_record_delivery", lambda rec: None)
        email_rate_limiter.reset()
        update_system_settings({"email_rate_limit_per_sec": 4})

        def create_dummy_alert(idx: int):
            return {
                "alert_id": f"ALT_RATE_{idx}_{uuid.uuid4().hex[:6]}",
                "well_id": "15/9-F-15",
                "title": f"Test Hazard {idx}",
                "severity": "CRITICAL",
                "current_md": 2500.0 + idx,
                "evidence": f"Burst test {idx}",
                "disclaimer": "HISTORICAL OFFSET EVENT — NOT A PREDICTION",
            }

        # Dispatch 4 emails rapidly within the same second
        results = []
        for i in range(4):
            record = NotificationDeliveryEngine.dispatch_alert_email(
                alert_dict=create_dummy_alert(i),
                recipient_email="operator@test.com",
            )
            results.append(record)

        # All 4 emails should be allowed through the rate limiter (not RATE_LIMITED)
        for i, rec in enumerate(results):
            assert rec["status"] != "RATE_LIMITED", f"Email {i} should not be rate limited"

        # 5th email dispatched immediately within the same 1-second window MUST be rate-limited
        fifth_record = NotificationDeliveryEngine.dispatch_alert_email(
            alert_dict=create_dummy_alert(4),
            recipient_email="operator@test.com",
        )
        assert fifth_record["status"] == "RATE_LIMITED"
        assert "Rate limit exceeded" in fifth_record["error_message"]

        # Wait 1.05 seconds for the sliding window to roll forward
        time.sleep(1.05)

        # After window expires, new email must be allowed through again
        recovery_record = NotificationDeliveryEngine.dispatch_alert_email(
            alert_dict=create_dummy_alert(5),
            recipient_email="operator@test.com",
        )
        assert recovery_record["status"] != "RATE_LIMITED"
