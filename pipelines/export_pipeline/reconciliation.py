"""Post-export reconciliation: compare exported items against tenant state."""

import logging
from typing import Dict, List, Optional

from tabulate import tabulate

from ..core.dt_client import DynatraceClient
from ..core.types import ExportResult, ReconciliationReport

logger = logging.getLogger("pipeline")


class ReconciliationChecker:
    """Compare what was exported against what the tenant API reports."""

    def __init__(self, dt_client: DynatraceClient, export_result: ExportResult):
        self.client = dt_client
        self.export = export_result

    def check(self) -> ReconciliationReport:
        """Query tenant for counts, compare against export counts."""
        report = ReconciliationReport()

        tenant_counts = self.client.get_counts(self.export.config_types)
        report.tenant_counts = tenant_counts
        report.exported_counts = dict(self.export.items_exported)

        for config_type in self.export.config_types:
            tenant_n = tenant_counts.get(config_type, 0)
            exported_n = self.export.items_exported.get(config_type, 0)

            if tenant_n > exported_n:
                # Identify missing items
                tenant_items = self.client.list_items(config_type)
                tenant_ids = {
                    i.get("id", i.get("entityId", ""))
                    for i in tenant_items
                }
                failed_ids = set(self.export.items_failed.get(config_type, []))
                missing = list(tenant_ids & failed_ids) if failed_ids else []
                if tenant_n - exported_n > len(missing):
                    missing.append(f"...and {tenant_n - exported_n - len(missing)} more")
                report.missing[config_type] = missing

        return report

    @staticmethod
    def format_report(report: ReconciliationReport) -> str:
        """Format reconciliation report as a markdown-compatible table."""
        rows = []
        for ct in sorted(
            set(list(report.tenant_counts.keys()) + list(report.exported_counts.keys()))
        ):
            tenant_n = report.tenant_counts.get(ct, 0)
            exported_n = report.exported_counts.get(ct, 0)
            missing_n = tenant_n - exported_n
            status = "OK" if missing_n == 0 else "WARN"
            rows.append([ct, tenant_n, exported_n, missing_n, status])

        # Totals
        total_tenant = sum(r[1] for r in rows)
        total_exported = sum(r[2] for r in rows)
        total_missing = sum(r[3] for r in rows)
        rows.append(["**TOTAL**", total_tenant, total_exported, total_missing, ""])

        header = ["Config Type", "Tenant", "Exported", "Missing", "Status"]
        table = tabulate(rows, headers=header, tablefmt="github")

        lines = ["## Reconciliation Report", "", table]

        # List missing items if any
        if report.has_issues:
            lines.append("")
            lines.append("### Missing Items")
            for ct, items in sorted(report.missing.items()):
                if items:
                    lines.append(f"- **{ct}**: {', '.join(items)}")

        return "\n".join(lines)
