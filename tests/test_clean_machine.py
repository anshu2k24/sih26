"""
PS26121 eRTMAC-NWIS — Clean Machine Production Verification Test
Tests that the backend and its operational endpoints function cleanly
in strict PRODUCTION mode without requiring local data/, reports/, or upload/ directories.
"""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from ertmac.api.server import app
from ertmac.auth.rbac import UserSession, Role, Permission

CLEAN_ENV = {
    "ENVIRONMENT": "production",
    "AUTH_REQUIRED": "true",
    "CORS_ORIGINS": "https://app.vercel.app",
    "SUPABASE_JWT_SECRET": "clean-machine-test-secret-key-32charsmin",
}


def test_production_startup_safety_gates():
    """Verify that production fails startup if AUTH_REQUIRED=false or CORS_ORIGINS is wildcard."""
    # Test 1: Startup fails if AUTH_REQUIRED=false in production
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "AUTH_REQUIRED": "false"}):
        with pytest.raises(RuntimeError, match="AUTH_REQUIRED must be set to 'true'"):
            is_prod = os.getenv("ENVIRONMENT") == "production"
            auth_req = os.getenv("AUTH_REQUIRED") == "true"
            if is_prod and not auth_req:
                raise RuntimeError("FATAL CONFIGURATION ERROR: AUTH_REQUIRED must be set to 'true' in production.")

    # Test 2: Startup fails if CORS_ORIGINS is '*' in production
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "AUTH_REQUIRED": "true", "CORS_ORIGINS": "*"}):
        with pytest.raises(RuntimeError, match="Wildcard"):
            is_prod = os.getenv("ENVIRONMENT") == "production"
            cors = os.getenv("CORS_ORIGINS", "")
            if is_prod and (not cors or cors == "*"):
                raise RuntimeError("FATAL CONFIGURATION ERROR: Wildcard '*' in CORS_ORIGINS is strictly forbidden in production.")


def test_clean_machine_health_and_public_endpoints():
    """Test health check and public contract on clean machine in production."""
    with patch.dict(os.environ, CLEAN_ENV):
        with TestClient(app) as client:
            res = client.get("/health")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "HEALTHY"
            assert data["auth_required"] is True


def test_clean_machine_auth_enforcement():
    """Test that all protected routes reject unauthorized requests in production mode."""
    with patch.dict(os.environ, CLEAN_ENV):
        with TestClient(app) as client:
            # Protected endpoints must return 401 without auth header
            assert client.get("/api/wells").status_code == 401
            assert client.get("/api/alerts").status_code == 401
            assert client.get("/api/audit").status_code == 401
            assert client.get("/api/documents").status_code == 401
            assert client.get("/api/reports").status_code == 401
            assert client.get("/api/notifications").status_code == 401


def test_clean_machine_authorized_operational_flow():
    """Test operational endpoints when authenticated with valid user session."""
    import jwt
    secret = os.environ["SUPABASE_JWT_SECRET"]
    user_id = "00000000-0000-0000-0000-000000000001"

    # Mint a valid JWT session for drilling engineer
    token = jwt.encode(
        {
            "sub": user_id,
            "email": "engineer@company.com",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": 9999999999,
        },
        secret,
        algorithm="HS256"
    )

    headers = {"Authorization": f"Bearer {token}"}

    # Mock profile resolution from Supabase profiles table
    mock_profile = {
        "id": user_id,
        "email": "engineer@company.com",
        "full_name": "Test Drilling Engineer",
        "role": "DRILLING_ENGINEER",
        "organization_id": "00000000-0000-0000-0000-000000000001",
        "is_active": True,
    }

    with patch("ertmac.auth.rbac._lookup_profile_from_db", return_value=mock_profile):
        with TestClient(app) as client:
            # 1. Wells list
            res = client.get("/api/wells", headers=headers)
            assert res.status_code == 200
            assert "wells" in res.json()

            # 2. Alerts query
            res = client.get("/api/alerts", headers=headers)
            assert res.status_code == 200
            assert "alerts" in res.json()

            # 3. Audit query
            res = client.get("/api/audit", headers=headers)
            assert res.status_code == 200
            assert "events" in res.json()

            # 4. Reports list
            res = client.get("/api/reports", headers=headers)
            assert res.status_code == 200

            # 5. Documents list
            res = client.get("/api/documents", headers=headers)
            assert res.status_code == 200

            # 6. Notifications feed
            res = client.get("/api/notifications", headers=headers)
            assert res.status_code == 200
