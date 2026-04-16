# Legacy Migration Scripts

These scripts provide a single-step migration workflow that combines export and deploy into one operation. For production use with code review and format flexibility, see the [pipeline system](../pipelines/) instead.

## Scripts

### migrate.py

All-in-one Python migration. Exports configuration from a source tenant via the Dynatrace API, generates Terraform-compatible output, and deploys to a target tenant.

**Workflow:** verify Terraform CLI -> create environments.yaml -> verify API connections -> backup target -> download source -> validate -> generate Terraform config -> deploy

```bash
# Using .env
source .env
python3 scripts/migrate.py

# With arguments
python3 scripts/migrate.py \
    --source https://source.live.dynatrace.com \
    --target https://target.live.dynatrace.com \
    --source-token TOKEN \
    --target-token TOKEN

# Dry run
python3 scripts/migrate.py --dry-run

# Specific types only
python3 scripts/migrate.py --config-types dashboard,management-zone

# List supported types
python3 scripts/migrate.py --list-types
```

| Flag | Description |
|------|-------------|
| `--source` | Source tenant URL (or `SOURCE_TENANT_URL` env var) |
| `--target` | Target tenant URL (or `TARGET_TENANT_URL` env var) |
| `--source-token` | Source API token (or `SOURCE_TENANT_TOKEN` env var) |
| `--target-token` | Target API token (or `TARGET_TENANT_TOKEN` env var) |
| `--config-dir` | Working directory for configs (default: `config`) |
| `--dry-run` | Run terraform plan only, skip apply |
| `--config-types` | Comma-separated list of types to migrate |
| `--list-types` | Print available config types and exit |

---

### migrate.sh

Shell equivalent of `migrate.py`. Same 7-step workflow with colored terminal output.

```bash
# Using .env
source .env
./scripts/migrate.sh

# With arguments
./scripts/migrate.sh \
    --source-url https://source.live.dynatrace.com \
    --target-url https://target.live.dynatrace.com \
    --source-token TOKEN \
    --target-token TOKEN

# Dry run
./scripts/migrate.sh --dry-run

# Skip target backup
./scripts/migrate.sh --no-backup

# Specific types
./scripts/migrate.sh --config-types dashboard,management-zone

# List types
./scripts/migrate.sh --list-types
```

| Flag | Description |
|------|-------------|
| `--source-url` | Source tenant URL |
| `--target-url` | Target tenant URL |
| `--source-token` | Source API token |
| `--target-token` | Target API token |
| `--config-dir` | Working directory for configs (default: `config`) |
| `--dry-run` | Preview changes without applying |
| `--no-backup` | Skip backup of target configuration |
| `--config-types` | Comma-separated list of types to migrate |
| `--list-types` | Print available config types and exit |

---

### clone-config.sh

Standalone helper that downloads configuration from a single tenant into a timestamped directory. No deployment — export only.

```bash
# All config types
./scripts/clone-config.sh https://tenant.live.dynatrace.com TOKEN

# Specific types
./scripts/clone-config.sh https://tenant.live.dynatrace.com TOKEN dashboard,management-zone
```

| Argument | Required | Description |
|----------|----------|-------------|
| `source-url` | Yes | Dynatrace tenant URL |
| `source-token` | Yes | API token |
| `config-types` | No | Comma-separated types (default: all) |

Output directory: `config/cloned-YYYYMMDD-HHMMSS/`

---

### verify_migration.py

Post-migration verification that compares configuration counts between source and target tenants. Reports pass/warn/fail per config type.

```bash
# Using .env
source .env
python3 scripts/verify_migration.py

# With arguments
python3 scripts/verify_migration.py \
    --source https://source.live.dynatrace.com \
    --target https://target.live.dynatrace.com \
    --source-token TOKEN \
    --target-token TOKEN
```

| Flag | Description |
|------|-------------|
| `--source` | Source tenant URL (or `SOURCE_TENANT_URL` env var) |
| `--target` | Target tenant URL (or `TARGET_TENANT_URL` env var) |
| `--source-token` | Source API token (or `SOURCE_TENANT_TOKEN` env var) |
| `--target-token` | Target API token (or `TARGET_TENANT_TOKEN` env var) |

Checks: dashboards, alerting profiles, management zones, notifications, auto-tags.

---

## Setup Wizard

`setup.sh` lives in the project root (not in `scripts/`). It's an interactive wizard that checks dependencies, collects tenant credentials, verifies API connectivity, and writes a `.env` file.

```bash
./setup.sh
```
