"""Deploy Terraform configurations to a target tenant."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from ..core.types import DeployResult, ProjectType, TenantConfig

logger = logging.getLogger("pipeline")


class TerraformDeployer:
    """Run terraform init/plan/apply against a target tenant."""

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
        """Execute the Terraform deployment sequence.

        Returns:
            DeployResult with success/failure counts.
        """
        result = DeployResult(project_type=ProjectType.TERRAFORM)

        env = self._build_env()

        # terraform init
        logger.info("Running terraform init...")
        if not self._run_terraform(["init", "-input=false"], env):
            logger.error("terraform init failed")
            return result

        # terraform plan
        logger.info("Running terraform plan...")
        plan_ok = self._run_terraform(["plan", "-out=tfplan", "-input=false"], env)
        if not plan_ok:
            logger.error("terraform plan failed")
            return result

        if self.dry_run:
            logger.info("[DRY RUN] terraform plan complete — skipping apply")
            result.items_succeeded["plan"] = 1
            return result

        # terraform apply
        logger.info("Running terraform apply...")
        if self._run_terraform(["apply", "-auto-approve", "tfplan"], env):
            result.items_succeeded["apply"] = 1
            logger.info("terraform apply completed successfully")
        else:
            result.items_failed["apply"] = ["terraform apply returned non-zero"]
            logger.error("terraform apply failed")

        return result

    def _build_env(self) -> dict:
        """Build environment variables for Terraform subprocess."""
        env = os.environ.copy()
        env["DYNATRACE_ENV_URL"] = self.target.url
        env["DYNATRACE_API_TOKEN"] = self.target.token
        # Also set TF_VAR_ versions for variable-based auth
        env["TF_VAR_dynatrace_env_url"] = self.target.url
        env["TF_VAR_dynatrace_api_token"] = self.target.token
        return env

    def _run_terraform(self, args: list, env: dict) -> bool:
        """Run a terraform command and log output."""
        cmd = ["terraform"] + args
        try:
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
            if proc.returncode != 0 and proc.stderr:
                for line in proc.stderr.strip().split("\n"):
                    logger.error(f"  {line}")
            return proc.returncode == 0
        except FileNotFoundError:
            logger.error("Terraform CLI not found")
            return False
