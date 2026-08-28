"""
PS26121 eRTMAC-NWIS — Analytics, Knowledge & Multi-Tenant Test Suite (Phases 9 - 13)
"""

import pytest
from fastapi.testclient import TestClient
from ertmac.api.server import app

client = TestClient(app)


class TestAnalyticsEndpoints:

    def test_analytics_summary_endpoint(self):
        res = client.get("/api/analytics/summary")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert "total_active_alerts" in data
        assert "monitored_wells_count" in data
        assert data["monitored_wells_count"] > 0

    def test_well_profile_analytics_endpoint(self):
        res = client.get("/api/analytics/wells/15%2F9-F-14/profile")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert "profile" in data
        assert data["profile"]["well_id"] == "15/9-F-14"
        assert "event_type_distribution" in data["profile"]
        assert "depth_range_distribution" in data["profile"]

    def test_alerts_trend_endpoint(self):
        res = client.get("/api/analytics/alerts/trend")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert isinstance(data["trend"], list)
        assert len(data["trend"]) > 0


class TestKnowledgeAdvancedFilters:

    def test_search_with_domain_and_source_filters(self):
        res = client.get("/api/knowledge/search?domain=DRILLING_OPERATIONS&document_source=DDR")
        assert res.status_code == 200
        data = res.json()
        assert "results" in data
        assert "provenance" in data


class TestMultiTenantAdminOrganizations:

    def test_admin_list_organizations(self):
        res = client.get("/api/admin/organizations")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert "organizations" in data
        assert len(data["organizations"]) > 0
        assert "name" in data["organizations"][0]

