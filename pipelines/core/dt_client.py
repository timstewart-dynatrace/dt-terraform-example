"""Dynatrace API client for configuration export and deployment."""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import requests

from .types import (
    CONFIG_TYPE_API_MAP,
    ALL_CONFIG_TYPES,
    ExportResult,
    ExportFormat,
    TenantConfig,
)

logger = logging.getLogger("pipeline")


class DynatraceClient:
    """Dynatrace REST API client for configuration management."""

    def __init__(self, tenant: TenantConfig, timeout: int = 30):
        self.tenant = tenant
        self.url = tenant.url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Api-Token {tenant.token}"})
        self.session.timeout = timeout

    def verify_connection(self) -> bool:
        """Check that the tenant is reachable and the token is valid."""
        try:
            resp = self.session.get(f"{self.url}/api/v1/config/clusterversion")
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
            resp = self.session.get(f"{self.url}{endpoint}")
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
            resp = self.session.get(
                f"{self.url}{detail_endpoint.format(id=item_id)}"
            )
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
