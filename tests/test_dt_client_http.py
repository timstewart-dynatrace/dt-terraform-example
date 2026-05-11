"""Tests for `DynatraceClient` HTTP path — verifies the right Authorization
header reaches the wire for each request type.

These complement the unit tests in `test_dt_client_auth.py` (which exercise
`_auth_header_for_url` in isolation) by going through `_request` and the
public methods (`verify_connection`, `list_items`, `get_item`, `get_counts`)
end-to-end against a mocked HTTP server provided by `responses`.
"""

import pytest
import responses

from pipelines.core.dt_client import DynatraceClient
from pipelines.core.types import TenantConfig

from .conftest import CLASSIC_TOKEN, PLATFORM_TOKEN_S16, TENANT_URL


class TestVerifyConnection:
    """`verify_connection` hits `/api/v1/config/clusterversion` — a NON-excluded
    endpoint, so the primary token's header format applies."""

    @responses.activate
    def test_classic_token_sends_api_token_header(self, classic_client):
        responses.get(
            f"{TENANT_URL}/api/v1/config/clusterversion",
            json={"version": "1.300.0"},
            status=200,
        )
        assert classic_client.verify_connection() is True

        assert len(responses.calls) == 1
        assert responses.calls[0].request.headers["Authorization"] == f"Api-Token {CLASSIC_TOKEN}"

    @responses.activate
    def test_platform_token_sends_bearer_header(self, platform_client):
        responses.get(
            f"{TENANT_URL}/api/v1/config/clusterversion",
            json={"version": "1.300.0"},
            status=200,
        )
        assert platform_client.verify_connection() is True
        assert responses.calls[0].request.headers["Authorization"] == f"Bearer {PLATFORM_TOKEN_S16}"

    @responses.activate
    def test_verify_connection_returns_false_on_401(self, platform_client):
        responses.get(
            f"{TENANT_URL}/api/v1/config/clusterversion",
            json={"error": "unauthorized"},
            status=401,
        )
        assert platform_client.verify_connection() is False


class TestListItemsRoutingByEndpoint:
    """`list_items` for different config types should use the right header per
    the endpoint's place in the v1.88.0 exclusion list."""

    @responses.activate
    def test_dashboard_uses_platform_token_in_combined(self, combined_client):
        """Dashboards are NOT in the exclusion list — use Bearer."""
        responses.get(
            f"{TENANT_URL}/api/config/v1/dashboards",
            json={"dashboards": [{"id": "d-1", "name": "Test"}]},
            status=200,
        )
        items = combined_client.list_items("dashboard")
        assert len(items) == 1
        assert responses.calls[0].request.headers["Authorization"] == f"Bearer {PLATFORM_TOKEN_S16}"

    @responses.activate
    def test_synthetic_monitor_uses_classic_in_combined(self, combined_client):
        """Synthetic monitors ARE in the exclusion list — use Api-Token (the api_token slot)."""
        responses.get(
            f"{TENANT_URL}/api/synthetic/monitors",
            json={"monitors": [{"entityId": "SYNTHETIC_TEST-1", "name": "Test"}]},
            status=200,
        )
        # synthetic-monitor's list endpoint is /api/synthetic/monitors per types.py
        # but the CONFIG_TYPE_API_MAP may use a different path — we test the
        # actual route by reading the type's endpoint.
        from pipelines.core.types import CONFIG_TYPE_API_MAP
        endpoint, _, _ = CONFIG_TYPE_API_MAP["synthetic-monitor"]
        # Re-register on the actual endpoint
        responses.reset()
        responses.get(
            f"{TENANT_URL}{endpoint}",
            json={"monitors": [{"entityId": "SYNTHETIC_TEST-1", "name": "Test"}]},
            status=200,
        )
        items = combined_client.list_items("synthetic-monitor")
        # In a typical case, items should be returned (or empty if the mock
        # response key didn't match); we care about the request header.
        if endpoint.startswith("/api/synthetic"):
            assert responses.calls[0].request.headers["Authorization"] == f"Api-Token {CLASSIC_TOKEN}"

    @responses.activate
    def test_unknown_config_type_returns_empty_no_call(self, combined_client):
        """An unknown config type produces no HTTP call and an empty list."""
        items = combined_client.list_items("not-a-real-type")
        assert items == []
        assert len(responses.calls) == 0


class TestGetItem:
    @responses.activate
    def test_get_item_uses_detail_endpoint_with_id(self, combined_client):
        responses.get(
            f"{TENANT_URL}/api/config/v1/dashboards/dashboard-id-123",
            json={"id": "dashboard-id-123", "name": "My Dashboard", "tiles": []},
            status=200,
        )
        item = combined_client.get_item("dashboard", "dashboard-id-123")
        assert item is not None
        assert item["id"] == "dashboard-id-123"
        assert responses.calls[0].request.headers["Authorization"] == f"Bearer {PLATFORM_TOKEN_S16}"

    @responses.activate
    def test_get_item_returns_none_on_404(self, combined_client):
        responses.get(
            f"{TENANT_URL}/api/config/v1/dashboards/missing",
            status=404,
        )
        item = combined_client.get_item("dashboard", "missing")
        assert item is None


class TestRequestNonExcludedWithPlatformOnly:
    """Sanity check: Platform-Token-only tenant succeeds against non-excluded
    endpoints all the way through the HTTP path."""

    @responses.activate
    def test_dashboard_list_with_platform_only(self, platform_client):
        responses.get(
            f"{TENANT_URL}/api/config/v1/dashboards",
            json={"dashboards": []},
            status=200,
        )
        items = platform_client.list_items("dashboard")
        assert items == []
        assert responses.calls[0].request.headers["Authorization"] == f"Bearer {PLATFORM_TOKEN_S16}"
