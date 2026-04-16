"""Generate Terraform .tf.json files from raw JSON exports."""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List

from ..core.types import TERRAFORM_RESOURCE_MAP

logger = logging.getLogger("pipeline")


class TerraformFormatter:
    """Convert raw Dynatrace API JSON exports to Terraform .tf.json format."""

    def __init__(self, raw_dir: Path, output_dir: Path, target_url: str = ""):
        self.raw_dir = raw_dir
        self.output_dir = output_dir
        self.target_url = target_url

    def generate(self) -> Path:
        """Generate a complete Terraform project from raw exports.

        Returns:
            Path to the output directory containing .tf.json files.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._generate_provider()
        self._generate_variables()

        total = 0
        for type_dir in sorted(self.raw_dir.iterdir()):
            if not type_dir.is_dir():
                continue
            config_type = type_dir.name
            json_files = sorted(type_dir.glob("*.json"))
            if not json_files:
                continue

            count = self._generate_resources(config_type, json_files)
            total += count

        logger.info(f"Terraform output: {total} resources in {self.output_dir}")
        return self.output_dir

    def _generate_provider(self) -> None:
        """Create main.tf.json with provider block."""
        provider = {
            "terraform": {
                "required_version": ">= 1.0",
                "required_providers": {
                    "dynatrace": {
                        "source": "dynatrace-oss/dynatrace",
                        "version": "~> 1.0",
                    }
                },
            },
            "provider": {
                "dynatrace": {
                    "dt_env_url": "${var.dynatrace_env_url}",
                    "dt_api_token": "${var.dynatrace_api_token}",
                }
            },
        }
        self._write_json(self.output_dir / "main.tf.json", provider)

    def _generate_variables(self) -> None:
        """Create variables.tf.json with tenant variable definitions."""
        variables = {
            "variable": {
                "dynatrace_env_url": {
                    "type": "string",
                    "description": "Dynatrace environment URL",
                },
                "dynatrace_api_token": {
                    "type": "string",
                    "description": "Dynatrace API token",
                    "sensitive": True,
                },
            }
        }
        self._write_json(self.output_dir / "variables.tf.json", variables)

    def _generate_resources(self, config_type: str, json_files: List[Path]) -> int:
        """Create a .tf.json file with resource blocks for one config type.

        Returns:
            Number of resources generated.
        """
        tf_resource_type = TERRAFORM_RESOURCE_MAP.get(config_type)
        if not tf_resource_type:
            logger.warning(f"No Terraform resource mapping for: {config_type}")
            return 0

        resources: Dict[str, Dict] = {}
        for json_file in json_files:
            data = json.loads(json_file.read_text())
            resource_name = _sanitize_tf_name(json_file.stem)

            # Store the raw API payload as the resource config.
            # The dynatrace provider accepts JSON-encoded config for many
            # resource types via a "configuration" or similar attribute.
            resources[resource_name] = self._transform_to_resource(
                config_type, tf_resource_type, data
            )

        if not resources:
            return 0

        tf_json = {
            "resource": {
                tf_resource_type: resources,
            }
        }

        safe_type = config_type.replace("-", "_")
        self._write_json(self.output_dir / f"{safe_type}.tf.json", tf_json)
        return len(resources)

    def _transform_to_resource(
        self, config_type: str, tf_type: str, api_data: Dict
    ) -> Dict:
        """Map Dynatrace API response to Terraform resource attributes.

        For dashboard and complex types, the provider accepts the full JSON
        payload via a dedicated attribute. For simpler types, we map known
        fields to provider attributes.
        """
        name = api_data.get("name", api_data.get("displayName", "unnamed"))

        if config_type == "dashboard":
            return {
                "name": name,
                "contents": json.dumps(api_data),
            }

        if config_type == "management-zone":
            return {
                "name": name,
                "description": api_data.get("description", ""),
            }

        if config_type == "alerting-profile":
            return {
                "display_name": api_data.get("displayName", name),
            }

        if config_type == "auto-tag":
            return {
                "name": name,
            }

        # Fallback: store the full API payload as a JSON-encoded attribute.
        # This works with provider resources that accept raw JSON config.
        return {
            "name": name,
            "configuration": json.dumps(api_data),
        }

    @staticmethod
    def _write_json(path: Path, data: Dict) -> None:
        path.write_text(json.dumps(data, indent=2) + "\n")


def _sanitize_tf_name(name: str) -> str:
    """Convert a name to a valid Terraform resource identifier."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
    # Must start with a letter
    if safe and not safe[0].isalpha():
        safe = "r_" + safe
    return safe[:64] or "unnamed"
