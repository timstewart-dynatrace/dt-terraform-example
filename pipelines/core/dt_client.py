"""Dynatrace API client for configuration export and deployment.

Authentication model (combined auth):

- ``tenant.token`` is the primary credential. Auto-detected by prefix:

  - ``dt0s16`` / ``dt0s01`` → ``Authorization: Bearer <token>`` (Platform Token)
  - ``dt0c01``              → ``Authorization: Api-Token <token>`` (classic Access Token)

- ``tenant.api_token`` is an optional classic Access Token used only for the
  v1.88.0 exclusion list — endpoints that the Dynatrace Terraform provider
  removed from Platform-Token (OAuth) coverage in v1.88.0 (synthetic
  monitors, network monitors, custom devices, AG/API tokens, credentials,
  custom tags, host monitoring mode, key requests, hub extension active
  version + config, SLO v1/v2). These require a classic API Token.

Per-request, :meth:`_auth_header_for_url` returns the right Authorization
header tuple based on the URL pattern and the available tokens.

Source for the v1.88.0 boundary: ``dynatrace-oss/terraform-provider-dynatrace``
v1.88.0 release notes — *"The OAuth functionality has been removed for the
following resources, which previously relied on the* ``environment-api:*``
*scopes."* — https://github.com/dynatrace-oss/terraform-provider-dynatrace/releases/tag/v1.88.0
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from .types import (
    CONFIG_TYPE_API_MAP,
    ALL_CONFIG_TYPES,
    ExportResult,
    ExportFormat,
    TenantConfig,
)

logger = logging.getLogger("pipeline")


# URL patterns that require a classic API Token (the v1.88.0 exclusion list).
# These endpoints lost Platform-Token / OAuth support in the Dynatrace Terraform
# provider v1.88.0 release; the boundary tracks the underlying REST API.
_CLASSIC_API_TOKEN_URL_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r"^/api/synthetic/"),                  # synthetic monitors + locations + nodes
    re.compile(r"^/api/v1/synthetic/"),               # synthetic v1 endpoints
    re.compile(r"^/api/v2/synthetic/"),               # synthetic v2 endpoints
    re.compile(r"^/api/v1/networkZones"),             # network zones
    re.compile(r"^/api/v2/networkZones"),             # network zones v2
    re.compile(r"^/api/v2/slo"),                      # SLO v2
    re.compile(r"^/api/v1/slo"),                      # SLO v1
    re.compile(r"^/api/v2/tokens"),                   # API tokens management
    re.compile(r"^/api/v2/activeGateTokens"),         # ActiveGate tokens
    re.compile(r"^/api/v1/credentials"),              # credential vault
    re.compile(r"^/api/v2/credentials"),              # credential vault v2
    re.compile(r"^/api/v1/entity/(custom-device|customDevices)"),  # custom devices
    re.compile(r"^/api/v2/customDevices"),
    re.compile(r"^/api/config/v1/customTags"),        # custom tags
    re.compile(r"^/api/config/v1/hostMonitoringMode"),  # host monitoring mode
    re.compile(r"^/api/config/v1/service/keyRequests"),  # key requests
    re.compile(r"^/api/v2/hub/extensions/.*/active"),  # hub extension active version
    re.compile(r"^/api/v2/extensions/.+/monitoringConfigurations"),  # hub extension config
)


def _needs_classic_api_token(path: str) -> bool:
    """Return True if the given URL path requires a classic API Token.

    The path argument should be the URL path (e.g. ``/api/synthetic/monitors``),
    not the full URL. See :data:`_CLASSIC_API_TOKEN_URL_PATTERNS` for the
    v1.88.0 exclusion list this matches against.
    """
    return any(p.match(path) for p in _CLASSIC_API_TOKEN_URL_PATTERNS)


def _header_for_token(token: str) -> str:
    """Return the right Authorization header value for a Dynatrace token.

    - ``dt0s16`` / ``dt0s01`` prefix → ``Bearer <token>`` (Platform Token)
    - ``dt0c01`` prefix              → ``Api-Token <token>`` (classic Access Token)
    - unknown prefix                 → ``Api-Token <token>`` (back-compat default)
    """
    if token.startswith(("dt0s16.", "dt0s01.")):
        return f"Bearer {token}"
    return f"Api-Token {token}"


class MissingClassicTokenError(RuntimeError):
    """Raised when a request needs a classic API Token but none is configured.

    The error message names the failing URL path and tells the operator which
    env var to set.
    """


class DynatraceClient:
    """Dynatrace REST API client with combined-auth routing.

    See module docstring for the auth model.
    """

    def __init__(self, tenant: TenantConfig, timeout: int = 30):
        self.tenant = tenant
        self.url = tenant.url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = timeout
        # No session-level Authorization header — we set it per-request based on URL.

    def _auth_header_for_url(self, path: str) -> str:
        """Return the right Authorization header value for ``path``.

        Args:
            path: URL path (not the full URL). E.g. ``/api/config/v1/dashboards``.

        Returns:
            The full header value, e.g. ``"Bearer dt0s16.xxx"`` or
            ``"Api-Token dt0c01.xxx"``.

        Raises:
            MissingClassicTokenError: when ``path`` needs a classic API Token
                (per the v1.88.0 exclusion list) but the tenant config has
                neither an ``api_token`` set nor a ``dt0c01``-prefixed primary
                token to fall back on.
        """
        if _needs_classic_api_token(path):
            # Prefer the dedicated api_token slot
            if self.tenant.api_token:
                return f"Api-Token {self.tenant.api_token}"
            # Fall back to the primary token if it's already classic-shaped
            if self.tenant.token and self.tenant.token.startswith("dt0c01."):
                return f"Api-Token {self.tenant.token}"
            # Otherwise we cannot authenticate this endpoint
            raise MissingClassicTokenError(
                f"Endpoint {path} requires a classic API Token "
                f"(dt0c01 prefix). Set the *_TENANT_API_TOKEN env var or "
                f"the api_token field on the Tenant. See the v1.88.0 "
                f"exclusion list in dt_client.py for the full list of "
                f"affected endpoints."
            )

        # Non-excluded endpoint: use the primary token with prefix-detected header
        return _header_for_token(self.tenant.token)

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Issue a request with per-URL authentication."""
        headers = kwargs.pop("headers", {}) or {}
        headers["Authorization"] = self._auth_header_for_url(path)
        return self.session.request(method, f"{self.url}{path}", headers=headers, **kwargs)

    def verify_connection(self) -> bool:
        """Check that the tenant is reachable and the token is valid."""
        try:
            resp = self._request("GET", "/api/v1/config/clusterversion")
            resp.raise_for_status()
            logger.info(f"Connected to tenant: {self.url}")
            return True
        except Exception as e:
            logger.error(f"Connection failed for {self.url}: {e}")
            return False

    def list_items(self, config_type: str) -> List[Dict]:
        """List all items of a config type. Returns list of stub dicts."""
        api_info = CONFIG_TYPE_API_MAP.get(config_type)
        if not api_info:
            logger.warning(f"No API mapping for config type: {config_type}")
            return []

        endpoint, list_key, _ = api_info
        try:
            resp = self._request("GET", endpoint)
            resp.raise_for_status()
            return resp.json().get(list_key, [])
        except Exception as e:
            logger.warning(f"Failed to list {config_type}: {e}")
            return []

    def get_item(self, config_type: str, item_id: str) -> Optional[Dict]:
        """Fetch full configuration for a single item."""
        api_info = CONFIG_TYPE_API_MAP.get(config_type)
        if not api_info:
            return None

        _, _, detail_endpoint = api_info
        if not detail_endpoint:
            return None

        try:
            resp = self._request("GET", detail_endpoint.format(id=item_id))
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"Failed to get {config_type}/{item_id}: {e}")
            return None

    def get_counts(self, config_types: Optional[List[str]] = None) -> Dict[str, int]:
        """Get item counts per config type."""
        types = config_types or ALL_CONFIG_TYPES
        counts: Dict[str, int] = {}
        for ct in types:
            items = self.list_items(ct)
            counts[ct] = len(items)
        return counts

    def export_all(
        self,
        config_types: List[str],
        output_dir: Path,
    ) -> ExportResult:
        """Export all configs of specified types to JSON files.

        Args:
            config_types: List of config type names to export.
            output_dir: Directory to write JSON files into.

        Returns:
            ExportResult with counts and any failures.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        result = ExportResult(
            format=ExportFormat.TERRAFORM,  # raw JSON, format applied later
            output_dir=str(output_dir),
            config_types=config_types,
        )

        for config_type in config_types:
            items = self.list_items(config_type)
            if not items:
                result.items_exported[config_type] = 0
                continue

            type_dir = output_dir / config_type
            type_dir.mkdir(parents=True, exist_ok=True)

            api_info = CONFIG_TYPE_API_MAP.get(config_type)
            _, _, detail_endpoint = api_info if api_info else (None, None, None)
            exported = 0
            failed: List[str] = []

            for item in items:
                item_id = item.get("id", item.get("entityId", "unknown"))
                item_name = item.get("name", item_id)

                if detail_endpoint:
                    full_item = self.get_item(config_type, item_id)
                    if full_item is None:
                        failed.append(item_id)
                        continue
                else:
                    full_item = item

                safe_name = _sanitize_filename(item_name)
                out_file = type_dir / f"{safe_name}.json"
                out_file.write_text(json.dumps(full_item, indent=2))
                exported += 1

            result.items_exported[config_type] = exported
            if failed:
                result.items_failed[config_type] = failed

            logger.info(f"  {config_type}: {exported} exported" +
                        (f", {len(failed)} failed" if failed else ""))

        logger.info(f"Export complete: {result.total_count} total items")
        return result


def _sanitize_filename(name: str, max_len: int = 80) -> str:
    """Convert an item name to a safe filename."""
    safe = re.sub(r"[^\w\-]", "_", str(name))
    return safe[:max_len].rstrip("_")
