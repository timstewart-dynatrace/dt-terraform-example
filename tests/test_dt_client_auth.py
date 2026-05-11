"""Tests for `DynatraceClient._auth_header_for_url` — per-request auth routing.

This is the heart of the combined-auth model from Phase 02. Every scenario from
the Phase 02 PR's smoke checks is encoded here.
"""

import pytest

from pipelines.core.types import TenantConfig
from pipelines.core.dt_client import DynatraceClient, MissingClassicTokenError

from .conftest import CLASSIC_TOKEN, PLATFORM_TOKEN_S16, PLATFORM_TOKEN_S01, TENANT_URL


class TestBackwardCompatClassicOnly:
    """A tenant configured with only `*_TENANT_TOKEN=dt0c01...` must behave
    exactly as it did before Phase 02 — Api-Token header for every endpoint."""

    def test_classic_token_on_non_excluded_endpoint(self, classic_client):
        h = classic_client._auth_header_for_url("/api/config/v1/dashboards")
        assert h == f"Api-Token {CLASSIC_TOKEN}"

    def test_classic_token_on_excluded_endpoint_falls_back(self, classic_client):
        """Excluded endpoint with no separate api_token — the primary
        classic-shaped token gets reused via the fall-back path."""
        h = classic_client._auth_header_for_url("/api/synthetic/monitors")
        assert h == f"Api-Token {CLASSIC_TOKEN}"

    def test_classic_token_on_settings_v2(self, classic_client):
        """Settings 2.0 also accepts classic API Tokens."""
        h = classic_client._auth_header_for_url("/api/v2/settings/objects")
        assert h == f"Api-Token {CLASSIC_TOKEN}"


class TestPlatformTokenOnly:
    """A tenant configured with only `*_TENANT_TOKEN=dt0s16...` (or dt0s01)
    must use Bearer on non-excluded endpoints and error on excluded."""

    def test_platform_s16_on_non_excluded_endpoint(self, platform_client):
        h = platform_client._auth_header_for_url("/api/config/v1/dashboards")
        assert h == f"Bearer {PLATFORM_TOKEN_S16}"

    def test_platform_s01_on_non_excluded_endpoint(self, platform_tenant_dt0s01):
        client = DynatraceClient(platform_tenant_dt0s01)
        h = client._auth_header_for_url("/api/v2/settings/objects")
        assert h == f"Bearer {PLATFORM_TOKEN_S01}"

    def test_platform_on_excluded_raises_clear_error(self, platform_client):
        """Excluded endpoint + no classic token configured = MissingClassicTokenError."""
        with pytest.raises(MissingClassicTokenError) as exc_info:
            platform_client._auth_header_for_url("/api/synthetic/monitors")

        msg = str(exc_info.value)
        # Error must name the failing path so the operator knows what failed
        assert "/api/synthetic/monitors" in msg
        # Error must point at the env var to set
        assert "api_token" in msg.lower() or "API Token" in msg

    def test_platform_on_excluded_does_not_hit_network(self, platform_client):
        """The error is raised pre-network — no HTTP call should occur.

        Regression check: an earlier draft might have made the request and
        only failed on 401. We want the error to surface synchronously from
        the header-building step.
        """
        # If _auth_header_for_url tried to contact the tenant, it would error
        # with a connection error against the fake TENANT_URL. We assert
        # specifically MissingClassicTokenError (not ConnectionError).
        with pytest.raises(MissingClassicTokenError):
            platform_client._auth_header_for_url("/api/v2/slo")


class TestCombinedAuth:
    """Tenant configured with both Platform Token (primary) and classic API Token
    (secondary) — the canonical Phase 02 setup."""

    def test_combined_uses_platform_for_non_excluded(self, combined_client):
        h = combined_client._auth_header_for_url("/api/config/v1/dashboards")
        assert h == f"Bearer {PLATFORM_TOKEN_S16}"

    def test_combined_uses_classic_for_excluded(self, combined_client):
        h = combined_client._auth_header_for_url("/api/synthetic/monitors")
        assert h == f"Api-Token {CLASSIC_TOKEN}"

    def test_combined_uses_classic_for_network_zones(self, combined_client):
        h = combined_client._auth_header_for_url("/api/v1/networkZones")
        assert h == f"Api-Token {CLASSIC_TOKEN}"

    def test_combined_uses_classic_for_slo(self, combined_client):
        h = combined_client._auth_header_for_url("/api/v2/slo")
        assert h == f"Api-Token {CLASSIC_TOKEN}"

    def test_combined_uses_platform_for_management_zones(self, combined_client):
        """Management Zones is NOT in the v1.88.0 exclusion list — Platform Token works."""
        h = combined_client._auth_header_for_url("/api/config/v1/managementZones")
        assert h == f"Bearer {PLATFORM_TOKEN_S16}"


class TestApiTokenOnlySlot:
    """Edge case: tenant has only api_token set, no primary token.

    This is a misconfiguration in practice (the primary `token` is required),
    but we should not crash with an undefined behaviour."""

    def test_api_token_only_on_excluded_uses_it(self):
        tenant = TenantConfig(url=TENANT_URL, token="", api_token=CLASSIC_TOKEN)
        client = DynatraceClient(tenant)
        h = client._auth_header_for_url("/api/synthetic/monitors")
        assert h == f"Api-Token {CLASSIC_TOKEN}"

    def test_api_token_only_on_non_excluded_uses_empty_primary(self):
        """Non-excluded endpoint uses the primary token's prefix. An empty
        primary token falls through `_header_for_token` to the Api-Token
        default — which won't authenticate, but doesn't crash."""
        tenant = TenantConfig(url=TENANT_URL, token="", api_token=CLASSIC_TOKEN)
        client = DynatraceClient(tenant)
        h = client._auth_header_for_url("/api/config/v1/dashboards")
        # Empty token → Api-Token <empty> via the fallback in _header_for_token
        assert h == "Api-Token "
