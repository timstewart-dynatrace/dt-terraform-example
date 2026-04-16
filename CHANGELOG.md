# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-04-16

### Added
- Export pipeline (`pipelines/export.py`) with Terraform and Monaco format generators
- Deploy pipeline (`pipelines/deploy.py`) with auto-format detection
- GitHub Actions workflows for export (`export.yml`) and deploy (`deploy.yml`) with `workflow_dispatch` inputs
- Post-export reconciliation: compare exported items against tenant state
- Post-export topology analysis: map entity cross-references and compute deployment order
- Post-deploy results analysis: compare before/after tenant counts
- Pipeline configuration template (`config/pipeline.yaml.example`) with `${ENV_VAR}` interpolation
- Shared Dynatrace API client (`pipelines/core/dt_client.py`)
- Format auto-detection for deploy pipeline (Terraform vs Monaco)
- `tabulate` dependency for formatted report output

## [0.1.0] - 2026-04-16

### Added
- Python migration script (`scripts/migrate.py`) with CLI args, .env loading, dry-run, selective config types, and `--list-types`
- Shell migration script (`scripts/migrate.sh`) with colored output, `--dry-run`, `--no-backup`, `--config-types`, and `--list-types`
- Clone configuration helper (`scripts/clone-config.sh`) for timestamped downloads
- Post-migration verification script (`scripts/verify_migration.py`)
- Interactive setup wizard (`setup.sh`) for dependency checks and .env creation
- Environment configuration template (`config/.env.example`, `config/environments.yaml`)
- Documentation: Getting Started, Advanced Usage, and Troubleshooting guides
- `.claude/` directory with AI assistant instructions following best practices
- `DECISIONS.md` for architectural decision tracking
- `CHANGELOG.md` following Keep a Changelog format
- References to `dynatrace-terraform` and `dynatrace-apis` skills from SKILLS library
