"""
PS26121 eRTMAC-NWIS — WebSocket Authentication Security Tests
"""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from ertmac.api.server import app

client = TestClient(app)


class TestWebSocketAuthentication:

    def test_websocket_dev_mode_connects(self):
        """In dev mode (AUTH_REQUIRED=false), websocket connects without token."""
        with patch.dict(os.environ, {"AUTH_REQUIRED": "false"}):
            with client.websocket_connect("/api/ws/wells/15%2F9-F-14") as websocket:
                data = websocket.receive_json()
                assert data["type"] == "stream_status"
                assert data["data"]["well_id"] == "15/9-F-14"

    def test_websocket_auth_required_missing_token_closed(self):
        """When AUTH_REQUIRED=true, connecting without token closes websocket with 1008."""
        with patch.dict(os.environ, {"AUTH_REQUIRED": "true"}):
            with pytest.raises(Exception):
                with client.websocket_connect("/api/ws/wells/15%2F9-F-14") as websocket:
                    websocket.receive_json()

    def test_websocket_auth_required_invalid_token_closed(self):
        """When AUTH_REQUIRED=true, invalid token closes websocket with 1008."""
        with patch.dict(os.environ, {"AUTH_REQUIRED": "true", "SUPABASE_JWT_SECRET": "test-jwt-secret-key-for-unit-tests"}):
            with pytest.raises(Exception):
                with client.websocket_connect("/api/ws/wells/15%2F9-F-14?token=invalid_jwt") as websocket:
                    websocket.receive_json()

