"""Deploy pipeline orchestrator."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from ..core.dt_client import DynatraceClient
from ..core.types import (
    ALL_CONFIG_TYPES,
    DeployResult,
    ProjectType,
    TenantConfig,
)
from .deploy_monaco import MonacoDeployer
from .deploy_terraform import TerraformDeployer
from .format_detector import FormatDetector
from .results_analyzer import ResultsAnalyzer

logger = logging.getLogger("pipeline")


class DeployOrchestrator:
    """Coordinates the full deploy pipeline.

    Steps:
        1. Acquire configs (local dir or cloned from GitHub)
        2. Auto-detect project type
        3. Verify target tenant connection
        4. Snapshot pre-deploy state
        5. Deploy using appropriate strategy
        6. Analyze results
    """

    def __init__(
        self,
        target_tenant: TenantConfig,
        project_dir: Path,
        config_types: Optional[List[str]] = None,
        dry_run: bool = False,
    ):
        self.target_tenant = target_tenant
        self.project_dir = project_dir
        self.config_types = config_types or ALL_CONFIG_TYPES
        self.dry_run = dry_run
        self.dt_client = DynatraceClient(target_tenant)

        # Populated during execution
        self.project_type: ProjectType = ProjectType.UNKNOWN
        self.deploy_result: Optional[DeployResult] = None
        self.pre_counts: Dict[str, int] = {}

    def run(self) -> DeployResult:
        """Execute the full deploy pipeline."""
        logger.info("=" * 60)
        logger.info("Deploy Pipeline")
        logger.info("=" * 60)
        logger.info(f"Target:  {self.target_tenant.url}")
        logger.info(f"Source:  {self.project_dir}")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info("")

        # Step 1: Detect project type
        detector = FormatDetector()
        self.project_type = detector.detect(self.project_dir)

        if self.project_type == ProjectType.UNKNOWN:
            raise RuntimeError(
                f"Cannot detect project type in {self.project_dir}. "
                "Expected Terraform (.tf/.tf.json) or Monaco (manifest.yaml) files."
            )

        # Step 2: Verify target connection
        if not self.dt_client.verify_connection():
            raise RuntimeError("Cannot connect to target tenant")

        # Step 3: Snapshot pre-deploy state
        logger.info("Capturing pre-deploy state...")
        self.pre_counts = self.dt_client.get_counts(self.config_types)

        # Step 4: Deploy
        if self.project_type == ProjectType.TERRAFORM:
            deployer = TerraformDeployer(
                self.project_dir, self.target_tenant, self.dry_run
            )
        else:
            deployer = MonacoDeployer(
                self.project_dir, self.target_tenant, self.dry_run
            )

        self.deploy_result = deployer.deploy()

        logger.info("")
        logger.info(f"Deploy complete (type={self.project_type.value})")
        return self.deploy_result

    def run_analysis(self) -> str:
        """Step 5: Post-deploy analysis. Returns formatted report."""
        if self.deploy_result is None:
            raise RuntimeError("Must run deploy before analysis")

        analyzer = ResultsAnalyzer(
            self.dt_client, self.deploy_result, self.pre_counts
        )
        return analyzer.analyze(self.config_types)
