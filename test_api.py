"""
tests/api/test_api.py — API-level tests using requests.
"""

import pytest


@pytest.mark.api
class TestAPIHealth:
    def test_health_endpoint_returns_200(self, api_agent):
        result = api_agent.health_check("/health")
        assert result["ok"], f"Health check failed: {result}"

    def test_root_returns_200(self, api_agent):
        r = api_agent.get("/")
        assert r.status_code == 200

    def test_404_on_missing_route(self, api_agent):
        r = api_agent.get("/this-route-does-not-exist-xyz")
        assert r.status_code == 404


@pytest.mark.api
class TestAPIResponses:
    def test_response_is_json(self, api_agent):
        """Assumes /api returns JSON — adjust path for your target."""
        r = api_agent.get("/api")
        assert "application/json" in r.headers.get("Content-Type", "")

    def test_response_time_under_2s(self, api_agent):
        r = api_agent.get("/")
        assert r.elapsed.total_seconds() < 2.0, (
            f"Slow response: {r.elapsed.total_seconds():.2f}s"
        )

    def test_post_creates_resource(self, api_agent):
        """Example POST test — customize payload and path."""
        payload = {"name": "test_item", "value": 42}
        r = api_agent.post("/api/items", json_body=payload)
        # Accept 200 or 201
        assert r.status_code in (200, 201), f"Unexpected status: {r.status_code}"
