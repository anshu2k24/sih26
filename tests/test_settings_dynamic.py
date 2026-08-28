"""
PS26121 — Dynamic Settings API & Manager Unit Tests
"""

import pytest
from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.config.settings import get_notification_recipient_email, update_system_settings

client = TestClient(app)


class TestDynamicSettings:

    def test_settings_get_and_put_workflow(self):
        # 1. GET initial settings
        res_get = client.get("/api/settings")
        assert res_get.status_code == 200
        settings_data = res_get.json()
        assert "notification_recipient_email" in settings_data

        # 2. PUT updated notification email
        new_email = "custom.operator@equinor.com"
        res_put = client.put("/api/settings", json={"notification_recipient_email": new_email})
        assert res_put.status_code == 200
        updated_data = res_put.json()
        assert updated_data["notification_recipient_email"] == new_email

        # 3. Verify settings helper returns updated email
        assert get_notification_recipient_email() == new_email

        # 4. Reset back to default email
        update_system_settings({"notification_recipient_email": "operator@company.com"})

