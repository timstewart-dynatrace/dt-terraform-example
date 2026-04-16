"""Deploy Monaco configurations to a target tenant."""

import logging
import os
import subprocess
from pathlib import Path

import yaml

from ..core.types import DeployResult, ProjectType, TenantConfig

logger = logging.getLogger("pipeline")


class MonacoDeployer:
    """Run monaco deploy against a target tenant."""

    def __init__(
        self,
        project_dir: Path,
        target_tenant: TenantConfig,
        dry_run: bool = False,
    ):
        self.project_dir = project_dir
        self.target = target_tenant
        self.dry_run = dry_run

    def deploy(self) -> DeployResult:
        """Execute Monaco deployment.

        Creates a temporary environments.yaml pointing to the target tenant,
        then runs `monaco deploy`.

        Returns:
            DeployResult with success/failure info.
        """
        result = DeployResult(project_type=ProjectType.MONACO)

        # Ensure manifest.yaml exists
        manifest = self.project_dir / "manifest.yaml"
        if not manifest.exists():
            logger.error(f"No manifest.yaml found in {self.project_dir}")
            result.items_failed["manifest"] = ["manifest.yaml not found"]
            return result

        # Write a temporary environments.yaml for the target
        env_file = self.project_dir / "_deploy_environments.yaml"
        self._write_environments_yaml(env_file)

        try:
            cmd = [
                "monaco", "deploy",
                "--manifest", str(manifest),
                "--environment", "target",
            ]

            if self.dry_run:
                cmd.append("--dry-run")

            logger.info(f"Running: {' '.join(cmd)}")

            env = os.environ.copy()
            env["TARGET_TENANT_URL"] = self.target.url
            env["TARGET_TENANT_TOKEN"] = self.target.token

            proc = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            if proc.stdout:
                for line in proc.stdout.strip().split("\n"):
                    logger.info(f"  {line}")

            if proc.returncode == 0:
                result.items_succeeded["deploy"] = 1
                if self.dry_run:
                    logger.info("[DRY RUN] Monaco deploy completed")
                else:
                    logger.info("Monaco deploy completed successfully")
            else:
                result.items_failed["deploy"] = [proc.stderr or "non-zero exit"]
                if proc.stderr:
                    for line in proc.stderr.strip().split("\n"):
                        logger.error(f"  {line}")
                logger.error("Monaco deploy failed")

        except FileNotFoundError:
            logger.error("Monaco CLI not found")
            result.items_failed["deploy"] = ["monaco command not found"]
        finally:
            # Clean up temp file
            if env_file.exists():
                env_file.unlink()

        return result

    def _write_environments_yaml(self, path: Path) -> None:
        """Write a Monaco environments.yaml for the target tenant."""
        config = {
            "environmentGroups": [
                {
                    "name": "default",
                    "environments": [
                        {
                            "name": "target",
                            "url": {
                                "type": "environment",
                                "value": "TARGET_TENANT_URL",
                            },
                            "auth": {
                                "token": {
                                    "type": "environment",
                                    "name": "TARGET_TENANT_TOKEN",
                                }
                            },
                        }
                    ],
                }
            ]
        }
        path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))
