"""Export pipeline orchestrator."""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..core.dt_client import DynatraceClient
from ..core.types import (
    ALL_CONFIG_TYPES,
    ExportFormat,
    ExportResult,
    ReconciliationReport,
    TenantConfig,
    TopologyReport,
)
from .format_monaco import MonacoFormatter
from .format_terraform import TerraformFormatter
from .reconciliation import ReconciliationChecker
from .topology import TopologyAnalyzer

logger = logging.getLogger("pipeline")


class ExportOrchestrator:
    """Coordinates the full export pipeline.

    Steps:
        1. Verify source tenant connection
        2. Export raw JSON from tenant API
        3. Transform to target format (Monaco or Terraform)
        4. Reconciliation (optional)
        5. Topology analysis (optional)
    """

    def __init__(
        self,
        source_tenant: TenantConfig,
        config_types: List[str],
        export_format: ExportFormat,
        output_dir: Optional[str] = None,
    ):
        self.source_tenant = source_tenant
        self.config_types = config_types or ALL_CONFIG_TYPES
        self.export_format = export_format
        self.output_dir = Path(
            output_dir or f"export_{datetime.now():%Y%m%d_%H%M%S}"
        )
        self.dt_client = DynatraceClient(source_tenant)

        # Populated during execution
        self.export_result: Optional[ExportResult] = None
        self.reconciliation_report: Optional[ReconciliationReport] = None
        self.topology_report: Optional[TopologyReport] = None

    def run_export(self) -> ExportResult:
        """Execute steps 1-3: connect, export raw, transform."""
        logger.info("=" * 60)
        logger.info("Export Pipeline")
        logger.info("=" * 60)
        logger.info(f"Source: {self.source_tenant.url}")
        logger.info(f"Format: {self.export_format.value}")
        logger.info(f"Types:  {', '.join(self.config_types)}")
        logger.info(f"Output: {self.output_dir}")
        logger.info("")

        # Step 1: Verify connection
        if not self.dt_client.verify_connection():
            raise RuntimeError("Cannot connect to source tenant")

        # Step 2: Export raw JSON
        raw_dir = self.output_dir / "raw"
        logger.info("Exporting configurations from tenant...")
        self.export_result = self.dt_client.export_all(self.config_types, raw_dir)

        if self.export_result.total_count == 0:
            logger.warning("No configurations exported (tenant may be empty)")

        # Step 3: Transform to target format
        logger.info(f"Transforming to {self.export_format.value} format...")
        if self.export_format == ExportFormat.TERRAFORM:
            formatter = TerraformFormatter(
                raw_dir,
                self.output_dir / "terraform",
                target_url=self.source_tenant.url,
            )
        else:
            formatter = MonacoFormatter(raw_dir, self.output_dir / "monaco")

        formatter.generate()

        logger.info("")
        logger.info(f"Export complete: {self.export_result.total_count} items")
        return self.export_result

    def run_reconciliation(self) -> ReconciliationReport:
        """Step 4: Compare export against tenant state."""
        if self.export_result is None:
            raise RuntimeError("Must run export before reconciliation")

        logger.info("")
        logger.info("Running reconciliation...")
        checker = ReconciliationChecker(self.dt_client, self.export_result)
        self.reconciliation_report = checker.check()
        return self.reconciliation_report

    def run_topology(self) -> TopologyReport:
        """Step 5: Analyze entity relationships."""
        if self.export_result is None:
            raise RuntimeError("Must run export before topology analysis")

        logger.info("")
        logger.info("Running topology analysis...")
        raw_dir = self.output_dir / "raw"
        analyzer = TopologyAnalyzer(raw_dir, self.config_types)
        self.topology_report = analyzer.analyze()
        return self.topology_report
