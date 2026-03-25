# AGENTS

## Purpose
This repository provides a working Dynatrace Terraform migration example with Python and Shell automation for cloning and migrating configuration between tenants.

## What Was Completed
1. Initialized project structure and documentation.
2. Added migration tooling in Python and Shell.
3. Added helper tooling for clone and verification flows.
4. Added setup automation and safety defaults.
5. Added docs for quickstart, advanced usage, and troubleshooting.
6. Added list-types support to both migration scripts.
7. Created and published the repository to GitHub.

## Repository Snapshot
- Repository: https://github.com/timstewart-dynatrace/dt-terraform-example
- Default branch: main
- Initial commit: c005346
- Commit message: Initial commit: Dynatrace Terraform configuration migration scripts

## Files Added
- setup.sh
- scripts/migrate.py
- scripts/migrate.sh
- scripts/clone-config.sh
- scripts/verify_migration.py
- requirements.txt
- config/.env.example
- config/environments.yaml
- docs/GETTING_STARTED.md
- docs/ADVANCED.md
- docs/TROUBLESHOOTING.md
- README.md
- .gitignore

## Implemented Script Capabilities
### scripts/migrate.py
- Loads credentials from CLI args or .env.
- Verifies Terraform CLI availability.
- Verifies source and target API connectivity.
- Generates config/environments.yaml.
- Exports source configuration into Terraform-compatible state/config structure.
- Validates YAML configuration before deploy.
- Creates target backup before deployment.
- Supports dry-run mode.
- Supports selective migration via --config-types.
- Supports discovery via --list-types.

### scripts/migrate.sh
- Same migration flow as Python version.
- Includes colorful CLI logging and argument parsing.
- Supports --dry-run and --config-types.
- Supports --no-backup.
- Supports discovery via --list-types.

### scripts/clone-config.sh
- Downloads tenant configuration into timestamped folders.
- Optional config type filtering.

### scripts/verify_migration.py
- Compares source and target counts for key objects.
- Reports pass/warn/fail style status for verification.

### setup.sh
- Interactive setup wizard.
- Checks dependencies (Terraform, Python, curl).
- Collects tenant URL/token values.
- Writes .env for local use.

## Security and Safety Choices
- .gitignore excludes .env, logs, backups, and generated folders.
- Example tokens are kept only in template files.
- Backup-first deployment behavior in migration flow.
- Dry-run supported before real deployment.

## Operator Quick Commands
- Python migration: python3 scripts/migrate.py
- Shell migration: ./scripts/migrate.sh
- List config types (Python): python3 scripts/migrate.py --list-types
- List config types (Shell): ./scripts/migrate.sh --list-types
- Dashboards-only migration: python3 scripts/migrate.py --config-types dashboard

## Known Notes
- Configuration types are maintained in script constants/output tables.
- Terraform CLI must be available in PATH.
- API token scopes must match source read and target write operations.

## Handoff
For day-to-day usage, start with docs/GETTING_STARTED.md.
For change history and rationale, see PROJECT_SETUP.agent.md.
