"""Post-deploy analysis: compare target tenant state before and after deploy."""

import logging
from typing import Dict, List, Optional

from tabulate import tabulate

from ..core.dt_client import DynatraceClient
from ..core.types import DeployResult

logger = logging.getLogger("pipeline")


class ResultsAnalyzer:
    """Analyze deploy results and target tenant post-deploy state."""

    def __init__(
        self,
        dt_client: DynatraceClient,
        deploy_result: DeployResult,
        pre_counts: Optional[Dict[str, int]] = None,
    ):
        self.client = dt_client
        self.result = deploy_result
        self.pre_counts = pre_counts or {}

    def analyze(self, config_types: List[str]) -> str:
        """Query target tenant and produce a post-deploy summary.

        Returns:
            Formatted markdown report string.
        """
        logger.info("Analyzing deploy results...")

        post_counts = self.client.get_counts(config_types)

        rows = []
        for ct in sorted(config_types):
            pre = self.pre_counts.get(ct, "?")
            post = post_counts.get(ct, 0)
            delta = post - pre if isinstance(pre, int) else "?"
            rows.append([ct, pre, post, delta])

        lines = [
            "## Deploy Results",
            "",
            f"- **Project type:** {self.result.project_type.value}",
            f"- **Succeeded:** {sum(self.result.items_succeeded.values())}",
            f"- **Failed:** {sum(len(v) for v in self.result.items_failed.values())}",
            "",
        ]

        if rows:
            header = ["Config Type", "Before", "After", "Delta"]
            lines.append(tabulate(rows, headers=header, tablefmt="github"))
            lines.append("")

        if self.result.items_failed:
            lines.append("### Failures")
            for key, errors in self.result.items_failed.items():
                for err in errors:
                    lines.append(f"- **{key}**: {err}")

        return "\n".join(lines)
