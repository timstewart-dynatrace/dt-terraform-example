"""Auto-detect whether a directory contains Monaco, Terraform, or unknown configs."""

import logging
from pathlib import Path

import yaml

from ..core.types import ProjectType

logger = logging.getLogger("pipeline")


class FormatDetector:
    """Detect project type from directory contents."""

    def detect(self, project_dir: Path) -> ProjectType:
        """Examine files to determine if the project is Terraform, Monaco, or unknown.

        Detection rules (checked in order):
            1. .tf or .tf.json files referencing dynatrace -> TERRAFORM
            2. manifest.yaml with Monaco structure -> MONACO
            3. config.yaml files with 'configs:' key -> MONACO
            4. Otherwise -> UNKNOWN
        """
        if self._check_terraform(project_dir):
            logger.info("Detected project type: Terraform")
            return ProjectType.TERRAFORM

        if self._check_monaco(project_dir):
            logger.info("Detected project type: Monaco")
            return ProjectType.MONACO

        logger.warning("Could not detect project type")
        return ProjectType.UNKNOWN

    def _check_terraform(self, project_dir: Path) -> bool:
        """Look for .tf / .tf.json files that reference the Dynatrace provider."""
        tf_files = (
            list(project_dir.glob("**/*.tf"))
            + list(project_dir.glob("**/*.tf.json"))
        )
        if not tf_files:
            return False

        for f in tf_files:
            try:
                content = f.read_text()
                if "dynatrace" in content:
                    return True
            except Exception:
                continue
        return False

    def _check_monaco(self, project_dir: Path) -> bool:
        """Look for Monaco v2 manifest or config.yaml files."""
        # Check for manifest.yaml
        manifest = project_dir / "manifest.yaml"
        if manifest.exists():
            try:
                data = yaml.safe_load(manifest.read_text())
                if isinstance(data, dict) and (
                    "manifestVersion" in data or "projects" in data
                ):
                    return True
            except Exception:
                pass

        # Check for config.yaml with 'configs:' key (Monaco project layout)
        for cfg in project_dir.glob("**/config.yaml"):
            try:
                data = yaml.safe_load(cfg.read_text())
                if isinstance(data, dict) and "configs" in data:
                    return True
            except Exception:
                continue

        return False
