"""Generate Monaco v2 project structure from raw JSON exports."""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List

import yaml

from ..core.types import MONACO_TYPE_MAP

logger = logging.getLogger("pipeline")


class MonacoFormatter:
    """Convert raw Dynatrace API JSON exports to Monaco v2 project format."""

    def __init__(self, raw_dir: Path, output_dir: Path):
        self.raw_dir = raw_dir
        self.output_dir = output_dir

    def generate(self) -> Path:
        """Generate a complete Monaco v2 project from raw exports.

        Output structure:
            output_dir/
            ├── manifest.yaml
            └── project/
                ├── alerting-profile/
                │   ├── config.yaml
                │   └── item-name.json
                └── dashboard/
                    ├── config.yaml
                    └── item-name.json

        Returns:
            Path to the output directory.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        project_dir = self.output_dir / "project"
        project_dir.mkdir(exist_ok=True)

        config_types_generated: List[str] = []
        total = 0

        for type_dir in sorted(self.raw_dir.iterdir()):
            if not type_dir.is_dir():
                continue
            config_type = type_dir.name
            json_files = sorted(type_dir.glob("*.json"))
            if not json_files:
                continue

            count = self._generate_config_type(project_dir, config_type, json_files)
            if count > 0:
                config_types_generated.append(config_type)
                total += count

        self._generate_manifest(config_types_generated)

        logger.info(f"Monaco output: {total} configs across "
                    f"{len(config_types_generated)} types in {self.output_dir}")
        return self.output_dir

    def _generate_manifest(self, config_types: List[str]) -> None:
        """Create manifest.yaml with project references."""
        manifest = {
            "manifestVersion": "1.0",
            "projects": [
                {
                    "name": "project",
                    "path": "project",
                }
            ],
            "environmentGroups": [
                {
                    "name": "default",
                    "environments": [
                        {
                            "name": "target",
                            "url": {"type": "environment", "value": "TARGET_TENANT_URL"},
                            "auth": {
                                "token": {
                                    "type": "environment",
                                    "name": "TARGET_TENANT_TOKEN",
                                }
                            },
                        }
                    ],
                }
            ],
        }
        path = self.output_dir / "manifest.yaml"
        path.write_text(yaml.dump(manifest, default_flow_style=False, sort_keys=False))

    def _generate_config_type(
        self, project_dir: Path, config_type: str, json_files: List[Path]
    ) -> int:
        """Create config.yaml and JSON payloads for one config type.

        Returns:
            Number of configs generated.
        """
        monaco_type = MONACO_TYPE_MAP.get(config_type, config_type)
        type_dir = project_dir / monaco_type
        type_dir.mkdir(parents=True, exist_ok=True)

        configs: List[Dict] = []
        for json_file in json_files:
            data = json.loads(json_file.read_text())
            item_name = data.get("name", data.get("displayName", json_file.stem))
            safe_name = _sanitize_name(item_name)
            config_id = f"{monaco_type}-{safe_name}"

            # Copy the JSON payload
            dest = type_dir / f"{safe_name}.json"
            dest.write_text(json.dumps(data, indent=2) + "\n")

            configs.append({
                "id": config_id,
                "type": {"api": monaco_type},
                "config": {
                    "name": item_name,
                    "template": f"{safe_name}.json",
                },
            })

        # Write config.yaml for this type
        config_yaml = {"configs": configs}
        (type_dir / "config.yaml").write_text(
            yaml.dump(config_yaml, default_flow_style=False, sort_keys=False)
        )

        return len(configs)


def _sanitize_name(name: str, max_len: int = 64) -> str:
    """Convert a display name to a filesystem-safe identifier."""
    safe = re.sub(r"[^\w\-]", "_", str(name)).lower()
    return safe[:max_len].rstrip("_") or "unnamed"
