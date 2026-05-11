#!/usr/bin/env python3
"""Deploy pipeline CLI entry point.

Can run interactively (no args) or fully flag-driven for CI/GitHub Actions.

Examples:
    # Flag-driven (for GitHub Actions)
    python -m pipelines.deploy \
        --source-dir ./exported/terraform \
        --target-url https://target.live.dynatrace.com \
        --target-token TOKEN \
        --dry-run

    # With analysis
    python -m pipelines.deploy \
        --source-dir ./exported/terraform \
        --target-url https://target.live.dynatrace.com \
        --target-token TOKEN \
        --analyze
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from pipelines.core.config import PipelineConfig
from pipelines.core.logging_setup import setup_logging
from pipelines.core.types import ALL_CONFIG_TYPES, TenantConfig
from pipelines.deploy_pipeline.deployer import DeployOrchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy Dynatrace configuration from Terraform or Monaco project"
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Directory containing Terraform or Monaco configs",
    )
    parser.add_argument("--target-url", help="Target Dynatrace tenant URL")
    parser.add_argument("--target-token", help="Target tenant API token")
    parser.add_argument(
        "--types",
        default="",
        help="Comma-separated config types, or 'all' (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run plan only, do not apply",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run post-deploy analysis",
    )
    parser.add_argument("--config", help="Path to pipeline.yaml")
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()
    logger = setup_logging("deploy")

    # Load config
    cfg = PipelineConfig.load(args.config)

    # Resolve target tenant
    cfg_target = cfg.get_target_tenant()
    target = TenantConfig(
        url=args.target_url or cfg_target.url,
        token=args.target_token or cfg_target.token,
        api_token=getattr(args, "target_api_token", None) or cfg_target.api_token,
    )
    if not target.url or not target.token:
        logger.error(
            "Target tenant URL and token required. "
            "Set via --target-url/--target-token, pipeline.yaml, or .env"
        )
        return 1

    # Resolve config types
    types_str = args.types or ""
    if types_str.lower() in ("all", ""):
        config_types = cfg.get_default_deploy_types() or ALL_CONFIG_TYPES
    else:
        config_types = [t.strip() for t in types_str.split(",") if t.strip()]

    # Validate source dir
    source_dir = Path(args.source_dir)
    if not source_dir.is_dir():
        logger.error(f"Source directory does not exist: {source_dir}")
        return 1

    # Run deploy
    orchestrator = DeployOrchestrator(
        target_tenant=target,
        project_dir=source_dir,
        config_types=config_types,
        dry_run=args.dry_run,
    )

    try:
        orchestrator.run()
    except RuntimeError as e:
        logger.error(f"Deploy failed: {e}")
        return 1

    # Optional analysis
    report = ""
    if args.analyze:
        report = orchestrator.run_analysis()
        print("\n" + report)

    # Write to GITHUB_STEP_SUMMARY if running in Actions
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(f"## Deploy Summary\n\n")
            f.write(f"- **Project type:** {orchestrator.project_type.value}\n")
            f.write(f"- **Dry run:** {args.dry_run}\n")
            result = orchestrator.deploy_result
            if result:
                f.write(f"- **Succeeded:** {sum(result.items_succeeded.values())}\n")
                f.write(f"- **Failed:** {sum(len(v) for v in result.items_failed.values())}\n")
            if report:
                f.write("\n" + report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
