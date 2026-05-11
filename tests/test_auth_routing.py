"""Tests for `_needs_classic_api_token` — URL pattern matching for the v1.88.0 exclusion list.

Source-of-truth for the exclusion list:
https://github.com/dynatrace-oss/terraform-provider-dynatrace/releases/tag/v1.88.0
"The OAuth functionality has been removed for the following resources, which previously relied
on the `environment-api:*` scopes."
"""

import pytest

from pipelines.core.dt_client import _needs_classic_api_token


class TestNeedsClassicApiTokenPositive:
    """Paths that ARE in the v1.88.0 exclusion list — must return True."""

    @pytest.mark.parametrize(
        "path",
        [
            # Synthetic monitors + locations + nodes
            "/api/synthetic/monitors",
            "/api/synthetic/monitors/SYNTHETIC_TEST-1234567890",
            "/api/synthetic/locations",
            "/api/synthetic/nodes",
            "/api/v1/synthetic/monitors",
            "/api/v2/synthetic/locations",
            # Network zones
            "/api/v1/networkZones",
            "/api/v1/networkZones/zone-name",
            "/api/v2/networkZones/zone-name",
            # SLO v1 and v2
            "/api/v1/slo",
            "/api/v1/slo/slo-id-123",
            "/api/v2/slo",
            "/api/v2/slo/slo-id-123",
            # Tokens management
            "/api/v2/tokens",
            "/api/v2/tokens/abc123",
            "/api/v2/activeGateTokens",
            "/api/v2/activeGateTokens/token-id",
            # Credentials vault
            "/api/v1/credentials",
            "/api/v1/credentials/CREDENTIALS_VAULT-1234",
            "/api/v2/credentials",
            # Custom devices
            "/api/v1/entity/customDevices",
            "/api/v1/entity/custom-device/CUSTOM_DEVICE-1234",
            "/api/v2/customDevices",
            # Custom tags
            "/api/config/v1/customTags",
            "/api/config/v1/customTags/HOST-123",
            # Host monitoring mode
            "/api/config/v1/hostMonitoringMode",
            "/api/config/v1/hostMonitoringMode/HOST-123",
            # Key requests
            "/api/config/v1/service/keyRequests",
            "/api/config/v1/service/keyRequests/SERVICE-123",
            # Hub extension active version + monitoring configurations
            "/api/v2/hub/extensions/com.dynatrace.extension.snmp/active",
            "/api/v2/extensions/com.dynatrace.extension.snmp/monitoringConfigurations",
        ],
    )
    def test_excluded_path_needs_classic_token(self, path: str):
        assert _needs_classic_api_token(path) is True, (
            f"Expected {path!r} to be in the v1.88.0 exclusion list. "
            f"If this path's auth changed in a newer provider release, "
            f"update _CLASSIC_API_TOKEN_URL_PATTERNS in dt_client.py."
        )


class TestNeedsClassicApiTokenNegative:
    """Paths that are NOT in the v1.88.0 exclusion list — must return False.

    These represent resources that the AUTOM ecosystem confirms work with
    Platform Tokens today (or where Platform Token coverage was unaffected
    by v1.88.0).
    """

    @pytest.mark.parametrize(
        "path",
        [
            # The 7 classic-config-API resources that stay Platform-Token-eligible
            "/api/config/v1/alertingProfiles",
            "/api/config/v1/alertingProfiles/profile-id",
            "/api/config/v1/autoTags",
            "/api/config/v1/dashboards",
            "/api/config/v1/dashboards/dashboard-id",
            "/api/config/v1/managementZones",
            "/api/config/v1/notifications",
            "/api/config/v1/requestNamings",
            "/api/config/v1/extensions",
            # Settings 2.0 (Platform-Token native)
            "/api/v2/settings/objects",
            "/api/v2/settings/schemas",
            "/api/v2/settings/schemas/builtin:management-zones",
            # Tenant version check (used by verify_connection)
            "/api/v1/config/clusterversion",
            # Entity API (read-side, broadly Platform-Token-eligible)
            "/api/v2/entities",
            "/api/v2/entities/HOST-123",
            # DQL / Grail (Platform-Token native)
            "/platform/storage/query/v1/query:execute",
        ],
    )
    def test_non_excluded_path_does_not_need_classic_token(self, path: str):
        assert _needs_classic_api_token(path) is False, (
            f"Expected {path!r} to NOT need a classic API Token. "
            f"If this changed, the v1.88.0 boundary may have shifted; "
            f"check current provider release notes."
        )

    def test_empty_path_returns_false(self):
        """Defensive: an empty path is not in any exclusion pattern."""
        assert _needs_classic_api_token("") is False
