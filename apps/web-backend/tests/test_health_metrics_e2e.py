"""
End-to-end tests for health and metrics endpoints.

Verifies /health/live, /health/ready, and /metrics endpoints
are registered, respond correctly, and return expected formats.
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Health endpoint tests
# ---------------------------------------------------------------------------


class TestLivenessEndpoint:
    """Tests for GET /health/live (liveness probe)."""

    def test_liveness_returns_200(self, test_client: TestClient):
        """Liveness probe always returns HTTP 200."""
        response = test_client.get("/health/live")
        assert response.status_code == 200

    def test_liveness_returns_alive_status(self, test_client: TestClient):
        """Liveness probe body contains status=alive."""
        response = test_client.get("/health/live")
        data = response.json()
        assert data["status"] == "alive"

    def test_liveness_content_type_json(self, test_client: TestClient):
        """Liveness probe responds with JSON content type."""
        response = test_client.get("/health/live")
        assert "application/json" in response.headers["content-type"]

    def test_liveness_no_auth_required(self, test_client: TestClient):
        """Liveness probe is accessible without authentication."""
        # No auth headers passed – should still return 200
        response = test_client.get("/health/live")
        assert response.status_code == 200


class TestReadinessEndpoint:
    """Tests for GET /health/ready (readiness probe)."""

    def test_readiness_returns_200_or_503(self, test_client: TestClient):
        """Readiness probe returns either 200 (ready) or 503 (not ready)."""
        response = test_client.get("/health/ready")
        assert response.status_code in (200, 503)

    def test_readiness_200_contains_ready_status(self, test_client: TestClient):
        """When ready, body contains status=ready."""
        response = test_client.get("/health/ready")
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "ready"

    def test_readiness_503_contains_not_ready_status(self, test_client: TestClient):
        """When not ready, body contains status=not_ready with a reason."""
        response = test_client.get("/health/ready")
        if response.status_code == 503:
            data = response.json()
            # FastAPI HTTPException wraps the detail in {"detail": ...}
            detail = data.get("detail", data)
            assert detail.get("status") == "not_ready"
            assert "reason" in detail

    def test_readiness_no_auth_required(self, test_client: TestClient):
        """Readiness probe is accessible without authentication."""
        response = test_client.get("/health/ready")
        assert response.status_code in (200, 503)

    def test_readiness_content_type_json(self, test_client: TestClient):
        """Readiness probe responds with JSON content type."""
        response = test_client.get("/health/ready")
        assert "application/json" in response.headers["content-type"]


class TestDetailedHealthEndpoint:
    """Tests for GET /health/detailed (detailed health report)."""

    def test_detailed_health_returns_200(self, test_client: TestClient):
        """Detailed health endpoint returns HTTP 200."""
        response = test_client.get("/health/detailed")
        assert response.status_code == 200

    def test_detailed_health_has_required_fields(self, test_client: TestClient):
        """Detailed health response contains all required fields."""
        response = test_client.get("/health/detailed")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "headless_mode" in data
        assert "components" in data

    def test_detailed_health_status_is_valid(self, test_client: TestClient):
        """Detailed health overall status is one of the expected values."""
        response = test_client.get("/health/detailed")
        data = response.json()
        assert data["status"] in ("healthy", "degraded", "unhealthy")

    def test_detailed_health_uptime_is_positive(self, test_client: TestClient):
        """Uptime must be a non-negative number."""
        response = test_client.get("/health/detailed")
        data = response.json()
        assert data["uptime_seconds"] >= 0

    def test_detailed_health_headless_mode_is_bool(self, test_client: TestClient):
        """headless_mode field must be a boolean."""
        response = test_client.get("/health/detailed")
        data = response.json()
        assert isinstance(data["headless_mode"], bool)

    def test_detailed_health_components_structure(self, test_client: TestClient):
        """Components dict contains entries with status field."""
        response = test_client.get("/health/detailed")
        data = response.json()
        components = data["components"]
        assert isinstance(components, dict)
        for _name, comp in components.items():
            assert "status" in comp
            assert comp["status"] in ("ok", "degraded", "unavailable")


# ---------------------------------------------------------------------------
# Metrics endpoint tests
# ---------------------------------------------------------------------------


class TestMetricsEndpoint:
    """Tests for GET /metrics (Prometheus metrics)."""

    def test_metrics_returns_200(self, test_client: TestClient):
        """Metrics endpoint returns HTTP 200."""
        response = test_client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type_prometheus(self, test_client: TestClient):
        """Metrics endpoint returns Prometheus text content type."""
        response = test_client.get("/metrics")
        # Prometheus content type includes version=0.0.4
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type

    def test_metrics_body_is_non_empty(self, test_client: TestClient):
        """Metrics response body is non-empty."""
        response = test_client.get("/metrics")
        assert len(response.text) > 0

    def test_metrics_contains_uptime_metric(self, test_client: TestClient):
        """Metrics body contains the auto_claude_uptime_seconds metric."""
        response = test_client.get("/metrics")
        assert "auto_claude_uptime_seconds" in response.text

    def test_metrics_contains_app_info(self, test_client: TestClient):
        """Metrics body contains the auto_claude_app_info metric."""
        response = test_client.get("/metrics")
        assert "auto_claude_app" in response.text

    def test_metrics_contains_http_requests_counter(self, test_client: TestClient):
        """Metrics body contains the HTTP requests counter."""
        response = test_client.get("/metrics")
        assert "auto_claude_http_requests_total" in response.text

    def test_metrics_no_auth_required(self, test_client: TestClient):
        """Metrics endpoint is accessible without authentication (scraper-friendly)."""
        response = test_client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_prometheus_format_lines(self, test_client: TestClient):
        """Metrics body follows Prometheus text format (# HELP / # TYPE lines)."""
        response = test_client.get("/metrics")
        lines = response.text.splitlines()
        help_lines = [l for l in lines if l.startswith("# HELP")]
        type_lines = [l for l in lines if l.startswith("# TYPE")]
        assert len(help_lines) > 0, "Expected at least one # HELP line"
        assert len(type_lines) > 0, "Expected at least one # TYPE line"


# ---------------------------------------------------------------------------
# Route registration smoke test
# ---------------------------------------------------------------------------


def test_health_and_metrics_routes_registered():
    """Verify /health/* and /metrics routes are registered on the app."""
    from main import app

    paths = [route.path for route in app.routes]
    assert any("/health" in p for p in paths), f"/health not found in routes: {paths}"
    assert any("/metrics" in p for p in paths), f"/metrics not found in routes: {paths}"
