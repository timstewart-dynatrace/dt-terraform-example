# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`terraform/iam/` scaffold** — working example for managing Dynatrace **account-level** IAM with Terraform. Includes 2 example groups (`platform-team`, `dashboard-readers`), 3 example policies (`monitoring-read-only`, `dashboard-edit`, `production-admin`), 1 permission boundary (`production-only`, scoping a policy to a single management zone), and `dynatrace_iam_policy_bindings_v2` resources wiring groups to policies with boundary references. Provider pinned to `dynatrace-oss/dynatrace ~> 1.96` (current line as of v1.96.0, published 2026-05-06). Auth model is **distinct from the migration pipelines** — IAM uses OAuth client credentials (`DT_CLIENT_ID` / `DT_CLIENT_SECRET` / `DT_ACCOUNT_ID`) and targets the account API at `api.dynatrace.com`; the pipelines use tenant tokens against `<tenant>.live.dynatrace.com`. `terraform/iam/README.md` documents OAuth client setup, required scopes per resource type, the deprecated args this scaffold avoids (`dynatrace_iam_group.permissions`, `dynatrace_iam_policy.environment`), and a "verify against the current provider release before apply" check.
- `.claude/DECISIONS.md` entry — *2026-05-18 — Two auth models coexist (tenant tokens for migration, OAuth client for IAM)* — documents why account-level OAuth and tenant-token auth live in the same repo.

### Changed
- `.claude/settings.json` version bumped from `0.2.0` to `0.4.0`. The 0.2.0 → 0.3.0 bump documented in this changelog never landed in `settings.json`; this catches the file up and accounts for the new IAM scaffold (MINOR — new feature).
- Root `.gitignore` no longer excludes `.terraform.lock.hcl` — the lockfile is now committed per HashiCorp's reproducible-provider-install recommendation, applied to `terraform/iam/.terraform.lock.hcl`. `*.tfstate*` and `.terraform/` continue to be excluded.

### Documentation
- `terraform/iam/README.md` — OAuth setup section refined: explicit note that the IAM Account Management API requires an **OAuth2 bearer token** (raw API tokens and Platform Tokens will not work) and that the provider performs the credential-to-bearer-token exchange automatically. Scope descriptions reworded for clarity (action-oriented: *"Create/delete groups"* instead of *"Creating/updating/deleting groups"*). `account-env-read` retained with an explicit note that the provider requires it for policy/boundary/bindings resources even when account-scoped. OAuth client creation steps restructured to match the Account Management UI flow exactly.

### Fixed
- `terraform/iam/policies.tf` — replaced unsupported permission DSL tokens that caused HTTP 400 at apply time. Dropped `entities:read`, `davis-problems:read`, and `document:documents:read/write/delete` from the example policies; the Dynatrace IAM permission catalog does not include them. `monitoring-read-only` now grants `settings:objects:read, settings:schemas:read` only (the two tokens verified in the dynatrace-oss provider's integration tests). `dashboard-edit` repurposed as a settings-schema-scoped edit policy with `WHERE settings:schemaId = "builtin:management-zones"` as a verified-existing placeholder — operators should swap to whichever schema they actually want to grant edit access to. `production-admin` continues to use `settings:objects:read/write/delete` (the `:write` and `:delete` tokens are inferred from the `:read` pattern; if Dynatrace rejects them, drop to read-only and consult the IAM permissions catalog). `terraform/iam/README.md` adds a new "Permission DSL tokens are validated at apply, not at plan" caveat explaining the failure mode and how to diagnose it via `TF_LOG=DEBUG`.

## [0.3.0] - 2026-05-12

### Added
- **Reference Currency directive** at `.claude/rules/reference-currency.md` — documented discipline for keeping cited URLs and quoted statements current. Two directives: (1) **next-touch reference standardization** — when editing any file with cited URLs, use the `[Title (publisher)](URL)` minimal format, cite source pages not docs-assistant summaries, no marketing taglines, no internal-rule links from user-facing docs, wrap direct quotes in italic single quotes; (2) **deep content verification** — URL liveness check via `scripts/validate_citation_urls.py` (monthly + on every PR touching citations + after major Dynatrace provider releases); manual content-drift spot-check for the load-bearing v1.88.0 release-note quote in `dt_client.py`. Adapted from the Best-Practice-Notebooks-Generator project's `workflow.md` § Reference Currency directive — sized for this smaller codebase. Wired into `.claude/CLAUDE.md` Always-active rules.
- **`scripts/validate_citation_urls.py`** — walks all `.md` files + Python source under `pipelines/`, `tests/`, `scripts/`, extracts every `https://...` URL, filters placeholders (variable substitutions, example domains, all-caps placeholders), concurrent HEAD-checks each unique URL, writes a per-source report to `docs/citation-status.md`. Exit code 0 if no 404s, 1 if any (suitable for CI gating once baseline is clean). Initial baseline: **0 404s, 25 of 26 URLs live, 1 known false-positive** (Lithium-platform `community.dynatrace.com` 403 on HEAD — works in browser; same false-positive as the Notebooks-Generator project).
- **`docs/citation-status.md`** — committed baseline produced by the validator.
- **pytest test suite** (94 tests) locking down the Phase 02 combined-auth logic. Covers `_header_for_token` (Bearer / Api-Token / unknown-prefix fallback), `_needs_classic_api_token` (10 positive cases from the v1.88.0 exclusion list + 14 negative cases including Settings 2.0 and other Platform-eligible endpoints), `DynatraceClient._auth_header_for_url` (backward-compat classic-only, Platform-only on non-excluded works, Platform-only on excluded raises `MissingClassicTokenError` with clear remediation, combined-auth routes correctly per URL), `TenantConfig` construction, and `PipelineConfig.get_source_tenant` / `get_target_tenant` env-and-yaml loading including the new `*_TENANT_API_TOKEN` slot. End-to-end HTTP tests using the `responses` library verify the right `Authorization` header reaches the wire for `verify_connection`, `list_items`, and `get_item`.
- `requirements-dev.txt` with `pytest`, `pytest-cov`, `responses`.
- `pyproject.toml` configuring pytest and coverage (`testpaths`, coverage source, exclude lines for `TYPE_CHECKING` etc).
- `tests/conftest.py` with reusable tenant + client fixtures and an `autouse` env-clean fixture so tests are deterministic regardless of the developer's local env.
- `.github/workflows/test.yml` — runs pytest on PR and push to main; matrix across Python 3.9 / 3.11 / 3.12; uploads coverage XML on the 3.12 leg.
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
