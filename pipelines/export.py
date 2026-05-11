#!/usr/bin/env python3
"""Export pipeline CLI entry point.

Can run interactively (no args) or fully flag-driven for CI/GitHub Actions.

Examples:
    # Interactive
    python -m pipelines.export

    # Flag-driven (for GitHub Actions)
    python -m pipelines.export \
        --source-url https://tenant.live.dynatrace.com \
        --source-token TOKEN \
        --types all \
        --format terraform \
        --reconcile \
        --topology
"""

import argparse
import os
import sys
from pathlib import Path

# Allow running as `python pipelines/export.py` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from pipelines.core.config import PipelineConfig
from pipelines.core.logging_setup import setup_logging
from pipelines.core.types import ALL_CONFIG_TYPES, ExportFormat, TenantConfig
from pipelines.export_pipeline.exporter import ExportOrchestrator
from pipelines.export_pipeline.reconciliation import ReconciliationChecker
from pipelines.export_pipeline.topology import TopologyAnalyzer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Dynatrace configuration to Terraform or Monaco format"
    )
    parser.add_argument("--source-url", help="Source Dynatrace tenant URL")
    parser.add_argument("--source-token", help="Source tenant API token")
    parser.add_argument(
        "--types",
        default="",
        help="Comma-separated config types, or 'all' (default: all)",
    )
    parser.add_argument(
        "--format",
        choices=["terraform", "monaco"],
        help="Export format (default: from pipeline.yaml or terraform)",
    )
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Run reconciliation after export",
    )
    parser.add_argument(
        "--topology",
        action="store_true",
        help="Run topology analysis after export",
    )
    parser.add_argument("--config", help="Path to pipeline.yaml")
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="List available config types and exit",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    if args.list_types:
        print("\nAvailable configuration types:\n")
        for ct in ALL_CONFIG_TYPES:
            print(f"  {ct}")
        print()
        return 0

    logger = setup_logging("export")

    # Load config
    cfg = PipelineConfig.load(args.config)

    # Resolve source tenant
    cfg_source = cfg.get_source_tenant()
    source = TenantConfig(
        url=args.source_url or cfg_source.url,
        token=args.source_token or cfg_source.token,
        api_token=getattr(args, "source_api_token", None) or cfg_source.api_token,
    )
    if not source.url or not source.token:
        logger.error(
            "Source tenant URL and token required. "
            "Set via --source-url/--source-token, pipeline.yaml, or .env"
        )
        return 1

    # Resolve config types
    types_str = args.types or ""
    if types_str.lower() in ("all", ""):
        config_types = cfg.get_default_export_types() or ALL_CONFIG_TYPES
    else:
        config_types = [t.strip() for t in types_str.split(",") if t.strip()]

    # Resolve format
    if args.format:
        export_format = ExportFormat(args.format)
    else:
        export_format = cfg.get_default_format()

    # Run export
    orchestrator = ExportOrchestrator(
        source_tenant=source,
        config_types=config_types,
        export_format=export_format,
        output_dir=args.output_dir,
    )

    try:
        orchestrator.run_export()
    except RuntimeError as e:
        logger.error(f"Export failed: {e}")
        return 1

    # Optional post-export steps
    if args.reconcile:
        report = orchestrator.run_reconciliation()
        print("\n" + ReconciliationChecker.format_report(report))

    if args.topology:
        report = orchestrator.run_topology()
        print("\n" + TopologyAnalyzer.format_report(report))

    # Write summary to GITHUB_STEP_SUMMARY if running in Actions
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(f"## Export Summary\n\n")
            f.write(f"- **Format:** {export_format.value}\n")
            f.write(f"- **Types:** {', '.join(config_types)}\n")
            result = orchestrator.export_result
            if result:
                f.write(f"- **Total items:** {result.total_count}\n")
                for ct, count in sorted(result.items_exported.items()):
                    if count > 0:
                        f.write(f"  - {ct}: {count}\n")

            if orchestrator.reconciliation_report:
                f.write("\n")
                f.write(ReconciliationChecker.format_report(
                    orchestrator.reconciliation_report
                ))

            if orchestrator.topology_report:
                f.write("\n")
                f.write(TopologyAnalyzer.format_report(
                    orchestrator.topology_report
                ))

    return 0


if __name__ == "__main__":
    sys.exit(main())
