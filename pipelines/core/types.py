"""Shared data classes and enums for the pipeline system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ExportFormat(Enum):
    MONACO = "monaco"
    TERRAFORM = "terraform"


class ProjectType(Enum):
    MONACO = "monaco"
    TERRAFORM = "terraform"
    UNKNOWN = "unknown"


# Config type -> (list endpoint, list_key, detail endpoint or None)
# detail_endpoint uses {id} placeholder
CONFIG_TYPE_API_MAP: Dict[str, Tuple[str, str, Optional[str]]] = {
    "alerting-profile": (
        "/api/config/v1/alertingProfiles",
        "values",
        "/api/config/v1/alertingProfiles/{id}",
    ),
    "auto-tag": (
        "/api/config/v1/autoTags",
        "values",
        "/api/config/v1/autoTags/{id}",
    ),
    "dashboard": (
        "/api/config/v1/dashboards",
        "dashboards",
        "/api/config/v1/dashboards/{id}",
    ),
    "management-zone": (
        "/api/config/v1/managementZones",
        "values",
        "/api/config/v1/managementZones/{id}",
    ),
    "notification": (
        "/api/config/v1/notifications",
        "values",
        "/api/config/v1/notifications/{id}",
    ),
    "request-naming": (
        "/api/config/v1/service/requestNaming",
        "values",
        "/api/config/v1/service/requestNaming/{id}",
    ),
    "extension": (
        "/api/config/v1/extensions",
        "extensions",
        "/api/config/v1/extensions/{id}",
    ),
    "synthetic-monitor": (
        "/api/v1/synthetic/monitors",
        "monitors",
        "/api/v1/synthetic/monitors/{id}",
    ),
    "synthetic-location": (
        "/api/v1/synthetic/locations",
        "locations",
        None,  # Full data returned in list
    ),
}

ALL_CONFIG_TYPES = sorted(CONFIG_TYPE_API_MAP.keys())

# Config type -> Terraform resource type (dynatrace-oss/dynatrace provider)
TERRAFORM_RESOURCE_MAP: Dict[str, str] = {
    "alerting-profile": "dynatrace_alerting",
    "auto-tag": "dynatrace_autotag_v2",
    "dashboard": "dynatrace_json_dashboard",
    "management-zone": "dynatrace_management_zone_v2",
    "notification": "dynatrace_notification",
    "request-naming": "dynatrace_request_naming",
    "extension": "dynatrace_extension",
    "synthetic-monitor": "dynatrace_http_monitor",
    "synthetic-location": "dynatrace_synthetic_location",
}

# Config type -> Monaco API type identifier
MONACO_TYPE_MAP: Dict[str, str] = {
    "alerting-profile": "alerting-profile",
    "auto-tag": "auto-tag",
    "dashboard": "dashboard",
    "management-zone": "management-zone",
    "notification": "notification",
    "request-naming": "request-naming",
    "extension": "extension",
    "synthetic-monitor": "synthetic-monitor",
    "synthetic-location": "synthetic-location",
}


@dataclass
class TenantConfig:
    """Tenant connection settings.

    Two token slots are supported:

    - ``token`` is the primary credential. It may be a **Platform Token**
      (``dt0s16``/``dt0s01`` prefix — sent as ``Authorization: Bearer``) or a
      **classic Access Token** (``dt0c01`` prefix — sent as
      ``Authorization: Api-Token``). The header format is auto-detected by
      prefix in :class:`DynatraceClient`.

    - ``api_token`` is an optional secondary credential, only used when the
      primary token is a Platform Token *and* a particular request targets an
      endpoint that Dynatrace removed from Platform-Token coverage in
      Terraform provider v1.88.0 (synthetic monitors, network monitors,
      AG/API tokens, credentials, custom devices, custom tags, host
      monitoring mode, key requests, hub extension active version + config,
      SLO v1/v2). These endpoints require a classic API Token even when
      everything else in the same tenant works with the Platform Token.

    Backward compatibility: a config that sets only ``token`` (regardless of
    prefix) continues to work — Platform-Token-prefixed tokens get Bearer
    headers, classic-API-Token-prefixed tokens get Api-Token headers, and
    requests to the v1.88.0 exclusion list fall back to the primary token if
    it is classic-API-shaped.
    """

    url: str
    token: str
    api_token: Optional[str] = None


@dataclass
class GitHubTarget:
    repo: str       # "owner/repo"
    branch: str
    path: str       # subdirectory within repo


@dataclass
class ExportResult:
    format: ExportFormat
    output_dir: str
    config_types: List[str]
    items_exported: Dict[str, int] = field(default_factory=dict)
    items_failed: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def total_count(self) -> int:
        return sum(self.items_exported.values())


@dataclass
class ReconciliationReport:
    tenant_counts: Dict[str, int] = field(default_factory=dict)
    exported_counts: Dict[str, int] = field(default_factory=dict)
    missing: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def has_issues(self) -> bool:
        return any(len(v) > 0 for v in self.missing.values())


@dataclass
class TopologyNode:
    config_type: str
    item_id: str
    item_name: str
    references: List[str] = field(default_factory=list)


@dataclass
class TopologyReport:
    nodes: List[TopologyNode] = field(default_factory=list)
    edges: List[Tuple[str, str, str]] = field(default_factory=list)
    layers: Dict[int, List[str]] = field(default_factory=dict)
    cycles: List[List[str]] = field(default_factory=list)


@dataclass
class DeployResult:
    project_type: ProjectType
    config_types_deployed: List[str] = field(default_factory=list)
    items_succeeded: Dict[str, int] = field(default_factory=dict)
    items_failed: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def total_count(self) -> int:
        return sum(self.items_succeeded.values())
