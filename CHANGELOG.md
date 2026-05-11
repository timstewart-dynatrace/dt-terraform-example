# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Combined auth (Platform Token + classic API Token)** in `pipelines/core/dt_client.py`. The primary `*_TENANT_TOKEN` may now be a Platform Token (`dt0s16` / `dt0s01`, sent as `Authorization: Bearer`) or a classic Access Token (`dt0c01`, sent as `Authorization: Api-Token`) — auto-detected by prefix. New optional `*_TENANT_API_TOKEN` slot accepts a classic Access Token used only for endpoints that the Dynatrace Terraform provider removed from Platform-Token coverage in [v1.88.0](https://github.com/dynatrace-oss/terraform-provider-dynatrace/releases/tag/v1.88.0): synthetic monitors / locations, network monitors, AG/API tokens, credential vault, custom devices, custom tags, host monitoring mode, key requests, hub extension active version + config, SLO v1/v2. Per-request URL-pattern routing in `_auth_header_for_url` picks the right header per call.
- `MissingClassicTokenError` raised with a clear remediation message when an excluded-endpoint request lacks a classic API Token, instead of returning a silent 401.
- `TenantConfig.api_token` field (optional).

### Changed
- `requirements.txt` bumped to current pinned versions (May 2026): `requests` 2.31.0 → 2.32.5, `pyyaml` 6.0.1 → 6.0.3, `python-dotenv` 1.0.0 → 1.2.1; `tabulate` unchanged at 0.9.0.
- `config/.env.example` documents the optional `*_TENANT_API_TOKEN` slot alongside `*_TENANT_TOKEN`, and the primary-token example switched to `dt0s16` (Platform Token) to reflect Dynatrace's current default for new tenants.
- README "Getting API Tokens" section rewritten to explain combined auth, the v1.88.0 boundary, and which scopes each token type carries.
- `.claude/CLAUDE.md` skill-include paths corrected (`VisualCode-AI-Template` → `Claude-AI-Template`) — the shared skills repo was renamed.

### Backward compatibility
- Existing configurations that set only `*_TENANT_TOKEN=dt0c01...` continue to work identically — the primary token is classic-shaped and is reused as the API Token for the excluded endpoints via the fall-back path. No call-site changes required.

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
