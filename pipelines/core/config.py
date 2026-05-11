"""Pipeline configuration loader.

Loads settings from config/pipeline.yaml with ${ENV_VAR} interpolation,
falling back to environment variables and CLI defaults.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .types import ExportFormat, GitHubTarget, TenantConfig


def _interpolate_env(value: Any) -> Any:
    """Replace ${VAR} placeholders with environment variable values."""
    if not isinstance(value, str):
        return value
    return re.sub(
        r"\$\{(\w+)\}",
        lambda m: os.environ.get(m.group(1), m.group(0)),
        value,
    )


def _interpolate_dict(d: Dict) -> Dict:
    """Recursively interpolate env vars in a dict."""
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = _interpolate_dict(v)
        elif isinstance(v, list):
            out[k] = [_interpolate_env(i) for i in v]
        else:
            out[k] = _interpolate_env(v)
    return out


class PipelineConfig:
    """Load and merge config from pipeline.yaml and environment."""

    def __init__(self, data: Dict):
        self._data = data

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "PipelineConfig":
        """Load config from YAML file, with env var interpolation.

        Falls back to an empty config if the file doesn't exist.
        """
        path = Path(config_path or os.environ.get(
            "PIPELINE_CONFIG", "config/pipeline.yaml"
        ))
        if path.exists():
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
            data = _interpolate_dict(raw)
        else:
            data = {}
        return cls(data)

    # -- Source / Target tenants --

    def get_source_tenant(self) -> TenantConfig:
        export_cfg = self._data.get("export", {})
        api_token = (export_cfg.get("source_tenant_api_token")
                     or os.environ.get("SOURCE_TENANT_API_TOKEN") or None)
        return TenantConfig(
            url=(export_cfg.get("source_tenant_url")
                 or os.environ.get("SOURCE_TENANT_URL", "")),
            token=(export_cfg.get("source_tenant_token")
                   or os.environ.get("SOURCE_TENANT_TOKEN", "")),
            api_token=api_token,
        )

    def get_target_tenant(self) -> TenantConfig:
        deploy_cfg = self._data.get("deploy", {})
        api_token = (deploy_cfg.get("target_tenant_api_token")
                     or os.environ.get("TARGET_TENANT_API_TOKEN") or None)
        return TenantConfig(
            url=(deploy_cfg.get("target_tenant_url")
                 or os.environ.get("TARGET_TENANT_URL", "")),
            token=(deploy_cfg.get("target_tenant_token")
                   or os.environ.get("TARGET_TENANT_TOKEN", "")),
            api_token=api_token,
        )

    # -- GitHub --

    def get_github_target(self) -> GitHubTarget:
        gh = self._data.get("export", {}).get("github", {})
        return GitHubTarget(
            repo=gh.get("repo", os.environ.get("GITHUB_REPO", "")),
            branch=gh.get("branch", os.environ.get("GITHUB_BRANCH", "main")),
            path=gh.get("path", os.environ.get("GITHUB_PATH", "exported")),
        )

    # -- Defaults --

    def get_default_format(self) -> ExportFormat:
        fmt = self._data.get("export", {}).get("default_format", "terraform")
        try:
            return ExportFormat(fmt)
        except ValueError:
            return ExportFormat.TERRAFORM

    def get_default_export_types(self) -> list:
        return self._data.get("export", {}).get("default_types", [])

    def get_default_deploy_types(self) -> list:
        return self._data.get("deploy", {}).get("default_types", [])

    def get_auto_approve(self) -> bool:
        return self._data.get("deploy", {}).get("auto_approve", False)
