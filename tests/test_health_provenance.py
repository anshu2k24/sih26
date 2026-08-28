"""
PS26121 Phase 8 — System Health & Data Provenance Test Suite

Tests verify:
1. Detailed health endpoint returns healthy components
2. OCR status check handles missing binary gracefully
3. Provenance registry returns authentic dataset sources (Equinor Volve & NPD)
4. Enforces STRICT_ZERO_FABRICATION policy string
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("AUTH_REQUIRED", "false")

from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.documents.extractor import check_tesseract_available

client = TestClient(app)


class TestHealthAndProvenance:
    def test_detailed_health_endpoint(self):
        res = client.get("/health/detailed")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "OPERATIONAL"
        assert "components" in data
        assert "database" in data["components"]
        assert "ocr_engine" in data["components"]
        assert "data_sources" in data["components"]
        assert "ml_gate" in data["components"]
        assert data["components"]["ml_gate"]["status"] == "ML_NOT_READY"

    def test_provenance_registry_endpoint(self):
        res = client.get("/api/provenance")
        assert res.status_code == 200
        data = res.json()
        assert "STRICT_ZERO_FABRICATION" in data["data_fabrication_policy"]
        assert len(data["provenance_registry"]) >= 3

        datasets = [item["dataset_name"] for item in data["provenance_registry"]]
        assert any("Equinor Volve" in d for d in datasets)
        assert any("NPD Official" in d for d in datasets)

    def test_ocr_availability_check(self):
        avail = check_tesseract_available()
        assert isinstance(avail, bool)
